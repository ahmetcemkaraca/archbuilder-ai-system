"""
RAG Service Implementation for ArchBuilder.AI
Retrieval-Augmented Generation with document chunking, embedding generation,
similarity search, and multilingual support for building codes and regulations
"""

import asyncio
import json
import hashlib
import math
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import structlog
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.documents import DocumentType
from app.models.rag import (
    RAGQueryRequest,
    RAGQueryResponse,
    DocumentChunk,
    EmbeddingVector,
    SimilaritySearchResult,
    RAGIndexStats
)
from app.core.exceptions import (
    RAGServiceException,
    EmbeddingException,
    SearchException
)
from app.core.config import settings
from app.utils.cache import AsyncCache
from app.utils.performance import PerformanceTracker
from app.core.logging import get_logger, log_ai_operation

logger = structlog.get_logger(__name__)


@dataclass
class ChunkingStrategy:
    """Configuration for document chunking strategies"""
    chunk_size: int = 1000  # Characters per chunk
    overlap: int = 200      # Character overlap between chunks
    respect_sentences: bool = True
    respect_paragraphs: bool = True
    min_chunk_size: int = 100
    max_chunk_size: int = 2000


class DocumentChunker:
    """Advanced document chunking with context preservation"""
    
    def __init__(self, strategy: ChunkingStrategy = None):
        self.strategy = strategy or ChunkingStrategy()
        self.logger = get_logger(__name__)
        
        # Language-specific sentence delimiters
        self.sentence_delimiters = {
            'en': ['.', '!', '?'],
            'tr': ['.', '!', '?', ':', ';'],
            'de': ['.', '!', '?', ':', ';'],
            'fr': ['.', '!', '?', ':', ';'],
            'es': ['.', '!', '?', ':', ';']
        }
        
        # Building code specific markers
        self.section_markers = [
            'Article', 'Section', 'Chapter', 'Madde', 'Bölüm', 'Artikel',
            'Paragraf', 'Clause', 'Subsection', 'Part'
        ]
    
    async def chunk_document(
        self,
        content: str,
        document_id: str,
        metadata: Dict[str, Any],
        correlation_id: str
    ) -> List[DocumentChunk]:
        """Chunk document content with context preservation"""
        
        logger.info(
            "Starting document chunking",
            document_id=document_id,
            content_length=len(content),
            strategy=self.strategy.__dict__,
            correlation_id=correlation_id
        )
        
        try:
            # Detect language for appropriate chunking
            language = metadata.get('language', 'en')
            
            # Split into logical sections first
            sections = self._split_into_sections(content, language)
            
            chunks = []
            chunk_index = 0
            
            for section_index, section in enumerate(sections):
                section_chunks = await self._chunk_section(
                    section,
                    document_id,
                    section_index,
                    chunk_index,
                    metadata,
                    language,
                    correlation_id
                )
                
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)
            
            # Post-process chunks for quality
            chunks = self._post_process_chunks(chunks, metadata)
            
            logger.info(
                "Document chunking completed",
                document_id=document_id,
                total_chunks=len(chunks),
                avg_chunk_size=sum(len(chunk.content) for chunk in chunks) / len(chunks) if chunks else 0,
                correlation_id=correlation_id
            )
            
            return chunks
            
        except Exception as e:
            logger.error(
                "Document chunking failed",
                document_id=document_id,
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise RAGServiceException(
                f"Failed to chunk document {document_id}",
                "DOCUMENT_CHUNKING_FAILED",
                correlation_id,
                inner_exception=e
            )
    
    def _split_into_sections(self, content: str, language: str) -> List[str]:
        """Split content into logical sections"""
        
        lines = content.split('\n')
        sections = []
        current_section = []
        
        for line in lines:
            line = line.strip()
            
            # Check if line is a section header
            is_section_header = self._is_section_header(line, language)
            
            if is_section_header and current_section:
                # Save current section
                section_content = '\n'.join(current_section).strip()
                if section_content:
                    sections.append(section_content)
                current_section = [line]
            else:
                current_section.append(line)
        
        # Add final section
        if current_section:
            section_content = '\n'.join(current_section).strip()
            if section_content:
                sections.append(section_content)
        
        # If no sections found, treat entire content as one section
        if not sections:
            sections = [content]
        
        return sections
    
    def _is_section_header(self, line: str, language: str) -> bool:
        """Determine if line is a section header"""
        
        if not line:
            return False
        
        # Check for section markers
        for marker in self.section_markers:
            if line.startswith(marker):
                return True
        
        # Check for numbered sections (e.g., "1.2.3", "Article 5")
        words = line.split()
        if words:
            first_word = words[0]
            # Check for numeric pattern
            if (first_word.replace('.', '').replace('-', '').isdigit() or
                any(char.isdigit() for char in first_word[:5])):
                return True
        
        # Check if line is all uppercase (common for headers)
        if line.isupper() and len(line.split()) <= 8:
            return True
        
        return False
    
    async def _chunk_section(
        self,
        section: str,
        document_id: str,
        section_index: int,
        start_chunk_index: int,
        metadata: Dict[str, Any],
        language: str,
        correlation_id: str
    ) -> List[DocumentChunk]:
        """Chunk a section with overlap and context preservation"""
        
        if len(section) <= self.strategy.max_chunk_size:
            # Section fits in one chunk
            chunk_id = f"{document_id}_chunk_{start_chunk_index}"
            
            return [DocumentChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                chunk_index=start_chunk_index,
                content=section,
                metadata={
                    **metadata,
                    "section_index": section_index,
                    "language": language,
                    "chunk_type": "complete_section"
                },
                created_at=datetime.utcnow()
            )]
        
        # Need to split section into multiple chunks
        chunks = []
        
        if self.strategy.respect_paragraphs:
            paragraphs = section.split('\n\n')
            current_chunk = ""
            chunk_index = start_chunk_index
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                # Check if adding paragraph would exceed chunk size
                if (len(current_chunk) + len(para) + 2 > self.strategy.chunk_size and 
                    len(current_chunk) >= self.strategy.min_chunk_size):
                    
                    # Save current chunk
                    chunk_id = f"{document_id}_chunk_{chunk_index}"
                    chunks.append(DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        chunk_index=chunk_index,
                        content=current_chunk.strip(),
                        metadata={
                            **metadata,
                            "section_index": section_index,
                            "language": language,
                            "chunk_type": "paragraph_split"
                        },
                        created_at=datetime.utcnow()
                    ))
                    
                    # Start new chunk with overlap
                    overlap_text = self._get_overlap_text(current_chunk, self.strategy.overlap)
                    current_chunk = overlap_text + "\n\n" + para if overlap_text else para
                    chunk_index += 1
                else:
                    # Add paragraph to current chunk
                    if current_chunk:
                        current_chunk += "\n\n" + para
                    else:
                        current_chunk = para
            
            # Save final chunk
            if current_chunk.strip():
                chunk_id = f"{document_id}_chunk_{chunk_index}"
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    chunk_index=chunk_index,
                    content=current_chunk.strip(),
                    metadata={
                        **metadata,
                        "section_index": section_index,
                        "language": language,
                        "chunk_type": "paragraph_split"
                    },
                    created_at=datetime.utcnow()
                ))
        
        else:
            # Simple character-based chunking
            chunks = self._chunk_by_characters(
                section, document_id, section_index, start_chunk_index, metadata, language
            )
        
        return chunks
    
    def _chunk_by_characters(
        self,
        text: str,
        document_id: str,
        section_index: int,
        start_chunk_index: int,
        metadata: Dict[str, Any],
        language: str
    ) -> List[DocumentChunk]:
        """Chunk text by character count with sentence boundary respect"""
        
        chunks = []
        chunk_index = start_chunk_index
        start = 0
        
        while start < len(text):
            end = start + self.strategy.chunk_size
            
            if end >= len(text):
                # Final chunk
                chunk_content = text[start:].strip()
                if chunk_content:
                    chunk_id = f"{document_id}_chunk_{chunk_index}"
                    chunks.append(DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        chunk_index=chunk_index,
                        content=chunk_content,
                        metadata={
                            **metadata,
                            "section_index": section_index,
                            "language": language,
                            "chunk_type": "character_split"
                        },
                        created_at=datetime.utcnow()
                    ))
                break
            
            # Try to end at sentence boundary
            if self.strategy.respect_sentences:
                sentence_end = self._find_sentence_boundary(
                    text, end, language, start + self.strategy.min_chunk_size
                )
                if sentence_end > start:
                    end = sentence_end
            
            chunk_content = text[start:end].strip()
            if chunk_content:
                chunk_id = f"{document_id}_chunk_{chunk_index}"
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    chunk_index=chunk_index,
                    content=chunk_content,
                    metadata={
                        **metadata,
                        "section_index": section_index,
                        "language": language,
                        "chunk_type": "character_split"
                    },
                    created_at=datetime.utcnow()
                ))
            
            # Move start position with overlap
            start = end - self.strategy.overlap
            chunk_index += 1
        
        return chunks
    
    def _find_sentence_boundary(
        self,
        text: str,
        preferred_end: int,
        language: str,
        min_end: int
    ) -> int:
        """Find the best sentence boundary near preferred_end"""
        
        delimiters = self.sentence_delimiters.get(language, ['.', '!', '?'])
        
        # Look backwards from preferred_end for sentence delimiter
        search_start = max(min_end, preferred_end - 200)
        
        for i in range(preferred_end - 1, search_start - 1, -1):
            if text[i] in delimiters:
                # Check if it's actually end of sentence (not abbreviation)
                if i + 1 < len(text) and (text[i + 1].isspace() or text[i + 1] == '\n'):
                    return i + 1
        
        # If no sentence boundary found, return preferred_end
        return preferred_end
    
    def _get_overlap_text(self, text: str, overlap_size: int) -> str:
        """Get overlap text from end of chunk"""
        
        if len(text) <= overlap_size:
            return text
        
        overlap_text = text[-overlap_size:]
        
        # Try to start overlap at word boundary
        space_index = overlap_text.find(' ')
        if space_index > 0:
            overlap_text = overlap_text[space_index + 1:]
        
        return overlap_text
    
    def _post_process_chunks(
        self,
        chunks: List[DocumentChunk],
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """Post-process chunks for quality improvement"""
        
        processed_chunks = []
        
        for chunk in chunks:
            # Skip chunks that are too small
            if len(chunk.content.strip()) < self.strategy.min_chunk_size:
                continue
            
            # Clean up content
            content = chunk.content.strip()
            
            # Remove excessive whitespace
            content = ' '.join(content.split())
            
            # Update chunk with cleaned content
            chunk.content = content
            
            # Add quality metrics
            chunk.metadata.update({
                "content_length": len(content),
                "word_count": len(content.split()),
                "quality_score": self._calculate_chunk_quality(content)
            })
            
            processed_chunks.append(chunk)
        
        return processed_chunks
    
    def _calculate_chunk_quality(self, content: str) -> float:
        """Calculate quality score for chunk (0.0 to 1.0)"""
        
        score = 1.0
        
        # Penalize very short chunks
        if len(content) < 100:
            score *= 0.5
        
        # Penalize chunks with too much whitespace
        whitespace_ratio = (len(content) - len(content.replace(' ', ''))) / len(content)
        if whitespace_ratio > 0.3:
            score *= 0.8
        
        # Reward chunks with complete sentences
        sentence_delims = ['.', '!', '?']
        if any(content.strip().endswith(delim) for delim in sentence_delims):
            score *= 1.1
        
        # Reward chunks with section markers (important content)
        if any(marker in content for marker in self.section_markers):
            score *= 1.2
        
        return min(1.0, score)


class EmbeddingGenerator:
    """Generate embeddings for document chunks with multiple strategies"""
    
    def __init__(self, cache: Optional[AsyncCache] = None):
        self.cache = cache
        self.logger = get_logger(__name__)
        
        # Initialize TF-IDF vectorizer for fallback
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=512,
            stop_words='english',
            ngram_range=(1, 2),
            max_df=0.95,
            min_df=2
        )
        self.tfidf_fitted = False
        
        # Store embedding cache
        self.embedding_cache: Dict[str, np.ndarray] = {}
    
    async def generate_embeddings(
        self,
        chunks: List[DocumentChunk],
        correlation_id: str
    ) -> List[EmbeddingVector]:
        """Generate embeddings for document chunks"""
        
        logger.info(
            "Generating embeddings",
            chunk_count=len(chunks),
            correlation_id=correlation_id
        )
        
        try:
            embeddings = []
            
            # Prepare texts for vectorization
            texts = [chunk.content for chunk in chunks]
            
            # Generate embeddings based on available method
            if hasattr(self, '_generate_openai_embeddings'):
                vectors = await self._generate_openai_embeddings(texts, correlation_id)
            else:
                vectors = await self._generate_tfidf_embeddings(texts, correlation_id)
            
            # Create embedding objects
            for i, chunk in enumerate(chunks):
                embedding = EmbeddingVector(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    vector=vectors[i].tolist(),
                    embedding_model="tfidf-512d",  # or "text-embedding-ada-002" for OpenAI
                    vector_dimension=len(vectors[i]),
                    created_at=datetime.utcnow(),
                    metadata={
                        "content_length": len(chunk.content),
                        "language": chunk.metadata.get("language", "en"),
                        "chunk_type": chunk.metadata.get("chunk_type", "unknown")
                    }
                )
                embeddings.append(embedding)
            
            logger.info(
                "Embeddings generated successfully",
                embedding_count=len(embeddings),
                vector_dimension=embeddings[0].vector_dimension if embeddings else 0,
                correlation_id=correlation_id
            )
            
            return embeddings
            
        except Exception as e:
            logger.error(
                "Embedding generation failed",
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise EmbeddingException(
                "Failed to generate embeddings",
                "EMBEDDING_GENERATION_FAILED",
                correlation_id,
                inner_exception=e
            )
    
    async def _generate_tfidf_embeddings(
        self,
        texts: List[str],
        correlation_id: str
    ) -> np.ndarray:
        """Generate TF-IDF based embeddings as fallback"""
        
        try:
            if not self.tfidf_fitted:
                # Fit vectorizer on all texts
                self.tfidf_vectorizer.fit(texts)
                self.tfidf_fitted = True
            
            # Transform texts to vectors
            vectors = self.tfidf_vectorizer.transform(texts)
            
            # Convert to dense array
            return vectors.toarray()
            
        except Exception as e:
            logger.error(
                "TF-IDF embedding generation failed",
                error=str(e),
                correlation_id=correlation_id
            )
            raise
    
    async def generate_query_embedding(
        self,
        query: str,
        correlation_id: str
    ) -> np.ndarray:
        """Generate embedding for search query"""
        
        try:
            # Check cache first
            cache_key = f"query_embedding:{hashlib.md5(query.encode()).hexdigest()}"
            
            if self.cache:
                cached_embedding = await self.cache.get(cache_key)
                if cached_embedding:
                    return np.array(cached_embedding)
            
            # Generate embedding
            if hasattr(self, '_generate_openai_embeddings'):
                vectors = await self._generate_openai_embeddings([query], correlation_id)
                embedding = vectors[0]
            else:
                if not self.tfidf_fitted:
                    # If vectorizer not fitted, create simple embedding
                    embedding = np.random.random(512)  # Random fallback
                else:
                    vectors = self.tfidf_vectorizer.transform([query])
                    embedding = vectors.toarray()[0]
            
            # Cache result
            if self.cache:
                await self.cache.set(cache_key, embedding.tolist(), ttl=3600)
            
            return embedding
            
        except Exception as e:
            logger.error(
                "Query embedding generation failed",
                query_length=len(query),
                error=str(e),
                correlation_id=correlation_id
            )
            raise


class SimilaritySearchEngine:
    """Advanced similarity search with multiple ranking strategies"""
    
    def __init__(self, cache: Optional[AsyncCache] = None):
        self.cache = cache
        self.logger = get_logger(__name__)
        
        # Store embeddings for fast search
        self.embeddings_index: Dict[str, np.ndarray] = {}
        self.chunks_index: Dict[str, DocumentChunk] = {}
    
    async def index_chunks(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[EmbeddingVector],
        correlation_id: str
    ):
        """Index chunks and embeddings for fast searching"""
        
        logger.info(
            "Indexing chunks for similarity search",
            chunk_count=len(chunks),
            correlation_id=correlation_id
        )
        
        try:
            for chunk, embedding in zip(chunks, embeddings):
                self.chunks_index[chunk.chunk_id] = chunk
                self.embeddings_index[chunk.chunk_id] = np.array(embedding.vector)
            
            logger.info(
                "Chunk indexing completed",
                total_indexed=len(self.chunks_index),
                correlation_id=correlation_id
            )
            
        except Exception as e:
            logger.error(
                "Chunk indexing failed",
                error=str(e),
                correlation_id=correlation_id
            )
            raise
    
    async def search_similar(
        self,
        query_embedding: np.ndarray,
        max_results: int = 10,
        similarity_threshold: float = 0.1,
        filters: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> List[SimilaritySearchResult]:
        """Search for similar chunks using cosine similarity"""
        
        logger.info(
            "Performing similarity search",
            max_results=max_results,
            similarity_threshold=similarity_threshold,
            filters=filters,
            correlation_id=correlation_id
        )
        
        try:
            if not self.embeddings_index:
                logger.warning("No embeddings indexed for search")
                return []
            
            results = []
            
            # Calculate similarities
            for chunk_id, chunk_embedding in self.embeddings_index.items():
                chunk = self.chunks_index[chunk_id]
                
                # Apply filters
                if filters and not self._apply_filters(chunk, filters):
                    continue
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                
                if similarity >= similarity_threshold:
                    results.append(SimilaritySearchResult(
                        chunk_id=chunk_id,
                        document_id=chunk.document_id,
                        similarity_score=float(similarity),
                        chunk_content=chunk.content,
                        chunk_metadata=chunk.metadata,
                        ranking_features={
                            "cosine_similarity": float(similarity),
                            "content_length": len(chunk.content),
                            "quality_score": chunk.metadata.get("quality_score", 0.5)
                        }
                    ))
            
            # Sort by similarity score (descending)
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            
            # Apply additional ranking
            results = self._rerank_results(results, query_embedding)
            
            # Limit results
            results = results[:max_results]
            
            logger.info(
                "Similarity search completed",
                results_found=len(results),
                avg_similarity=sum(r.similarity_score for r in results) / len(results) if results else 0,
                correlation_id=correlation_id
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Similarity search failed",
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise SearchException(
                "Similarity search failed",
                "SIMILARITY_SEARCH_FAILED",
                correlation_id,
                inner_exception=e
            )
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        
        # Normalize vectors
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return np.dot(vec1, vec2) / (norm1 * norm2)
    
    def _apply_filters(self, chunk: DocumentChunk, filters: Dict[str, Any]) -> bool:
        """Apply filters to chunk"""
        
        metadata = chunk.metadata
        
        # Language filter
        if "language" in filters:
            if metadata.get("language") != filters["language"]:
                return False
        
        # Document type filter
        if "document_type" in filters:
            if metadata.get("file_type") != filters["document_type"]:
                return False
        
        # Building code filter
        if "is_building_code" in filters:
            if metadata.get("is_building_code") != filters["is_building_code"]:
                return False
        
        # Content length filter
        if "min_content_length" in filters:
            if len(chunk.content) < filters["min_content_length"]:
                return False
        
        return True
    
    def _rerank_results(
        self,
        results: List[SimilaritySearchResult],
        query_embedding: np.ndarray
    ) -> List[SimilaritySearchResult]:
        """Apply additional ranking to improve result quality"""
        
        for result in results:
            # Calculate combined score
            similarity_score = result.similarity_score
            quality_score = result.chunk_metadata.get("quality_score", 0.5)
            content_length_score = min(1.0, len(result.chunk_content) / 1000)  # Normalize by 1000 chars
            
            # Weight factors
            combined_score = (
                similarity_score * 0.6 +
                quality_score * 0.3 +
                content_length_score * 0.1
            )
            
            result.ranking_features["combined_score"] = combined_score
        
        # Sort by combined score
        results.sort(key=lambda x: x.ranking_features["combined_score"], reverse=True)
        
        return results
    
    def remove_document(self, document_id: str, correlation_id: str):
        """Remove all chunks for a document from the index"""
        
        logger.info(
            "Removing document from search index",
            document_id=document_id,
            correlation_id=correlation_id
        )
        
        chunks_to_remove = [
            chunk_id for chunk_id, chunk in self.chunks_index.items()
            if chunk.document_id == document_id
        ]
        
        for chunk_id in chunks_to_remove:
            del self.chunks_index[chunk_id]
            if chunk_id in self.embeddings_index:
                del self.embeddings_index[chunk_id]
        
        logger.info(
            "Document removed from search index",
            document_id=document_id,
            chunks_removed=len(chunks_to_remove),
            correlation_id=correlation_id
        )


class RAGService:
    """Comprehensive RAG service with document processing and knowledge retrieval"""
    
    def __init__(
        self,
        cache: Optional[AsyncCache] = None,
        performance_tracker: Optional[PerformanceTracker] = None,
        chunking_strategy: Optional[ChunkingStrategy] = None
    ):
        self.cache = cache
        self.performance_tracker = performance_tracker
        self.logger = get_logger(__name__)
        
        # Initialize components
        self.chunker = DocumentChunker(chunking_strategy or ChunkingStrategy())
        self.embedding_generator = EmbeddingGenerator(cache)
        self.search_engine = SimilaritySearchEngine(cache)
        
        # Document storage
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.document_chunks: Dict[str, List[DocumentChunk]] = {}
        
        logger.info("RAG Service initialized")
    
    async def index_document(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any],
        correlation_id: str
    ) -> Dict[str, Any]:
        """Index document for RAG retrieval"""
        
        start_time = datetime.utcnow()
        
        logger.info(
            "Starting document indexing",
            document_id=document_id,
            content_length=len(content),
            correlation_id=correlation_id
        )
        
        try:
            # Store document metadata
            self.documents[document_id] = {
                "metadata": metadata,
                "content_length": len(content),
                "indexed_at": start_time,
                "correlation_id": correlation_id
            }
            
            # Chunk document
            chunks = await self.chunker.chunk_document(
                content, document_id, metadata, correlation_id
            )
            
            if not chunks:
                logger.warning(
                    "No chunks generated for document",
                    document_id=document_id,
                    correlation_id=correlation_id
                )
                return {"status": "no_chunks", "chunk_count": 0}
            
            # Generate embeddings
            embeddings = await self.embedding_generator.generate_embeddings(
                chunks, correlation_id
            )
            
            # Index for search
            await self.search_engine.index_chunks(chunks, embeddings, correlation_id)
            
            # Store chunks
            self.document_chunks[document_id] = chunks
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info(
                "Document indexing completed",
                document_id=document_id,
                chunk_count=len(chunks),
                processing_time_ms=processing_time,
                correlation_id=correlation_id
            )
            
            # Log AI operation
            log_ai_operation(
                operation="document_indexing",
                model_used="tfidf-512d",
                input_tokens=len(content.split()),
                correlation_id=correlation_id,
                metadata={
                    "document_id": document_id,
                    "chunk_count": len(chunks),
                    "processing_time_ms": int(processing_time)
                }
            )
            
            return {
                "status": "indexed",
                "chunk_count": len(chunks),
                "embedding_count": len(embeddings),
                "processing_time_ms": int(processing_time),
                "avg_chunk_size": sum(len(chunk.content) for chunk in chunks) / len(chunks)
            }
            
        except Exception as e:
            logger.error(
                "Document indexing failed",
                document_id=document_id,
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise RAGServiceException(
                f"Failed to index document {document_id}",
                "DOCUMENT_INDEXING_FAILED",
                correlation_id,
                inner_exception=e
            )
    
    async def query_knowledge_base(
        self,
        query: str,
        max_results: int = 10,
        similarity_threshold: float = 0.3,
        filters: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> RAGQueryResponse:
        """Query the knowledge base using RAG retrieval"""
        
        if correlation_id is None:
            correlation_id = f"rag-query-{uuid.uuid4().hex[:8]}"
        
        start_time = datetime.utcnow()
        
        logger.info(
            "Querying knowledge base",
            query_length=len(query),
            max_results=max_results,
            similarity_threshold=similarity_threshold,
            filters=filters,
            correlation_id=correlation_id
        )
        
        try:
            # Generate query embedding
            query_embedding = await self.embedding_generator.generate_query_embedding(
                query, correlation_id
            )
            
            # Search for similar chunks
            search_results = await self.search_engine.search_similar(
                query_embedding,
                max_results=max_results,
                similarity_threshold=similarity_threshold,
                filters=filters,
                correlation_id=correlation_id
            )
            
            # Prepare response
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            response = RAGQueryResponse(
                query=query,
                correlation_id=correlation_id,
                results_found=len(search_results),
                documents=search_results,
                processing_time_ms=int(processing_time),
                search_metadata={
                    "similarity_threshold": similarity_threshold,
                    "max_results_requested": max_results,
                    "filters_applied": filters or {},
                    "avg_similarity": sum(r.similarity_score for r in search_results) / len(search_results) if search_results else 0
                },
                timestamp=datetime.utcnow()
            )
            
            logger.info(
                "Knowledge base query completed",
                query_length=len(query),
                results_found=len(search_results),
                avg_similarity=response.search_metadata["avg_similarity"],
                processing_time_ms=processing_time,
                correlation_id=correlation_id
            )
            
            # Log AI operation
            log_ai_operation(
                operation="rag_query",
                model_used="tfidf-512d",
                input_tokens=len(query.split()),
                correlation_id=correlation_id,
                metadata={
                    "results_found": len(search_results),
                    "avg_similarity": response.search_metadata["avg_similarity"]
                }
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Knowledge base query failed",
                query=query[:100],  # Log first 100 chars
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            
            # Return error response
            return RAGQueryResponse(
                query=query,
                correlation_id=correlation_id,
                results_found=0,
                documents=[],
                processing_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                search_metadata={"error": str(e)},
                timestamp=datetime.utcnow()
            )


# Global RAG service instance
rag_service = RAGService()