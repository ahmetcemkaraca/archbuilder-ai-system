"""
Document Processing Pipeline for ArchBuilder.AI
Handles parsing of DWG/DXF, IFC, PDF and other architectural file formats
"""

import asyncio
import os
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, BinaryIO
import mimetypes
import tempfile

from app.core.logging import get_logger, log_file_operation, log_validation_result
from app.models.documents import (
    DocumentMetadata, 
    ProcessingResult, 
    ProcessingStatus,
    DocumentType
)

logger = get_logger(__name__)


class ProcessingPriority(str, Enum):
    """Document processing priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class DocumentProcessor:
    """Main document processing coordinator"""
    
    def __init__(self):
        self.processors = {
            DocumentType.PDF: PDFProcessor(),
            DocumentType.DWG: DWGProcessor(),
            DocumentType.DXF: DXFProcessor(),
            DocumentType.IFC: IFCProcessor(),
            DocumentType.RVT: RevitProcessor(),
            DocumentType.TEXT: TextProcessor()
        }
        self.logger = get_logger(__name__)
    
    async def process_document(self, 
                             file_path: Path,
                             processing_options: Optional[Dict[str, Any]] = None,
                             priority: ProcessingPriority = ProcessingPriority.NORMAL,
                             correlation_id: Optional[str] = None) -> ProcessingResult:
        """Process a document and extract content"""
        
        if correlation_id is None:
            correlation_id = f"doc-{uuid.uuid4().hex[:8]}"
        
        processing_options = processing_options or {}
        
        self.logger.info(
            "Starting document processing",
            correlation_id=correlation_id,
            file_path=str(file_path),
            priority=priority
        )
        
        try:
            # Detect file format
            file_format = self._detect_file_format(file_path)
            
            if file_format is None:
                raise ValueError(f"Could not detect file format for: {file_path}")
            
            log_file_operation(
                operation="format_detection",
                file_path=str(file_path),
                file_type=file_format.value
            )
            
            if file_format not in self.processors:
                raise ValueError(f"Unsupported file format: {file_format}")
            
            # Get appropriate processor
            processor = self.processors[file_format]
            
            # Extract metadata first
            metadata = await self._extract_metadata(file_path, file_format)
            
            # Process the document
            processing_result = await processor.process(
                file_path, 
                processing_options, 
                correlation_id
            )
            
            # Update processing result
            processing_result.processing_status = ProcessingStatus.COMPLETED
            
            log_validation_result(
                validation_type="document_processing",
                passed=True,
                details={
                    "file_format": file_format.value,
                    "confidence": processing_result.confidence_score,
                    "content_length": len(processing_result.extracted_text or "")
                }
            )
            
            self.logger.info(
                "Document processing completed",
                correlation_id=correlation_id,
                confidence=processing_result.confidence_score,
                extracted_text_length=len(processing_result.extracted_text or "")
            )
            
            return processing_result
            
        except Exception as e:
            self.logger.error(
                "Document processing failed",
                correlation_id=correlation_id,
                error=str(e),
                file_path=str(file_path)
            )
            
            return ProcessingResult(
                document_id=correlation_id,
                correlation_id=correlation_id,
                processing_status=ProcessingStatus.FAILED,
                error_messages=[f"Processing failed: {str(e)}"],
                confidence_score=0.0,
                processing_time_ms=0
            )
    
    def _detect_file_format(self, file_path: Path) -> Optional[DocumentType]:
        """Detect file format from extension and content"""
        
        # Check by extension first
        extension = file_path.suffix.lower()
        extension_map = {
            '.pdf': DocumentType.PDF,
            '.dwg': DocumentType.DWG,
            '.dxf': DocumentType.DXF,
            '.ifc': DocumentType.IFC,
            '.rvt': DocumentType.RVT,
            '.txt': DocumentType.TEXT
        }
        
        if extension in extension_map:
            return extension_map[extension]
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            mime_map = {
                'application/pdf': DocumentType.PDF,
                'text/plain': DocumentType.TEXT
            }
            
            if mime_type in mime_map:
                return mime_map[mime_type]
        
        return None
    
    async def _extract_metadata(self, file_path: Path, file_format: DocumentType) -> DocumentMetadata:
        """Extract basic file metadata"""
        
        stat = file_path.stat()
        
        # Calculate checksum
        checksum = await self._calculate_checksum(file_path)
        
        return DocumentMetadata(
            filename=file_path.name,
            file_type=file_format,
            file_size_bytes=stat.st_size,
            content_hash=checksum
        )
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate file checksum for integrity verification"""
        import hashlib
        
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()


