"""
Document Service Implementation for ArchBuilder.AI
Handles multi-format document processing (DWG/DXF, IFC, PDF) with validation,
metadata extraction, and secure file management
"""

import os
import asyncio
import hashlib
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, BinaryIO, Tuple
import structlog
import aiofiles
from pydantic import ValidationError

from app.models.documents import (
    DocumentUploadRequest,
    DocumentUploadResponse,
    DocumentProcessingRequest,
    DocumentProcessingResponse,
    DocumentMetadata,
    DocumentType,
    DocumentStatus,
    ProcessingStatus,
    DocumentValidationResult
)
from app.core.exceptions import (
    DocumentServiceException,
    DocumentValidationException,
    DocumentProcessingException,
    SecurityException,
    StorageException
)
from app.core.config import settings
from app.documents.parsers.dwg_parser import DWGParser
from app.documents.parsers.pdf_parser import PDFParser  
from app.documents.parsers.ifc_parser import IFCParser
from app.documents.extractors.content_extractor import ContentExtractor
from app.documents.validation.document_validator import DocumentValidator
from app.services.rag_service import RAGService
from app.utils.security import SecurityUtils
from app.utils.cache import AsyncCache
from app.utils.performance import PerformanceTracker

logger = structlog.get_logger(__name__)


class FileUploadHandler:
    """Secure file upload handling with validation and virus scanning"""
    
    def __init__(self, upload_path: str, max_file_size: int = 100 * 1024 * 1024):  # 100MB default
        self.upload_path = Path(upload_path)
        self.max_file_size = max_file_size
        self.upload_path.mkdir(parents=True, exist_ok=True)
        
        # Allowed file types and their MIME types
        self.allowed_extensions = {
            '.dwg': ['application/acad', 'application/autocad', 'application/dwg'],
            '.dxf': ['application/dxf', 'text/plain'],
            '.ifc': ['application/ifc', 'text/plain', 'application/step'],
            '.pdf': ['application/pdf'],
            '.txt': ['text/plain'],
            '.doc': ['application/msword'],
            '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        }
    
    async def validate_upload(
        self,
        file_data: bytes,
        filename: str,
        correlation_id: str
    ) -> DocumentValidationResult:
        """Comprehensive file validation before processing"""
        
        logger.info(
            "Validating file upload",
            filename=filename,
            file_size=len(file_data),
            correlation_id=correlation_id
        )
        
        errors = []
        warnings = []
        
        # File size validation
        if len(file_data) > self.max_file_size:
            errors.append(f"File size {len(file_data)} exceeds maximum {self.max_file_size} bytes")
        
        if len(file_data) == 0:
            errors.append("File is empty")
        
        # Filename validation
        if not filename or len(filename.strip()) == 0:
            errors.append("Invalid filename")
        
        # Extension validation
        file_extension = Path(filename).suffix.lower()
        if file_extension not in self.allowed_extensions:
            errors.append(f"Unsupported file type: {file_extension}")
        else:
            # MIME type validation
            detected_mime = mimetypes.guess_type(filename)[0]
            allowed_mimes = self.allowed_extensions[file_extension]
            
            if detected_mime and detected_mime not in allowed_mimes:
                warnings.append(f"MIME type {detected_mime} unusual for {file_extension}")
        
        # Basic malware signature check
        security_issues = await self._basic_security_scan(file_data, filename, correlation_id)
        errors.extend(security_issues)
        
        # File format validation
        format_issues = await self._validate_file_format(file_data, file_extension, correlation_id)
        errors.extend(format_issues.get('errors', []))
        warnings.extend(format_issues.get('warnings', []))
        
        is_valid = len(errors) == 0
        confidence_score = 1.0 - (len(errors) * 0.3 + len(warnings) * 0.1)
        confidence_score = max(0.0, min(1.0, confidence_score))
        
        logger.info(
            "File validation completed",
            filename=filename,
            is_valid=is_valid,
            error_count=len(errors),
            warning_count=len(warnings),
            confidence=confidence_score,
            correlation_id=correlation_id
        )
        
        return DocumentValidationResult(
            is_valid=is_valid,
            confidence_score=confidence_score,
            validation_errors=errors,
            validation_warnings=warnings,
            file_type=self._detect_file_type(file_extension),
            estimated_processing_time_ms=self._estimate_processing_time(len(file_data), file_extension)
        )
    
    async def _basic_security_scan(
        self,
        file_data: bytes,
        filename: str,
        correlation_id: str
    ) -> List[str]:
        """Basic security scanning for malicious content"""
        
        issues = []
        
        # Check for suspicious file signatures
        malicious_signatures = [
            b'\x4d\x5a',  # PE executable header
            b'\x50\x4b\x03\x04',  # ZIP file (could contain malware)
            b'<script',  # Embedded JavaScript
            b'javascript:',  # JavaScript protocol
            b'vbscript:',  # VBScript protocol
        ]
        
        file_data_lower = file_data.lower()
        for signature in malicious_signatures:
            if signature in file_data_lower:
                issues.append(f"Suspicious content detected in {filename}")
                break
        
        # Check file size vs declared type
        file_extension = Path(filename).suffix.lower()
        if file_extension in ['.txt', '.dxf'] and len(file_data) > 50 * 1024 * 1024:  # 50MB
            issues.append(f"Unusually large text file: {filename}")
        
        # Check for embedded executables in CAD files
        if file_extension in ['.dwg', '.dxf'] and b'\x4d\x5a' in file_data:
            issues.append(f"Potential embedded executable in CAD file: {filename}")
        
        if issues:
            logger.warning(
                "Security issues detected",
                filename=filename,
                issues=issues,
                correlation_id=correlation_id
            )
        
        return issues
    
    async def _validate_file_format(
        self,
        file_data: bytes,
        file_extension: str,
        correlation_id: str
    ) -> Dict[str, List[str]]:
        """Validate file format integrity"""
        
        errors = []
        warnings = []
        
        try:
            if file_extension == '.pdf':
                # Basic PDF header check
                if not file_data.startswith(b'%PDF-'):
                    errors.append("Invalid PDF header")
                elif len(file_data) < 1000:
                    warnings.append("PDF file appears very small")
            
            elif file_extension == '.dwg':
                # DWG format has version identifier at beginning
                if len(file_data) < 6:
                    errors.append("DWG file too small to be valid")
                else:
                    version_header = file_data[:6]
                    if not version_header.startswith(b'AC10'):
                        warnings.append("Unusual DWG version header")
            
            elif file_extension == '.dxf':
                # DXF files are text-based, check for typical header
                if len(file_data) > 0:
                    text_start = file_data[:1000].decode('utf-8', errors='ignore')
                    if 'SECTION' not in text_start and 'HEADER' not in text_start:
                        warnings.append("DXF file missing typical section headers")
            
            elif file_extension == '.ifc':
                # IFC files start with ISO-10303 header
                if len(file_data) > 0:
                    text_start = file_data[:100].decode('utf-8', errors='ignore')
                    if not text_start.startswith('ISO-10303'):
                        warnings.append("IFC file missing ISO-10303 header")
        
        except Exception as e:
            logger.warning(
                "File format validation error",
                error=str(e),
                extension=file_extension,
                correlation_id=correlation_id
            )
            warnings.append(f"Could not validate {file_extension} format: {str(e)}")
        
        return {"errors": errors, "warnings": warnings}
    
    def _detect_file_type(self, file_extension: str) -> DocumentType:
        """Detect document type from file extension"""
        
        extension_mapping = {
            '.dwg': DocumentType.DWG,
            '.dxf': DocumentType.DXF, 
            '.ifc': DocumentType.IFC,
            '.pdf': DocumentType.PDF,
            '.txt': DocumentType.TEXT,
            '.doc': DocumentType.DOCUMENT,
            '.docx': DocumentType.DOCUMENT
        }
        
        return extension_mapping.get(file_extension.lower(), DocumentType.UNKNOWN)
    
    def _estimate_processing_time(self, file_size: int, file_extension: str) -> int:
        """Estimate processing time based on file type and size"""
        
        # Base processing times in milliseconds per MB
        processing_rates = {
            '.pdf': 2000,    # 2 seconds per MB
            '.dwg': 5000,    # 5 seconds per MB (complex parsing)
            '.dxf': 3000,    # 3 seconds per MB
            '.ifc': 4000,    # 4 seconds per MB
            '.txt': 500,     # 0.5 seconds per MB
            '.doc': 1000,    # 1 second per MB
            '.docx': 1000
        }
        
        file_size_mb = file_size / (1024 * 1024)
        rate = processing_rates.get(file_extension.lower(), 3000)
        
        return int(file_size_mb * rate)
    
    async def save_uploaded_file(
        self,
        file_data: bytes,
        filename: str,
        correlation_id: str
    ) -> Tuple[str, DocumentMetadata]:
        """Save uploaded file securely with metadata generation"""
        
        # Generate secure filename
        file_hash = hashlib.sha256(file_data).hexdigest()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file_hash[:8]}_{Path(filename).name}"
        file_path = self.upload_path / safe_filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_data)
        
        # Generate metadata
        metadata = DocumentMetadata(
            filename=filename,
            original_filename=filename,
            file_size_bytes=len(file_data),
            file_type=self._detect_file_type(Path(filename).suffix),
            mime_type=mimetypes.guess_type(filename)[0] or "application/octet-stream",
            file_hash=file_hash,
            upload_timestamp=datetime.utcnow(),
            storage_path=str(file_path),
            processing_status=ProcessingStatus.PENDING
        )
        
        logger.info(
            "File saved successfully",
            original_filename=filename,
            saved_path=str(file_path),
            file_size=len(file_data),
            correlation_id=correlation_id
        )
        
        return str(file_path), metadata


