"""
Unit tests for RAG Service functionality
Tests document chunking, embedding generation, and similarity search
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any
import numpy as np

from app.services.rag_service import RAGService
from app.models.documents import DocumentChunk, EmbeddingVector, RAGContext
from app.models.ai import AIProcessingRequest, PromptContext


class TestRAGService:
    """Test RAG Service main functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.rag_service = RAGService()
    
    @pytest.mark.asyncio
    async def test_create_document_chunks_success(self):
        """Test successful document chunking"""
        document_id = "doc-123"
        document_text = """
        Chapter 1: Building Requirements
        
        Minimum ceiling height shall be 2.4 meters for residential spaces.
        All rooms must have adequate natural lighting.
        
        Chapter 2: Fire Safety
        
        Exit doors must be clearly marked and accessible.
        Fire extinguishers must be installed every 30 meters.
        Emergency exits must be clearly marked with illuminated signs.
        """
        
        chunks = await self.rag_service.create_document_chunks(document_id, document_text)
        
        # Assertions
        assert len(chunks) > 0
        assert all(chunk.document_id == document_id for chunk in chunks)
        assert all(len(chunk.text) <= 2000 for chunk in chunks)  # Max chunk size
        assert all(chunk.chunk_index >= 0 for chunk in chunks)
        
        # Check that chunks contain relevant content
        chunk_texts = [chunk.text for chunk in chunks]
        combined_text = " ".join(chunk_texts)
        assert "ceiling height" in combined_text
        assert "fire safety" in combined_text.lower()
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_success(self):
        """Test successful embedding generation"""
        # Create test chunks
        chunks = [
            DocumentChunk(
                document_id="doc-123",
                chunk_index=0,
                text="Minimum ceiling height shall be 2.4 meters",
                start_position=0,
                end_position=43
            ),
            DocumentChunk(
                document_id="doc-123",
                chunk_index=1,
                text="Fire extinguishers must be installed every 30 meters",
                start_position=44,
                end_position=97
            )
        ]
        
        # Mock embedding generation
        with patch.object(self.rag_service, '_generate_embedding_vector') as mock_embed:
            mock_embed.side_effect = [
                [0.1, 0.2, 0.3, 0.4, 0.5],  # Mock vector for first chunk
                [0.6, 0.7, 0.8, 0.9, 1.0]   # Mock vector for second chunk
            ]
            
            embeddings = await self.rag_service.generate_embeddings(chunks)
            
            # Assertions
            assert len(embeddings) == 2
            assert all(len(emb.vector) == 5 for emb in embeddings)
            assert embeddings[0].document_id == "doc-123"
            assert embeddings[0].chunk_index == 0
            assert embeddings[1].chunk_index == 1
    
    @pytest.mark.asyncio
    async def test_similarity_search_success(self):
        """Test successful similarity search"""
        query = "What is the minimum ceiling height?"
        
        # Mock stored embeddings
        stored_embeddings = [
            EmbeddingVector(
                document_id="doc-123",
                chunk_index=0,
                text="Minimum ceiling height shall be 2.4 meters for residential spaces",
                vector=[0.1, 0.2, 0.3, 0.4, 0.5]
            ),
            EmbeddingVector(
                document_id="doc-123",
                chunk_index=1,
                text="Fire extinguishers must be installed every 30 meters",
                vector=[0.6, 0.7, 0.8, 0.9, 1.0]
            ),
            EmbeddingVector(
                document_id="doc-456",
                chunk_index=0,
                text="Window opening requirements for natural ventilation",
                vector=[0.2, 0.3, 0.4, 0.5, 0.6]
            )
        ]
        
        # Mock query embedding
        query_vector = [0.15, 0.25, 0.35, 0.45, 0.55]
        
        with patch.object(self.rag_service, '_get_stored_embeddings', return_value=stored_embeddings):
            with patch.object(self.rag_service, '_generate_embedding_vector', return_value=query_vector):
                
                results = await self.rag_service.similarity_search(query, max_results=2)
                
                # Assertions
                assert len(results) <= 2
                assert all(hasattr(result, 'text') for result in results)
                assert all(hasattr(result, 'similarity_score') for result in results)
                
                # The first result should be about ceiling height (most similar)
                assert "ceiling height" in results[0].text
                assert results[0].similarity_score > results[1].similarity_score
    
    @pytest.mark.asyncio
    async def test_create_rag_context_success(self):
        """Test successful RAG context creation"""
        query = "What are the fire safety requirements?"
        
        # Mock relevant chunks
        relevant_chunks = [
            DocumentChunk(
                document_id="doc-123",
                chunk_index=5,
                text="Exit doors must be clearly marked and accessible at all times",
                start_position=200,
                end_position=264
            ),
            DocumentChunk(
                document_id="doc-123", 
                chunk_index=6,
                text="Fire extinguishers must be installed every 30 meters in commercial buildings",
                start_position=265,
                end_position=341
            )
        ]
        
        # Mock building rules
        building_rules = []
        
        with patch.object(self.rag_service, 'similarity_search', return_value=relevant_chunks):
            with patch.object(self.rag_service, '_get_relevant_building_rules', return_value=building_rules):
                
                context = await self.rag_service.create_rag_context(query, max_chunks=5)
                
                # Assertions
                assert context.query == query
                assert len(context.relevant_chunks) == 2
                assert context.max_chunks == 5
                assert context.confidence_score > 0.0
                assert "fire" in context.relevant_chunks[0].text.lower() or "fire" in context.relevant_chunks[1].text.lower()
    
    @pytest.mark.asyncio
    async def test_enhance_ai_prompt_with_rag(self):
        """Test AI prompt enhancement with RAG context"""
        original_prompt = "Design a residential building layout"
        
        # Create AI processing request
        request = AIProcessingRequest(
            correlation_id="test-123",
            prompt=original_prompt,
            ai_model_config=Mock(),
            confidence_threshold=0.7,
            context=PromptContext(
                language="en",
                region="Turkey"
            )
        )
        
        # Mock RAG context
        rag_context = RAGContext(
            query=original_prompt,
            relevant_chunks=[
                DocumentChunk(
                    document_id="building-code-123",
                    chunk_index=0,
                    text="Residential buildings must have minimum 2.4m ceiling height",
                    start_position=0,
                    end_position=60
                ),
                DocumentChunk(
                    document_id="building-code-123",
                    chunk_index=1,
                    text="Natural lighting area must be minimum 10% of floor area",
                    start_position=61,
                    end_position=116
                )
            ],
            confidence_score=0.85
        )
        
        with patch.object(self.rag_service, 'create_rag_context', return_value=rag_context):
            enhanced_prompt = await self.rag_service.enhance_ai_prompt_with_rag(request)
            
            # Assertions
            assert len(enhanced_prompt) > len(original_prompt)
            assert original_prompt in enhanced_prompt
            assert "2.4m ceiling height" in enhanced_prompt
            assert "natural lighting" in enhanced_prompt.lower()
            assert "building code" in enhanced_prompt.lower() or "regulation" in enhanced_prompt.lower()
    
    def test_calculate_similarity_score(self):
        """Test similarity score calculation"""
        vector1 = [1.0, 0.0, 0.0, 0.0, 0.0]
        vector2 = [1.0, 0.0, 0.0, 0.0, 0.0]  # Identical vectors
        vector3 = [0.0, 1.0, 0.0, 0.0, 0.0]  # Orthogonal vectors
        vector4 = [-1.0, 0.0, 0.0, 0.0, 0.0] # Opposite vectors
        
        # Test identical vectors (similarity = 1.0)
        similarity_identical = self.rag_service._calculate_similarity(vector1, vector2)
        assert abs(similarity_identical - 1.0) < 0.01
        
        # Test orthogonal vectors (similarity = 0.0)
        similarity_orthogonal = self.rag_service._calculate_similarity(vector1, vector3)
        assert abs(similarity_orthogonal - 0.0) < 0.01
        
        # Test opposite vectors (similarity = -1.0)
        similarity_opposite = self.rag_service._calculate_similarity(vector1, vector4)
        assert abs(similarity_opposite - (-1.0)) < 0.01
    
    def test_chunk_text_with_overlap(self):
        """Test text chunking with overlap"""
        text = "This is a very long text that needs to be chunked. " * 50  # ~2500 chars
        
        chunks = self.rag_service._chunk_text_with_overlap(text, chunk_size=500, overlap_size=50)
        
        # Assertions
        assert len(chunks) > 1  # Should be multiple chunks
        assert all(len(chunk) <= 500 for chunk in chunks)
        
        # Check overlap between consecutive chunks
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            
            # Find common substring at the end of current and start of next
            overlap_found = False
            for j in range(1, min(51, len(current_chunk), len(next_chunk))):
                if current_chunk[-j:] in next_chunk[:j+10]:  # Allow some flexibility
                    overlap_found = True
                    break
            
            # At least some chunks should have overlap
            if i < len(chunks) - 2:  # Not the last transition
                assert overlap_found or len(current_chunk) < 450  # Unless chunk is naturally short
    
    def test_extract_keywords_from_query(self):
        """Test keyword extraction from queries"""
        query1 = "What is the minimum ceiling height for residential buildings?"
        keywords1 = self.rag_service._extract_keywords(query1)
        
        expected_keywords = ["minimum", "ceiling", "height", "residential", "buildings"]
        assert any(keyword in keywords1 for keyword in expected_keywords)
        
        query2 = "Fire safety requirements and emergency exit specifications"
        keywords2 = self.rag_service._extract_keywords(query2)
        
        expected_keywords2 = ["fire", "safety", "emergency", "exit", "specifications"]
        assert any(keyword in keywords2 for keyword in expected_keywords2)
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_embeddings(self):
        """Test storing and retrieving embeddings"""
        # Create test embedding
        embedding = EmbeddingVector(
            document_id="doc-123",
            chunk_index=0,
            text="Test chunk text for embedding storage",
            vector=[0.1, 0.2, 0.3, 0.4, 0.5]
        )
        
        # Mock storage operations
        with patch.object(self.rag_service, '_store_embedding') as mock_store:
            with patch.object(self.rag_service, '_get_stored_embeddings') as mock_retrieve:
                
                mock_store.return_value = True
                mock_retrieve.return_value = [embedding]
                
                # Store embedding
                success = await self.rag_service.store_embedding(embedding)
                assert success is True
                
                # Retrieve embeddings
                retrieved = await self.rag_service.get_embeddings_for_document("doc-123")
                assert len(retrieved) == 1
                assert retrieved[0].document_id == "doc-123"
                assert retrieved[0].text == "Test chunk text for embedding storage"