class BaseProcessor(ABC):
    """Base class for document processors"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    async def process(self, 
                     file_path: Path, 
                     options: Dict[str, Any],
                     correlation_id: str) -> ProcessingResult:
        """Process document and extract content"""
        pass
    
    def _create_processing_result(self, 
                                correlation_id: str,
                                text: Optional[str] = None,
                                data: Optional[Dict[str, Any]] = None,
                                confidence: float = 1.0,
                                warnings: Optional[List[str]] = None,
                                processing_time_ms: int = 0) -> ProcessingResult:
        """Create a standardized processing result"""
        
        return ProcessingResult(
            document_id=f"doc-{uuid.uuid4().hex[:8]}",
            correlation_id=correlation_id,
            processing_status=ProcessingStatus.COMPLETED,
            extracted_text=text,
            extracted_data=data,
            confidence_score=confidence,
            warnings=warnings or [],
            processing_time_ms=processing_time_ms
        )


class PDFProcessor(BaseProcessor):
    """PDF document processor using PyPDF2 and OCR"""
    
    async def process(self, 
                     file_path: Path, 
                     options: Dict[str, Any],
                     correlation_id: str) -> ProcessingResult:
        """Extract text and images from PDF"""
        
        self.logger.info("Processing PDF document", correlation_id=correlation_id)
        
        try:
            # Try PyPDF2 first for text extraction
            extracted_text = await self._extract_text_pypdf2(file_path)
            
            # If text extraction failed or returned little content, try OCR
            if not extracted_text or len(extracted_text.strip()) < 100:
                self.logger.info("Falling back to OCR for PDF", correlation_id=correlation_id)
                extracted_text = await self._extract_text_ocr(file_path)
            
            # Extract any embedded architectural drawings
            geometry_data = await self._extract_pdf_geometry(file_path)
            
            confidence = 0.9 if len(extracted_text.strip()) > 100 else 0.6
            
            return self._create_processing_result(
                correlation_id=correlation_id,
                text=extracted_text,
                data={"geometry": geometry_data},
                confidence=confidence
            )
            
        except Exception as e:
            self.logger.error("PDF processing failed", correlation_id=correlation_id, error=str(e))
            return self._create_processing_result(
                correlation_id=correlation_id,
                confidence=0.0
            )
    
    async def _extract_text_pypdf2(self, file_path: Path) -> str:
        """Extract text using PyPDF2"""
        try:
            # PyPDF2 import is optional - graceful degradation
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                return text.strip()
                
        except ImportError:
            self.logger.warning("PyPDF2 not available, skipping PDF text extraction")
            return ""
        except Exception as e:
            self.logger.warning(f"PyPDF2 extraction failed: {e}")
            return ""
    
    async def _extract_text_ocr(self, file_path: Path) -> str:
        """Extract text using OCR (placeholder for future implementation)"""
        # TODO: Implement OCR using Tesseract or cloud OCR service
        self.logger.info("OCR extraction not implemented yet")
        return ""
    
    async def _extract_pdf_geometry(self, file_path: Path) -> Dict[str, Any]:
        """Extract geometric data from PDF (placeholder)"""
        # TODO: Implement PDF geometry extraction for architectural drawings
        return {}


class DWGProcessor(BaseProcessor):
    """DWG/AutoCAD document processor"""
    
    async def process(self, 
                     file_path: Path, 
                     options: Dict[str, Any],
                     correlation_id: str) -> ProcessingResult:
        """Extract geometry and metadata from DWG files"""
        
        self.logger.info("Processing DWG document", correlation_id=correlation_id)
        
        try:
            # TODO: Implement DWG processing using ezdxf or similar library
            # For now, return basic file info
            
            geometry_data = {
                "layers": [],
                "entities": [],
                "blocks": [],
                "text_entities": []
            }
            
            # Placeholder implementation
            warnings = ["DWG processing not fully implemented yet"]
            
            return self._create_processing_result(
                correlation_id=correlation_id,
                text="DWG file processed (metadata only)",
                data={"geometry": geometry_data},
                confidence=0.5,
                warnings=warnings
            )
            
        except Exception as e:
            self.logger.error("DWG processing failed", correlation_id=correlation_id, error=str(e))
            return self._create_processing_result(
                correlation_id=correlation_id,
                confidence=0.0
            )


class DXFProcessor(BaseProcessor):
    """DXF document processor using ezdxf"""
    
    async def process(self, 
                     file_path: Path, 
                     options: Dict[str, Any],
                     correlation_id: str) -> ProcessingResult:
        """Extract geometry and text from DXF files"""
        
        self.logger.info("Processing DXF document", correlation_id=correlation_id)
        
        try:
            # Try to use ezdxf for DXF processing
            geometry_data = await self._extract_dxf_geometry(file_path)
            text_data = await self._extract_dxf_text(file_path)
            
            return self._create_processing_result(
                correlation_id=correlation_id,
                text=text_data,
                data={"geometry": geometry_data},
                confidence=0.8
            )
            
        except Exception as e:
            self.logger.error("DXF processing failed", correlation_id=correlation_id, error=str(e))
            return self._create_processing_result(
                correlation_id=correlation_id,
                confidence=0.0
            )
    
    async def _extract_dxf_geometry(self, file_path: Path) -> Dict[str, Any]:
        """Extract geometric entities from DXF"""
        try:
            # ezdxf import is optional - graceful degradation
            import ezdxf
            
            doc = ezdxf.readfile(str(file_path))
            modelspace = doc.modelspace()
            
            geometry_data = {
                "lines": [],
                "circles": [],
                "arcs": [],
                "polylines": [],
                "blocks": [],
                "layers": list(doc.layers)
            }
            
            for entity in modelspace:
                entity_type = entity.dxftype()
                
                if entity_type == "LINE":
                    geometry_data["lines"].append({
                        "start": list(entity.dxf.start),
                        "end": list(entity.dxf.end),
                        "layer": entity.dxf.layer
                    })
                elif entity_type == "CIRCLE":
                    geometry_data["circles"].append({
                        "center": list(entity.dxf.center),
                        "radius": entity.dxf.radius,
                        "layer": entity.dxf.layer
                    })
                # Add more entity types as needed
            
            return geometry_data
            
        except ImportError:
            self.logger.warning("ezdxf not available, skipping DXF geometry extraction")
            return {}
        except Exception as e:
            self.logger.warning(f"DXF geometry extraction failed: {e}")
            return {}
    
    async def _extract_dxf_text(self, file_path: Path) -> str:
        """Extract text entities from DXF"""
        try:
            # ezdxf import is optional - graceful degradation
            import ezdxf
            
            doc = ezdxf.readfile(str(file_path))
            modelspace = doc.modelspace()
            
            text_content = []
            
            for entity in modelspace:
                if entity.dxftype() in ["TEXT", "MTEXT"]:
                    text_content.append(entity.dxf.text)
            
            return "\n".join(text_content)
            
        except ImportError:
            return ""
        except Exception as e:
            self.logger.warning(f"DXF text extraction failed: {e}")
            return ""


class IFCProcessor(BaseProcessor):
    """IFC (Industry Foundation Classes) processor"""
    
    async def process(self, 
                     file_path: Path, 
                     options: Dict[str, Any],
                     correlation_id: str) -> ProcessingResult:
        """Extract BIM data from IFC files"""
        
        self.logger.info("Processing IFC document", correlation_id=correlation_id)
        
        try:
            # TODO: Implement IFC processing using ifcopenshell
            geometry_data = {
                "buildings": [],
                "storeys": [],
                "spaces": [],
                "elements": []
            }
            
            warnings = ["IFC processing not fully implemented yet"]
            
            return self._create_processing_result(
                correlation_id=correlation_id,
                text="IFC file processed (metadata only)",
                data={"geometry": geometry_data},
                confidence=0.5,
                warnings=warnings
            )
            
        except Exception as e:
            self.logger.error("IFC processing failed", correlation_id=correlation_id, error=str(e))
            return self._create_processing_result(
                correlation_id=correlation_id,
                confidence=0.0
            )


class RevitProcessor(BaseProcessor):
    """Revit file processor (limited without Revit API)"""
    
    async def process(self, 
                     file_path: Path, 
                     options: Dict[str, Any],
                     correlation_id: str) -> ProcessingResult:
        """Extract basic metadata from Revit files"""
        
        self.logger.info("Processing Revit document", correlation_id=correlation_id)
        
        try:
            # Note: Full Revit processing requires Revit API on Windows
            # This is a placeholder for metadata extraction
            
            warnings = [
                "Revit file processing requires Revit API",
                "Only metadata extraction available in cloud environment"
            ]
            
            return self._create_processing_result(
                correlation_id=correlation_id,
                text="Revit file detected (metadata only)",
                confidence=0.3,
                warnings=warnings
            )
            
        except Exception as e:
            self.logger.error("Revit processing failed", correlation_id=correlation_id, error=str(e))
            return self._create_processing_result(
                correlation_id=correlation_id,
                confidence=0.0
            )


class TextProcessor(BaseProcessor):
    """Plain text document processor"""
    
    async def process(self, 
                     file_path: Path, 
                     options: Dict[str, Any],
                     correlation_id: str) -> ProcessingResult:
        """Process plain text files"""
        
        self.logger.info("Processing text document", correlation_id=correlation_id)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            return self._create_processing_result(
                correlation_id=correlation_id,
                text=text_content,
                confidence=1.0
            )
            
        except Exception as e:
            self.logger.error("Text processing failed", correlation_id=correlation_id, error=str(e))
            return self._create_processing_result(
                correlation_id=correlation_id,
                confidence=0.0
            )


# Utility functions for batch processing
async def batch_process_documents(document_paths: List[Path], 
                                processor: DocumentProcessor,
                                max_concurrent: int = 5) -> List[ProcessingResult]:
    """Process multiple documents concurrently"""
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_single(path: Path) -> ProcessingResult:
        async with semaphore:
            return await processor.process_document(path)
    
    tasks = [process_single(path) for path in document_paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Convert exceptions to failed results
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final_results.append(ProcessingResult(
                document_id=f"batch-{i}",
                correlation_id=f"batch-{i}",
                processing_status=ProcessingStatus.FAILED,
                error_messages=[str(result)],
                confidence_score=0.0,
                processing_time_ms=0
            ))
        else:
            final_results.append(result)
    
    return final_results