class DocumentParser:
    """Multi-format document parser with content extraction"""
    
    def __init__(self):
        self.dwg_parser = DWGParser()
        self.pdf_parser = PDFParser()
        self.ifc_parser = IFCParser()
        self.content_extractor = ContentExtractor()
    
    async def parse_document(
        self,
        file_path: str,
        document_type: DocumentType,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Parse document and extract structured content"""
        
        logger.info(
            "Starting document parsing",
            file_path=file_path,
            document_type=document_type.value,
            correlation_id=correlation_id
        )
        
        try:
            if document_type == DocumentType.DWG:
                content = await self._parse_dwg(file_path, correlation_id)
            elif document_type == DocumentType.DXF:
                content = await self._parse_dxf(file_path, correlation_id)
            elif document_type == DocumentType.IFC:
                content = await self._parse_ifc(file_path, correlation_id)
            elif document_type == DocumentType.PDF:
                content = await self._parse_pdf(file_path, correlation_id)
            elif document_type == DocumentType.TEXT:
                content = await self._parse_text(file_path, correlation_id)
            else:
                content = await self._parse_generic(file_path, correlation_id)
            
            # Extract additional metadata
            content["extraction_metadata"] = {
                "parser_version": "1.0",
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "correlation_id": correlation_id,
                "confidence_score": content.get("confidence", 0.8)
            }
            
            logger.info(
                "Document parsing completed",
                file_path=file_path,
                content_sections=len(content.get("sections", [])),
                entities_count=len(content.get("entities", [])),
                correlation_id=correlation_id
            )
            
            return content
            
        except Exception as e:
            logger.error(
                "Document parsing failed",
                file_path=file_path,
                document_type=document_type.value,
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            raise DocumentProcessingException(
                f"Failed to parse {document_type.value} document",
                "DOCUMENT_PARSING_FAILED",
                correlation_id,
                inner_exception=e
            )
    
    async def _parse_dwg(self, file_path: str, correlation_id: str) -> Dict[str, Any]:
        """Parse DWG file using ezdxf library"""
        
        try:
            return await self.dwg_parser.parse(file_path, correlation_id)
        except Exception as e:
            logger.warning(
                "DWG parsing failed, attempting basic extraction",
                error=str(e),
                correlation_id=correlation_id
            )
            # Fallback to basic file analysis
            return await self._parse_generic(file_path, correlation_id)
    
    async def _parse_dxf(self, file_path: str, correlation_id: str) -> Dict[str, Any]:
        """Parse DXF file using ezdxf library"""
        
        try:
            import ezdxf
            
            # Load DXF document
            doc = ezdxf.readfile(file_path)
            
            entities = []
            layers = []
            blocks = []
            
            # Extract entities from model space
            msp = doc.modelspace()
            for entity in msp:
                entity_data = {
                    "type": entity.dxftype(),
                    "layer": entity.dxf.layer,
                    "color": getattr(entity.dxf, 'color', None),
                    "linetype": getattr(entity.dxf, 'linetype', None)
                }
                
                # Extract geometry based on entity type
                if entity.dxftype() == 'LINE':
                    entity_data["start"] = list(entity.dxf.start)
                    entity_data["end"] = list(entity.dxf.end)
                elif entity.dxftype() == 'CIRCLE':
                    entity_data["center"] = list(entity.dxf.center)
                    entity_data["radius"] = entity.dxf.radius
                elif entity.dxftype() == 'ARC':
                    entity_data["center"] = list(entity.dxf.center)
                    entity_data["radius"] = entity.dxf.radius
                    entity_data["start_angle"] = entity.dxf.start_angle
                    entity_data["end_angle"] = entity.dxf.end_angle
                elif entity.dxftype() == 'TEXT':
                    entity_data["text"] = entity.dxf.text
                    entity_data["insert"] = list(entity.dxf.insert)
                    entity_data["height"] = entity.dxf.height
                
                entities.append(entity_data)
            
            # Extract layers
            for layer in doc.layers:
                layers.append({
                    "name": layer.dxf.name,
                    "color": layer.dxf.color,
                    "linetype": layer.dxf.linetype,
                    "on": not layer.is_off(),
                    "frozen": layer.is_frozen(),
                    "locked": layer.is_locked()
                })
            
            # Extract blocks
            for block in doc.blocks:
                if not block.name.startswith('*'):  # Skip anonymous blocks
                    block_entities = []
                    for entity in block:
                        block_entities.append({
                            "type": entity.dxftype(),
                            "layer": entity.dxf.layer
                        })
                    
                    blocks.append({
                        "name": block.name,
                        "entities": block_entities
                    })
            
            logger.info(
                "DXF parsing successful",
                entities_count=len(entities),
                layers_count=len(layers),
                blocks_count=len(blocks),
                correlation_id=correlation_id
            )
            
            return {
                "format": "DXF",
                "version": doc.dxfversion,
                "entities": entities,
                "layers": layers,
                "blocks": blocks,
                "units": doc.units,
                "confidence": 0.95,
                "architectural_elements": self._extract_architectural_elements(entities)
            }
            
        except Exception as e:
            logger.error(
                "DXF parsing failed",
                error=str(e),
                correlation_id=correlation_id
            )
            raise
    
    async def _parse_ifc(self, file_path: str, correlation_id: str) -> Dict[str, Any]:
        """Parse IFC file using ifcopenshell"""
        
        try:
            return await self.ifc_parser.parse(file_path, correlation_id)
        except Exception as e:
            logger.warning(
                "IFC parsing failed, attempting text extraction",
                error=str(e),
                correlation_id=correlation_id
            )
            # Fallback to text parsing
            return await self._parse_text(file_path, correlation_id)
    
    async def _parse_pdf(self, file_path: str, correlation_id: str) -> Dict[str, Any]:
        """Parse PDF file for building codes and regulations"""
        
        try:
            return await self.pdf_parser.parse(file_path, correlation_id)
        except Exception as e:
            logger.error(
                "PDF parsing failed",
                error=str(e),
                correlation_id=correlation_id
            )
            raise
    
    async def _parse_text(self, file_path: str, correlation_id: str) -> Dict[str, Any]:
        """Parse text file"""
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # Basic text analysis
            lines = content.split('\n')
            words = content.split()
            
            # Try to detect if it's building code content
            building_code_indicators = [
                'building code', 'regulation', 'code section', 'article',
                'yapı yönetmeliği', 'madde', 'bölüm', 'yönetmelik',
                'bauordnung', 'baugesetzbuch', 'din norm'
            ]
            
            is_building_code = any(
                indicator in content.lower() 
                for indicator in building_code_indicators
            )
            
            return {
                "format": "TEXT",
                "content": content,
                "line_count": len(lines),
                "word_count": len(words),
                "character_count": len(content),
                "is_building_code": is_building_code,
                "language": self._detect_language(content),
                "confidence": 0.9 if len(content) > 100 else 0.7,
                "sections": self._extract_text_sections(content)
            }
            
        except UnicodeDecodeError:
            # Try different encodings
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
                        content = await f.read()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise DocumentProcessingException(
                    "Unable to decode text file with any supported encoding",
                    "TEXT_ENCODING_ERROR",
                    correlation_id
                )
    
    async def _parse_generic(self, file_path: str, correlation_id: str) -> Dict[str, Any]:
        """Generic file parsing for unknown formats"""
        
        file_stat = os.stat(file_path)
        
        return {
            "format": "UNKNOWN",
            "file_size": file_stat.st_size,
            "modified_time": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            "confidence": 0.5,
            "content": "Binary file - content extraction not supported"
        }
    
    def _extract_architectural_elements(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract architectural elements from CAD entities"""
        
        walls = []
        doors = []
        windows = []
        rooms = []
        
        # Group entities by layer to identify architectural elements
        layer_entities = {}
        for entity in entities:
            layer = entity.get("layer", "0")
            if layer not in layer_entities:
                layer_entities[layer] = []
            layer_entities[layer].append(entity)
        
        # Identify walls (typically lines on wall layers)
        wall_layers = [layer for layer in layer_entities.keys() 
                      if any(keyword in layer.lower() for keyword in ['wall', 'duvar', 'wand'])]
        
        for layer in wall_layers:
            for entity in layer_entities[layer]:
                if entity["type"] == "LINE":
                    walls.append({
                        "start_point": entity["start"],
                        "end_point": entity["end"],
                        "layer": layer,
                        "length": self._calculate_line_length(entity["start"], entity["end"])
                    })
        
        # Identify doors and windows (typically blocks or circles on specific layers)
        door_layers = [layer for layer in layer_entities.keys() 
                      if any(keyword in layer.lower() for keyword in ['door', 'kapı', 'tür'])]
        
        window_layers = [layer for layer in layer_entities.keys() 
                        if any(keyword in layer.lower() for keyword in ['window', 'pencere', 'fenster'])]
        
        return {
            "walls": walls,
            "doors": doors,
            "windows": windows,
            "rooms": rooms,
            "total_wall_length": sum(wall.get("length", 0) for wall in walls)
        }
    
    def _calculate_line_length(self, start: List[float], end: List[float]) -> float:
        """Calculate length of a line between two points"""
        
        import math
        
        if len(start) >= 2 and len(end) >= 2:
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            return math.sqrt(dx*dx + dy*dy)
        
        return 0.0
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection for text content"""
        
        text_lower = text.lower()
        
        # Turkish indicators
        turkish_words = ['yapı', 'bina', 'madde', 'yönetmelik', 'bölüm', 'türkiye']
        if any(word in text_lower for word in turkish_words):
            return "tr"
        
        # German indicators  
        german_words = ['bau', 'ordnung', 'gebäude', 'norm', 'deutschland']
        if any(word in text_lower for word in german_words):
            return "de"
        
        # Default to English
        return "en"
    
    def _extract_text_sections(self, content: str) -> List[Dict[str, str]]:
        """Extract sections from text content"""
        
        sections = []
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            
            # Check if line looks like a section header
            if (line and 
                (line.isupper() or 
                 line.startswith(('Chapter', 'Section', 'Article', 'Bölüm', 'Madde', 'Artikel')) or
                 any(char.isdigit() for char in line[:5]))):
                
                # Save previous section
                if current_section:
                    sections.append({
                        "title": current_section,
                        "content": '\n'.join(current_content).strip()
                    })
                
                # Start new section
                current_section = line
                current_content = []
            else:
                if line:  # Skip empty lines
                    current_content.append(line)
        
        # Save last section
        if current_section:
            sections.append({
                "title": current_section,
                "content": '\n'.join(current_content).strip()
            })
        
        return sections


class DocumentService:
    """Comprehensive document processing service with multi-format support"""
    
    def __init__(
        self,
        rag_service: Optional[RAGService] = None,
        cache: Optional[AsyncCache] = None,
        performance_tracker: Optional[PerformanceTracker] = None,
        upload_path: str = "./uploads"
    ):
        self.rag_service = rag_service
        self.cache = cache
        self.performance_tracker = performance_tracker
        
        # Initialize components
        self.upload_handler = FileUploadHandler(upload_path)
        self.parser = DocumentParser()
        self.validator = DocumentValidator() if hasattr(self, 'DocumentValidator') else None
        
        # Document storage
        self.documents: Dict[str, DocumentMetadata] = {}
        
        logger.info("Document Service initialized")
    
    async def upload_document(
        self,
        request: DocumentUploadRequest,
        correlation_id: str
    ) -> DocumentUploadResponse:
        """Upload and validate document with comprehensive processing"""
        
        start_time = datetime.utcnow()
        
        logger.info(
            "Starting document upload",
            filename=request.filename,
            file_size=len(request.file_data) if request.file_data else 0,
            correlation_id=correlation_id
        )
        
        try:
            # Validate upload
            validation_result = await self.upload_handler.validate_upload(
                request.file_data,
                request.filename,
                correlation_id
            )
            
            if not validation_result.is_valid:
                raise DocumentValidationException(
                    "Document validation failed",
                    "DOCUMENT_VALIDATION_FAILED", 
                    correlation_id,
                    validation_errors=validation_result.validation_errors
                )
            
            # Save file
            file_path, metadata = await self.upload_handler.save_uploaded_file(
                request.file_data,
                request.filename,
                correlation_id
            )
            
            # Generate document ID
            document_id = f"doc_{hashlib.md5(f'{correlation_id}_{file_path}'.encode()).hexdigest()[:16]}"
            
            # Store metadata
            metadata.document_id = document_id
            metadata.upload_timestamp = start_time
            metadata.processing_status = ProcessingStatus.UPLOADED
            
            self.documents[document_id] = metadata
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info(
                "Document upload completed",
                document_id=document_id,
                filename=request.filename,
                processing_time_ms=processing_time,
                correlation_id=correlation_id
            )
            
            return DocumentUploadResponse(
                document_id=document_id,
                correlation_id=correlation_id,
                status=DocumentStatus.UPLOADED,
                metadata=metadata,
                validation_result=validation_result,
                processing_time_ms=int(processing_time),
                upload_timestamp=start_time
            )
            
        except Exception as e:
            logger.error(
                "Document upload failed",
                filename=request.filename,
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            
            return DocumentUploadResponse(
                document_id="",
                correlation_id=correlation_id,
                status=DocumentStatus.FAILED,
                error_message=str(e),
                processing_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                upload_timestamp=start_time
            )
    
    async def process_document(
        self,
        request: DocumentProcessingRequest,
        correlation_id: str
    ) -> DocumentProcessingResponse:
        """Process document with content extraction and RAG integration"""
        
        start_time = datetime.utcnow()
        
        logger.info(
            "Starting document processing",
            document_id=request.document_id,
            processing_type=request.processing_type,
            correlation_id=correlation_id
        )
        
        try:
            # Get document metadata
            if request.document_id not in self.documents:
                raise DocumentServiceException(
                    f"Document {request.document_id} not found",
                    "DOCUMENT_NOT_FOUND",
                    correlation_id
                )
            
            metadata = self.documents[request.document_id]
            
            # Update status
            metadata.processing_status = ProcessingStatus.PROCESSING
            
            # Parse document content
            parsed_content = await self.parser.parse_document(
                metadata.storage_path,
                metadata.file_type,
                correlation_id
            )
            
            # Process with RAG if available
            rag_processed = False
            if self.rag_service and request.enable_rag:
                try:
                    await self._process_with_rag(
                        parsed_content,
                        metadata,
                        correlation_id
                    )
                    rag_processed = True
                except Exception as e:
                    logger.warning(
                        "RAG processing failed, continuing without it",
                        error=str(e),
                        correlation_id=correlation_id
                    )
            
            # Update metadata
            metadata.processing_status = ProcessingStatus.COMPLETED
            metadata.processed_content = parsed_content
            metadata.rag_processed = rag_processed
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info(
                "Document processing completed",
                document_id=request.document_id,
                content_sections=len(parsed_content.get("sections", [])),
                rag_processed=rag_processed,
                processing_time_ms=processing_time,
                correlation_id=correlation_id
            )
            
            return DocumentProcessingResponse(
                document_id=request.document_id,
                correlation_id=correlation_id,
                status=ProcessingStatus.COMPLETED,
                extracted_content=parsed_content,
                metadata=metadata,
                rag_processed=rag_processed,
                processing_time_ms=int(processing_time),
                processed_timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(
                "Document processing failed",
                document_id=request.document_id,
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            
            # Update status
            if request.document_id in self.documents:
                self.documents[request.document_id].processing_status = ProcessingStatus.FAILED
            
            return DocumentProcessingResponse(
                document_id=request.document_id,
                correlation_id=correlation_id,
                status=ProcessingStatus.FAILED,
                error_message=str(e),
                processing_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
                processed_timestamp=datetime.utcnow()
            )
    
    async def _process_with_rag(
        self,
        parsed_content: Dict[str, Any],
        metadata: DocumentMetadata,
        correlation_id: str
    ):
        """Process document content with RAG service"""
        
        try:
            # Extract text content for RAG processing
            text_content = ""
            
            if "content" in parsed_content:
                text_content = parsed_content["content"]
            elif "sections" in parsed_content:
                sections = parsed_content["sections"]
                text_content = "\n\n".join([
                    f"{section.get('title', '')}\n{section.get('content', '')}"
                    for section in sections
                ])
            
            if text_content and len(text_content.strip()) > 0:
                # Send to RAG service for indexing
                await self.rag_service.index_document(
                    document_id=metadata.document_id,
                    content=text_content,
                    metadata={
                        "filename": metadata.filename,
                        "file_type": metadata.file_type.value,
                        "language": parsed_content.get("language", "en"),
                        "is_building_code": parsed_content.get("is_building_code", False)
                    },
                    correlation_id=correlation_id
                )
                
                logger.info(
                    "Document indexed in RAG system",
                    document_id=metadata.document_id,
                    content_length=len(text_content),
                    correlation_id=correlation_id
                )
            else:
                logger.warning(
                    "No text content extracted for RAG processing",
                    document_id=metadata.document_id,
                    correlation_id=correlation_id
                )
                
        except Exception as e:
            logger.error(
                "RAG processing failed",
                document_id=metadata.document_id,
                error=str(e),
                correlation_id=correlation_id
            )
            raise
    
    async def get_document_metadata(
        self,
        document_id: str,
        correlation_id: str
    ) -> Optional[DocumentMetadata]:
        """Get document metadata by ID"""
        
        logger.info(
            "Retrieving document metadata",
            document_id=document_id,
            correlation_id=correlation_id
        )
        
        return self.documents.get(document_id)
    
    async def list_documents(
        self,
        user_id: Optional[str] = None,
        document_type: Optional[DocumentType] = None,
        status: Optional[ProcessingStatus] = None,
        correlation_id: Optional[str] = None
    ) -> List[DocumentMetadata]:
        """List documents with optional filtering"""
        
        logger.info(
            "Listing documents",
            user_id=user_id,
            document_type=document_type.value if document_type else None,
            status=status.value if status else None,
            correlation_id=correlation_id
        )
        
        documents = list(self.documents.values())
        
        # Apply filters
        if document_type:
            documents = [doc for doc in documents if doc.file_type == document_type]
        
        if status:
            documents = [doc for doc in documents if doc.processing_status == status]
        
        # Sort by upload timestamp (newest first)
        documents.sort(key=lambda x: x.upload_timestamp, reverse=True)
        
        return documents
    
    async def delete_document(
        self,
        document_id: str,
        correlation_id: str
    ) -> bool:
        """Delete document and cleanup files"""
        
        logger.info(
            "Deleting document",
            document_id=document_id,
            correlation_id=correlation_id
        )
        
        try:
            if document_id not in self.documents:
                return False
            
            metadata = self.documents[document_id]
            
            # Delete file from storage
            if os.path.exists(metadata.storage_path):
                os.remove(metadata.storage_path)
            
            # Remove from RAG if indexed
            if self.rag_service and metadata.rag_processed:
                try:
                    await self.rag_service.remove_document(document_id, correlation_id)
                except Exception as e:
                    logger.warning(
                        "Failed to remove document from RAG",
                        document_id=document_id,
                        error=str(e),
                        correlation_id=correlation_id
                    )
            
            # Remove from memory
            del self.documents[document_id]
            
            logger.info(
                "Document deleted successfully",
                document_id=document_id,
                correlation_id=correlation_id
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Document deletion failed",
                document_id=document_id,
                error=str(e),
                correlation_id=correlation_id,
                exc_info=True
            )
            return False
    
    async def get_document_content(
        self,
        document_id: str,
        correlation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get processed document content"""
        
        logger.info(
            "Retrieving document content",
            document_id=document_id,
            correlation_id=correlation_id
        )
        
        if document_id not in self.documents:
            return None
        
        metadata = self.documents[document_id]
        
        if hasattr(metadata, 'processed_content') and metadata.processed_content:
            return metadata.processed_content
        
        # If not processed yet, return None
        return None
    
    async def get_processing_status(
        self,
        document_id: str,
        correlation_id: str
    ) -> Optional[ProcessingStatus]:
        """Get document processing status"""
        
        if document_id not in self.documents:
            return None
        
        return self.documents[document_id].processing_status
    
    async def shutdown(self):
        """Cleanup resources on shutdown"""
        
        logger.info("Shutting down Document Service")
        
        # Could add cleanup of temporary files, database connections, etc.
        
        logger.info("Document Service shutdown complete")