class TestRAGServiceIntegration:
    """Integration tests for RAG Service functionality"""
    
    @pytest.mark.asyncio
    async def test_complete_rag_workflow(self):
        """Test complete RAG workflow from document to enhanced prompt"""
        rag_service = RAGService()
        
        # Step 1: Process document
        document_id = "building-code-tr-123"
        document_text = """
        Türk İnşaat Yönetmeliği - Konut Binaları
        
        Madde 5.1 - Tavan Yükseklikleri
        Konut binalarında minimum tavan yüksekliği 2.40 metre olmalıdır.
        Yatak odalarında bu yükseklik 2.30 metre olabilir.
        
        Madde 5.2 - Doğal Aydınlatma
        Tüm yaşam alanlarında pencere alanı, oda alanının minimum %10'u olmalıdır.
        Mutfak ve banyo gibi servis alanlarında %8 yeterlidir.
        
        Madde 6.1 - Yangın Güvenliği
        Çıkış kapıları minimum 90 cm genişliğinde olmalıdır.
        Acil çıkış yolları açık ve erişilebilir tutulmalıdır.
        """
        
        # Mock the entire workflow
        with patch.object(rag_service, '_generate_embedding_vector') as mock_embed:
            with patch.object(rag_service, '_store_embedding') as mock_store:
                with patch.object(rag_service, '_get_stored_embeddings') as mock_retrieve:
                    
                    # Configure mocks
                    mock_embed.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
                    mock_store.return_value = True
                    
                    # Step 2: Create chunks and embeddings
                    chunks = await rag_service.create_document_chunks(document_id, document_text)
                    embeddings = await rag_service.generate_embeddings(chunks)
                    
                    # Mock stored embeddings for retrieval
                    mock_retrieve.return_value = embeddings
                    
                    # Step 3: Create AI request
                    ai_request = AIProcessingRequest(
                        correlation_id="test-rag-workflow",
                        prompt="Create a 3-bedroom apartment layout following Turkish building codes",
                        ai_model_config=Mock(),
                        confidence_threshold=0.7,
                        context=PromptContext(
                            language="tr",
                            region="Turkey"
                        )
                    )
                    
                    # Step 4: Enhance prompt with RAG
                    enhanced_prompt = await rag_service.enhance_ai_prompt_with_rag(ai_request)
                    
                    # Assertions
                    assert len(chunks) > 0
                    assert len(embeddings) == len(chunks)
                    assert len(enhanced_prompt) > len(ai_request.prompt)
                    assert "Turkish building codes" in enhanced_prompt or "Türk" in enhanced_prompt
                    assert "2.40 metre" in enhanced_prompt or "2.30 metre" in enhanced_prompt
    
    @pytest.mark.asyncio
    async def test_multilingual_rag_support(self):
        """Test RAG support for multiple languages"""
        rag_service = RAGService()
        
        # Turkish document
        turkish_text = "Minimum tavan yüksekliği 2.40 metre olmalıdır"
        turkish_chunks = await rag_service.create_document_chunks("tr-doc", turkish_text)
        
        # English document  
        english_text = "Minimum ceiling height shall be 2.4 meters"
        english_chunks = await rag_service.create_document_chunks("en-doc", english_text)
        
        # Mock embeddings
        with patch.object(rag_service, '_generate_embedding_vector') as mock_embed:
            mock_embed.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
            
            turkish_embeddings = await rag_service.generate_embeddings(turkish_chunks)
            english_embeddings = await rag_service.generate_embeddings(english_chunks)
            
            # Both should be processed successfully
            assert len(turkish_embeddings) > 0
            assert len(english_embeddings) > 0
            assert turkish_embeddings[0].text != english_embeddings[0].text
    
    @pytest.mark.asyncio 
    async def test_rag_with_building_rules_extraction(self):
        """Test RAG integration with building rules extraction"""
        rag_service = RAGService()
        
        query = "What are the accessibility requirements for doors?"
        
        # Mock relevant chunks with building code content
        relevant_chunks = [
            DocumentChunk(
                document_id="accessibility-code",
                chunk_index=0,
                text="Door width for accessibility must be minimum 850mm clear opening",
                start_position=0,
                end_position=67
            )
        ]
        
        # Mock building rules
        from app.models.documents import BuildingRule
        building_rules = [
            BuildingRule(
                category="accessibility",
                rule_text="Minimum door width shall be 850mm for wheelchair access",
                numeric_value=850,
                unit="mm",
                confidence=0.95,
                source_section="4.2.3"
            )
        ]
        
        with patch.object(rag_service, 'similarity_search', return_value=relevant_chunks):
            with patch.object(rag_service, '_get_relevant_building_rules', return_value=building_rules):
                
                context = await rag_service.create_rag_context(query)
                
                # Assertions
                assert len(context.relevant_chunks) > 0
                assert len(context.building_rules) > 0
                assert context.building_rules[0].numeric_value == 850
                assert context.building_rules[0].unit == "mm"
                assert "accessibility" in context.building_rules[0].category