"""
Unit tests for Document Service functionality
Tests document processing, parsing, and RAG preparation
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from pathlib import Path
from typing import Dict, Any, List
import io
import uuid

from app.services.document_service import DocumentService
from app.models.documents import (
    DocumentUpload, DocumentMetadata, DocumentType, ProcessingStatus,
    ProcessingResult, DocumentChunk, CADDrawing, IFCModel,
    BuildingCodeDocument, BuildingRule
)


class TestDocumentService:
    """Test Document Service main functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.document_service = DocumentService()
    
    @pytest.mark.asyncio
    async def test_upload_document_success(self):
        """Test successful document upload"""
        # Mock file content
        file_content = b"Mock DWG file content"
        mock_file = io.BytesIO(file_content)
        
        # Create metadata
        metadata = DocumentMetadata(
            filename="test_drawing.dwg",
            file_type=DocumentType.DWG,
            file_size_bytes=len(file_content),
            content_hash="a" * 64,  # Mock SHA-256 hash
            mime_type="application/dwg"
        )
        
        upload_request = DocumentUpload(
            metadata=metadata,
            processing_options={"extract_dimensions": True}
        )
        
        # Mock successful processing
        with patch.object(self.document_service, '_process_dwg_document') as mock_process:
            mock_process.return_value = ProcessingResult(
                document_id=upload_request.id,
                correlation_id=upload_request.correlation_id,
                processing_status=ProcessingStatus.COMPLETED,
                confidence_score=0.95,
                processing_time_ms=1500,
                cad_drawing=CADDrawing(
                    filename="test_drawing.dwg",
                    file_type="dwg",
                    units="millimeters",
                    processing_status=ProcessingStatus.COMPLETED
                )
            )
            
            result = await self.document_service.upload_document(upload_request, mock_file, "user123")
            
            # Assertions
            assert result.processing_status == ProcessingStatus.COMPLETED
            assert result.confidence_score == 0.95
            assert result.cad_drawing is not None
            assert result.cad_drawing.file_type == "dwg"
            assert len(result.error_messages) == 0
    
    @pytest.mark.asyncio
    async def test_upload_document_parsing_error(self):
        """Test document upload with parsing error"""
        # Mock file content
        file_content = b"Invalid DWG content"
        mock_file = io.BytesIO(file_content)
        
        metadata = DocumentMetadata(
            filename="invalid.dwg",
            file_type=DocumentType.DWG,
            file_size_bytes=len(file_content),
            content_hash="b" * 64
        )
        
        upload_request = DocumentUpload(metadata=metadata)
        
        # Mock processing failure
        with patch.object(self.document_service, '_process_dwg_document') as mock_process:
            mock_process.side_effect = Exception("Invalid DWG format")
            
            result = await self.document_service.upload_document(upload_request, mock_file, "user123")
            
            # Assertions
            assert result.processing_status == ProcessingStatus.FAILED
            assert len(result.error_messages) > 0
            assert "Invalid DWG format" in result.error_messages[0]
    
    @pytest.mark.asyncio
    async def test_upload_pdf_building_code(self):
        """Test PDF building code upload and processing"""
        # Mock PDF content
        file_content = b"Mock PDF building code content"
        mock_file = io.BytesIO(file_content)
        
        metadata = DocumentMetadata(
            filename="turkish_building_code.pdf",
            file_type=DocumentType.PDF,
            file_size_bytes=len(file_content),
            content_hash="c" * 64,
            mime_type="application/pdf"
        )
        
        upload_request = DocumentUpload(
            metadata=metadata,
            processing_options={"extract_building_rules": True}
        )
        
        # Mock PDF processing
        with patch.object(self.document_service, '_process_pdf_document') as mock_process:
            mock_process.return_value = ProcessingResult(
                document_id=upload_request.id,
                correlation_id=upload_request.correlation_id,
                processing_status=ProcessingStatus.COMPLETED,
                confidence_score=0.88,
                processing_time_ms=2500,
                extracted_text="Building code regulations for residential structures...",
                building_rules=[
                    BuildingRule(
                        category="room_sizes",
                        rule_text="Minimum ceiling height shall be 2.4 meters",
                        numeric_value=2.4,
                        unit="meters",
                        confidence=0.95,
                        source_section="3.2.1"
                    )
                ]
            )
            
            result = await self.document_service.upload_document(upload_request, mock_file, "user123")
            
            # Assertions
            assert result.processing_status == ProcessingStatus.COMPLETED
            assert "Building code regulations" in result.extracted_text
            assert len(result.building_rules) == 1
            assert result.building_rules[0].numeric_value == 2.4
            assert result.building_rules[0].unit == "meters"
    
    @pytest.mark.asyncio
    async def test_upload_ifc_model(self):
        """Test IFC model upload and processing"""
        # Mock IFC content
        file_content = b"Mock IFC model content"
        mock_file = io.BytesIO(file_content)
        
        metadata = DocumentMetadata(
            filename="building_model.ifc",
            file_type=DocumentType.IFC,
            file_size_bytes=len(file_content),
            content_hash="d" * 64,
            mime_type="application/ifc"
        )
        
        upload_request = DocumentUpload(
            metadata=metadata,
            processing_options={"extract_spaces": True, "analyze_structure": True}
        )
        
        # Mock IFC processing
        with patch.object(self.document_service, '_process_ifc_document') as mock_process:
            mock_process.return_value = ProcessingResult(
                document_id=upload_request.id,
                correlation_id=upload_request.correlation_id,
                processing_status=ProcessingStatus.COMPLETED,
                confidence_score=0.92,
                processing_time_ms=3500,
                ifc_model=IFCModel(
                    filename="building_model.ifc",
                    schema_version="IFC4",
                    processing_status=ProcessingStatus.COMPLETED
                )
            )
            
            result = await self.document_service.upload_document(upload_request, mock_file, "user123")
            
            # Assertions
            assert result.processing_status == ProcessingStatus.COMPLETED
            assert result.ifc_model is not None
            assert result.ifc_model.schema_version == "IFC4"
            assert result.confidence_score == 0.92
    
    @pytest.mark.asyncio
    async def test_get_document_by_id(self):
        """Test retrieving document by ID"""
        document_id = "doc-123"
        
        # Mock document exists
        expected_result = ProcessingResult(
            document_id=document_id,
            correlation_id="corr-123",
            processing_status=ProcessingStatus.COMPLETED,
            confidence_score=0.95,
            processing_time_ms=1000,
            cad_drawing=CADDrawing(
                filename="test.dwg",
                file_type="dwg",
                units="millimeters"
            )
        )
        
        with patch.object(self.document_service, '_get_document_from_storage', return_value=expected_result):
            result = await self.document_service.get_document(document_id)
            
            assert result.document_id == document_id
            assert result.processing_status == ProcessingStatus.COMPLETED
            assert result.cad_drawing.filename == "test.dwg"
    
    @pytest.mark.asyncio
    async def test_list_user_documents(self):
        """Test listing documents for a user"""
        user_id = "user123"
        
        # Mock user documents
        expected_docs = [
            ProcessingResult(
                document_id="doc-1",
                correlation_id="corr-1",
                processing_status=ProcessingStatus.COMPLETED,
                confidence_score=0.95,
                processing_time_ms=1000
            ),
            ProcessingResult(
                document_id="doc-2",
                correlation_id="corr-2",
                processing_status=ProcessingStatus.COMPLETED,
                confidence_score=0.88,
                processing_time_ms=2000
            )
        ]
        
        with patch.object(self.document_service, '_get_user_documents', return_value=expected_docs):
            result = await self.document_service.list_documents(user_id)
            
            assert len(result) == 2
            assert result[0].document_id == "doc-1"
            assert result[1].document_id == "doc-2"
    
    @pytest.mark.asyncio
    async def test_delete_document(self):
        """Test document deletion"""
        document_id = "doc-123"
        user_id = "user123"
        
        # Mock successful deletion
        with patch.object(self.document_service, '_delete_document_storage', return_value=True):
            with patch.object(self.document_service, '_delete_document_metadata', return_value=True):
                result = await self.document_service.delete_document(document_id, user_id)
                
                assert result is True
    
    def test_determine_document_type_by_extension(self):
        """Test document type determination by file extension"""
        assert self.document_service._determine_document_type("test.dwg") == DocumentType.DWG
        assert self.document_service._determine_document_type("test.dxf") == DocumentType.DXF
        assert self.document_service._determine_document_type("test.ifc") == DocumentType.IFC
        assert self.document_service._determine_document_type("test.pdf") == DocumentType.PDF
        assert self.document_service._determine_document_type("test.txt") == DocumentType.TEXT
    
    def test_validate_file_size(self):
        """Test file size validation"""
        # Valid sizes
        assert self.document_service._validate_file_size(1024) is True  # 1KB
        assert self.document_service._validate_file_size(50 * 1024 * 1024) is True  # 50MB
        
        # Invalid sizes
        assert self.document_service._validate_file_size(0) is False  # Empty file
        assert self.document_service._validate_file_size(101 * 1024 * 1024) is False  # >100MB
    
    def test_calculate_content_hash(self):
        """Test content hash calculation"""
        content = b"test content"
        hash1 = self.document_service._calculate_content_hash(content)
        hash2 = self.document_service._calculate_content_hash(content)
        
        # Same content should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 character hex string
        
        # Different content should produce different hash
        different_content = b"different content"
        hash3 = self.document_service._calculate_content_hash(different_content)
        assert hash1 != hash3


class TestDWGDocumentProcessing:
    """Test DWG document processing functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.document_service = DocumentService()
    
    @pytest.mark.asyncio
    async def test_process_dwg_document_success(self):
        """Test successful DWG document processing"""
        file_content = b"Mock DWG content"
        
        with patch('ezdxf.readfile') as mock_readfile:
            # Mock DXF document structure
            mock_doc = Mock()
            mock_doc.modelspace.return_value = [
                Mock(dxftype="LINE", dxf=Mock(start=(0, 0), end=(100, 0))),
                Mock(dxftype="CIRCLE", dxf=Mock(center=(50, 50), radius=25)),
                Mock(dxftype="TEXT", dxf=Mock(text="Room A", insert=(25, 25)))
            ]
            mock_doc.layers = Mock()
            mock_doc.layers.data = {"Layer1": Mock(name="Layer1"), "Layer2": Mock(name="Layer2")}
            mock_doc.header = {"$ACADVER": "AC1027"}
            
            mock_readfile.return_value = mock_doc
            
            result = await self.document_service._process_dwg_document(file_content, "doc-123", "corr-123")
            
            # Assertions
            assert result.processing_status == ProcessingStatus.COMPLETED
            assert result.cad_drawing is not None
            assert result.cad_drawing.file_type == "dwg"
            assert len(result.cad_drawing.layers) > 0
            assert len(result.cad_drawing.elements) > 0
    
    @pytest.mark.asyncio
    async def test_process_dwg_document_invalid_format(self):
        """Test DWG processing with invalid format"""
        invalid_content = b"Not a valid DWG file"
        
        with patch('ezdxf.readfile', side_effect=Exception("Invalid DWG format")):
            with pytest.raises(Exception, match="Invalid DWG format"):
                await self.document_service._process_dwg_document(invalid_content, "doc-123", "corr-123")
    
    def test_extract_cad_elements(self):
        """Test CAD element extraction"""
        # Mock modelspace entities
        mock_entities = [
            Mock(dxftype="LINE", dxf=Mock(start=(0, 0), end=(100, 0))),
            Mock(dxftype="CIRCLE", dxf=Mock(center=(50, 50), radius=25)),
            Mock(dxftype="TEXT", dxf=Mock(text="Sample Text", insert=(10, 10)))
        ]
        
        elements = self.document_service._extract_cad_elements(mock_entities)
        
        assert len(elements) == 3
        assert elements[0].element_type == "line"
        assert elements[1].element_type == "circle"
        assert elements[2].element_type == "text"
    
    def test_extract_cad_layers(self):
        """Test CAD layer extraction"""
        # Mock layer data
        mock_layers = {
            "Architecture": Mock(name="Architecture", color=1, is_on=True, is_locked=False),
            "Structure": Mock(name="Structure", color=2, is_on=True, is_locked=True),
            "Dimensions": Mock(name="Dimensions", color=7, is_on=False, is_locked=False)
        }
        
        layers = self.document_service._extract_cad_layers(mock_layers)
        
        assert len(layers) == 3
        assert layers[0].name == "Architecture"
        assert layers[0].visible is True
        assert layers[1].name == "Structure"
        assert layers[1].locked is True
        assert layers[2].name == "Dimensions"
        assert layers[2].visible is False


class TestPDFDocumentProcessing:
    """Test PDF document processing functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.document_service = DocumentService()
    
    @pytest.mark.asyncio
    async def test_process_pdf_document_success(self):
        """Test successful PDF document processing"""
        file_content = b"Mock PDF content"
        
        with patch('PyPDF2.PdfReader') as mock_reader:
            # Mock PDF structure
            mock_page1 = Mock()
            mock_page1.extract_text.return_value = "Chapter 1: Building Requirements\nMinimum ceiling height: 2.4m"
            mock_page2 = Mock()
            mock_page2.extract_text.return_value = "Chapter 2: Fire Safety\nExit door requirements"
            
            mock_pdf = Mock()
            mock_pdf.pages = [mock_page1, mock_page2]
            mock_pdf.metadata = {"Title": "Building Code Document", "Subject": "Regulations"}
            
            mock_reader.return_value = mock_pdf
            
            result = await self.document_service._process_pdf_document(file_content, "doc-123", "corr-123")
            
            # Assertions
            assert result.processing_status == ProcessingStatus.COMPLETED
            assert "Building Requirements" in result.extracted_text
            assert "Fire Safety" in result.extracted_text
            assert len(result.building_rules) > 0  # Should extract some rules
    
    @pytest.mark.asyncio
    async def test_process_pdf_document_corrupted(self):
        """Test PDF processing with corrupted file"""
        corrupted_content = b"Not a valid PDF"
        
        with patch('PyPDF2.PdfReader', side_effect=Exception("Corrupted PDF file")):
            with pytest.raises(Exception, match="Corrupted PDF file"):
                await self.document_service._process_pdf_document(corrupted_content, "doc-123", "corr-123")
    
    def test_extract_building_rules_from_text(self):
        """Test building rule extraction from text"""
        text = """
        3.2.1 Ceiling Heights
        Minimum ceiling height shall be 2.4 meters for residential spaces.
        
        4.1.2 Door Requirements
        Minimum door width shall be 800mm for accessibility.
        
        5.3.1 Window Requirements
        Natural lighting area shall be minimum 10% of floor area.
        """
        
        rules = self.document_service._extract_building_rules_from_text(text)
        
        assert len(rules) >= 3
        
        # Check for ceiling height rule
        ceiling_rule = next((r for r in rules if "ceiling height" in r.rule_text.lower()), None)
        assert ceiling_rule is not None
        assert ceiling_rule.numeric_value == 2.4
        assert ceiling_rule.unit == "meters"
        
        # Check for door width rule
        door_rule = next((r for r in rules if "door width" in r.rule_text.lower()), None)
        assert door_rule is not None
        assert door_rule.numeric_value == 800
        assert door_rule.unit == "mm"


class TestIFCDocumentProcessing:
    """Test IFC document processing functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.document_service = DocumentService()
    
    @pytest.mark.asyncio
    async def test_process_ifc_document_success(self):
        """Test successful IFC document processing"""
        file_content = b"Mock IFC content"
        
        with patch('ifcopenshell.open') as mock_open:
            # Mock IFC structure
            mock_ifc = Mock()
            
            # Mock project
            mock_project = Mock()
            mock_project.Name = "Office Building Project"
            mock_project.GlobalId = "project-guid-123"
            
            # Mock building
            mock_building = Mock()
            mock_building.Name = "Main Building"
            mock_building.GlobalId = "building-guid-123"
            
            # Mock spaces
            mock_space1 = Mock()
            mock_space1.Name = "Office Room 1"
            mock_space1.GlobalId = "space-guid-1"
            mock_space2 = Mock()
            mock_space2.Name = "Conference Room"
            mock_space2.GlobalId = "space-guid-2"
            
            def mock_by_type(type_name):
                if type_name == "IfcProject":
                    return [mock_project]
                elif type_name == "IfcBuilding":
                    return [mock_building]
                elif type_name == "IfcSpace":
                    return [mock_space1, mock_space2]
                elif type_name == "IfcWall":
                    return [Mock(GlobalId=f"wall-{i}") for i in range(10)]  # 10 walls
                elif type_name == "IfcDoor":
                    return [Mock(GlobalId=f"door-{i}") for i in range(5)]  # 5 doors
                elif type_name == "IfcWindow":
                    return [Mock(GlobalId=f"window-{i}") for i in range(8)]  # 8 windows
                return []
            
            mock_ifc.by_type.side_effect = mock_by_type
            mock_ifc.schema = "IFC4"
            mock_open.return_value = mock_ifc
            
            result = await self.document_service._process_ifc_document(file_content, "doc-123", "corr-123")
            
            # Assertions
            assert result.processing_status == ProcessingStatus.COMPLETED
            assert result.ifc_model is not None
            assert result.ifc_model.schema_version == "IFC4"
            assert len(result.ifc_model.spaces) == 2
            assert len(result.ifc_model.walls) == 10
            assert len(result.ifc_model.doors) == 5
            assert len(result.ifc_model.windows) == 8
    
    @pytest.mark.asyncio
    async def test_process_ifc_document_invalid_format(self):
        """Test IFC processing with invalid format"""
        invalid_content = b"Not a valid IFC file"
        
        with patch('ifcopenshell.open', side_effect=Exception("Invalid IFC format")):
            with pytest.raises(Exception, match="Invalid IFC format"):
                await self.document_service._process_ifc_document(invalid_content, "doc-123", "corr-123")
    
    def test_extract_ifc_spatial_structure(self):
        """Test IFC spatial structure extraction"""
        # Mock IFC file
        mock_ifc = Mock()
        
        # Mock spatial elements
        mock_building = Mock()
        mock_building.Name = "Test Building"
        mock_building.GlobalId = "building-123"
        
        mock_floor1 = Mock()
        mock_floor1.Name = "Ground Floor"
        mock_floor1.GlobalId = "floor-1"
        
        mock_floor2 = Mock()
        mock_floor2.Name = "First Floor"
        mock_floor2.GlobalId = "floor-2"
        
        def mock_by_type(type_name):
            if type_name == "IfcBuilding":
                return [mock_building]
            elif type_name == "IfcBuildingStorey":
                return [mock_floor1, mock_floor2]
            return []
        
        mock_ifc.by_type.side_effect = mock_by_type
        
        structure = self.document_service._extract_ifc_spatial_structure(mock_ifc)
        
        assert len(structure["buildings"]) == 1
        assert structure["buildings"][0].name == "Test Building"
        assert len(structure["building_storeys"]) == 2
        assert structure["building_storeys"][0].name == "Ground Floor"
        assert structure["building_storeys"][1].name == "First Floor"


@pytest.mark.asyncio
class TestDocumentServiceIntegration:
    """Integration tests for Document Service with multiple file types"""
    
    async def test_multi_document_upload_workflow(self):
        """Test uploading multiple documents in sequence"""
        document_service = DocumentService()
        user_id = "user123"
        
        # Create test documents
        dwg_metadata = DocumentMetadata(
            filename="plan.dwg",
            file_type=DocumentType.DWG,
            file_size_bytes=1000,
            content_hash="a" * 64
        )
        
        pdf_metadata = DocumentMetadata(
            filename="code.pdf",
            file_type=DocumentType.PDF,
            file_size_bytes=2000,
            content_hash="b" * 64
        )
        
        ifc_metadata = DocumentMetadata(
            filename="model.ifc",
            file_type=DocumentType.IFC,
            file_size_bytes=3000,
            content_hash="c" * 64
        )
        
        # Mock processing methods
        with patch.object(document_service, '_process_dwg_document') as mock_dwg:
            with patch.object(document_service, '_process_pdf_document') as mock_pdf:
                with patch.object(document_service, '_process_ifc_document') as mock_ifc:
                    
                    # Configure successful responses
                    mock_dwg.return_value = ProcessingResult(
                        document_id="dwg-123", correlation_id="corr-123",
                        processing_status=ProcessingStatus.COMPLETED,
                        confidence_score=0.95, processing_time_ms=1000
                    )
                    
                    mock_pdf.return_value = ProcessingResult(
                        document_id="pdf-123", correlation_id="corr-456",
                        processing_status=ProcessingStatus.COMPLETED,
                        confidence_score=0.88, processing_time_ms=2000
                    )
                    
                    mock_ifc.return_value = ProcessingResult(
                        document_id="ifc-123", correlation_id="corr-789",
                        processing_status=ProcessingStatus.COMPLETED,
                        confidence_score=0.92, processing_time_ms=3000
                    )
                    
                    # Upload documents
                    dwg_upload = DocumentUpload(metadata=dwg_metadata)
                    dwg_result = await document_service.upload_document(dwg_upload, io.BytesIO(b"dwg"), user_id)
                    
                    pdf_upload = DocumentUpload(metadata=pdf_metadata)
                    pdf_result = await document_service.upload_document(pdf_upload, io.BytesIO(b"pdf"), user_id)
                    
                    ifc_upload = DocumentUpload(metadata=ifc_metadata)
                    ifc_result = await document_service.upload_document(ifc_upload, io.BytesIO(b"ifc"), user_id)
                    
                    # Assertions
                    assert all(result.processing_status == ProcessingStatus.COMPLETED 
                             for result in [dwg_result, pdf_result, ifc_result])
                    assert dwg_result.confidence_score == 0.95
                    assert pdf_result.confidence_score == 0.88
                    assert ifc_result.confidence_score == 0.92
    
    async def test_document_processing_error_handling(self):
        """Test comprehensive error handling during document processing"""
        document_service = DocumentService()
        
        metadata = DocumentMetadata(
            filename="broken.dwg",
            file_type=DocumentType.DWG,
            file_size_bytes=100,
            content_hash="error" + "0" * 60
        )
        
        # Mock processing failure
        with patch.object(document_service, '_process_dwg_document') as mock_process:
            mock_process.side_effect = Exception("Parser crashed")
            
            upload = DocumentUpload(metadata=metadata)
            result = await document_service.upload_document(upload, io.BytesIO(b"broken"), "user123")
            
            assert result.processing_status == ProcessingStatus.FAILED
            assert len(result.error_messages) > 0
            assert "Parser crashed" in result.error_messages[0]
    
    async def test_large_document_processing(self):
        """Test processing of large documents"""
        document_service = DocumentService()
        
        # Mock large file (10MB)
        large_size = 10 * 1024 * 1024
        large_content = b"x" * large_size
        
        metadata = DocumentMetadata(
            filename="large_code.pdf",
            file_type=DocumentType.PDF,
            file_size_bytes=large_size,
            content_hash="large" + "0" * 60
        )
        
        with patch.object(document_service, '_process_pdf_document') as mock_process:
            mock_process.return_value = ProcessingResult(
                document_id="large-123",
                correlation_id="corr-large",
                processing_status=ProcessingStatus.COMPLETED,
                confidence_score=0.85,
                processing_time_ms=5000,
                extracted_text="Large document content" * 1000
            )
            
            upload = DocumentUpload(metadata=metadata)
            result = await document_service.upload_document(upload, io.BytesIO(large_content), "user123")
            
            assert result.processing_status == ProcessingStatus.COMPLETED
            assert len(result.extracted_text) > 1000
            assert result.processing_time_ms == 5000