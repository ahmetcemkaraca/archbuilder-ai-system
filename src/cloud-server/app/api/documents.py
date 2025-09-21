"""
Document processing API endpoints for ArchBuilder.AI
Handles multi-format CAD file processing, RAG generation, and document analysis
"""

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..core.auth.authentication import get_current_user
from ..core.billing.billing_service import billing_service, track_usage
from ..core.database import get_db
from ..models.documents import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentAnalysisRequest,
    DocumentAnalysisResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    SupportedFormat
)
from ..services.document_service import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
@track_usage("document_upload", cost_units=2)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    project_id: Optional[str] = Form(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DocumentUploadResponse:
    """
    Upload and process architectural documents
    
    Supported formats:
    - DWG/DXF: AutoCAD drawings
    - IFC: Industry Foundation Classes
    - PDF: Building regulations and drawings
    - RVT: Revit files
    - SKP: SketchUp models
    """
    
    # Check usage limits
    if not await billing_service.check_usage_limit(current_user.id, "document_upload", db):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Document upload limit exceeded. Please upgrade your subscription."
        )
    
    # Validate file type
    supported_extensions = ['.dwg', '.dxf', '.ifc', '.pdf', '.rvt', '.skp', '.3dm', '.step', '.iges']
    file_extension = None
    if file.filename:
        file_extension = '.' + file.filename.split('.')[-1].lower()
    
    if not file_extension or file_extension not in supported_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Supported formats: {', '.join(supported_extensions)}"
        )
    
    # Check file size
    subscription = await billing_service.get_subscription_details(current_user.id, db)
    max_file_size = subscription.limits.cloud_storage_gb * 1024 * 1024 * 1024  # Convert GB to bytes
    
    if file.size and file.size > max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds subscription limit of {subscription.limits.cloud_storage_gb}GB"
        )
    
    try:
        upload_result = await document_service.upload_document(
            file=file,
            document_type=document_type,
            project_id=project_id,
            user_id=current_user.id
        )
        
        return upload_result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document upload failed: {str(e)}"
        )


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    project_id: Optional[str] = None,
    document_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[DocumentResponse]:
    """
    List user's documents with filtering and pagination
    """
    
    try:
        documents = await document_service.list_user_documents(
            user_id=current_user.id,
            project_id=project_id,
            document_type=document_type,
            limit=limit,
            offset=offset
        )
        
        return documents
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documents: {str(e)}"
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DocumentResponse:
    """
    Get document details by ID
    """
    
    try:
        document = await document_service.get_document(
            document_id=document_id,
            user_id=current_user.id
        )
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied"
            )
        
        return document
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Delete document and all associated data
    """
    
    try:
        success = await document_service.delete_document(
            document_id=document_id,
            user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied"
            )
        
        return {
            "message": "Document deleted successfully",
            "document_id": document_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document deletion failed: {str(e)}"
        )


@router.post("/{document_id}/analyze", response_model=DocumentAnalysisResponse)
@track_usage("document_analysis", cost_units=5)
async def analyze_document(
    document_id: str,
    request: DocumentAnalysisRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DocumentAnalysisResponse:
    """
    Analyze document content and extract architectural information
    
    Analysis includes:
    - Geometry extraction
    - Room identification
    - Dimension analysis
    - Compliance checking
    - Material identification
    """
    
    try:
        analysis = await document_service.analyze_document(
            document_id=document_id,
            request=request,
            user_id=current_user.id
        )
        
        return analysis
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document analysis failed: {str(e)}"
        )


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    request: DocumentSearchRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> DocumentSearchResponse:
    """
    Search documents using semantic search and RAG
    
    Supports:
    - Natural language queries
    - Semantic similarity search
    - Building code references
    - Technical specification lookup
    """
    
    try:
        search_results = await document_service.search_documents(
            request=request,
            user_id=current_user.id
        )
        
        return search_results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document search failed: {str(e)}"
        )


@router.get("/{document_id}/preview")
async def get_document_preview(
    document_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get document preview image or thumbnail
    """
    
    try:
        preview_data = await document_service.get_document_preview(
            document_id=document_id,
            user_id=current_user.id
        )
        
        if not preview_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document preview not available"
            )
        
        return {
            "preview_url": preview_data.preview_url,
            "thumbnail_url": preview_data.thumbnail_url,
            "page_count": preview_data.page_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document preview: {str(e)}"
        )


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Download original document file
    """
    
    try:
        download_info = await document_service.get_download_url(
            document_id=document_id,
            user_id=current_user.id
        )
        
        if not download_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or access denied"
            )
        
        # Return redirect to download URL
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=download_info.download_url)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document download failed: {str(e)}"
        )


@router.post("/{document_id}/convert")
@track_usage("document_conversion", cost_units=3)
async def convert_document(
    document_id: str,
    target_format: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Convert document to different format
    
    Supported conversions:
    - DWG ↔ DXF
    - IFC → DWG/DXF
    - PDF → DXF (for technical drawings)
    - RVT → IFC
    """
    
    supported_formats = ['dwg', 'dxf', 'ifc', 'pdf']
    if target_format.lower() not in supported_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported target format. Supported: {', '.join(supported_formats)}"
        )
    
    try:
        conversion_result = await document_service.convert_document(
            document_id=document_id,
            target_format=target_format,
            user_id=current_user.id
        )
        
        return {
            "message": "Document conversion started",
            "conversion_id": conversion_result.conversion_id,
            "estimated_completion": conversion_result.estimated_completion,
            "status": "processing"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document conversion failed: {str(e)}"
        )


@router.get("/formats/supported", response_model=List[dict])
async def get_supported_formats() -> List[dict]:
    """
    Get list of supported document formats and their capabilities
    """
    
    formats = [
        {
            "extension": ".dwg",
            "name": "AutoCAD Drawing",
            "type": "CAD",
            "supports_2d": True,
            "supports_3d": True,
            "can_upload": True,
            "can_convert_from": [".dxf", ".ifc"],
            "can_convert_to": [".dxf", ".ifc", ".pdf"]
        },
        {
            "extension": ".dxf",
            "name": "Drawing Exchange Format",
            "type": "CAD",
            "supports_2d": True,
            "supports_3d": True,
            "can_upload": True,
            "can_convert_from": [".dwg", ".ifc"],
            "can_convert_to": [".dwg", ".ifc", ".pdf"]
        },
        {
            "extension": ".ifc",
            "name": "Industry Foundation Classes",
            "type": "BIM",
            "supports_2d": True,
            "supports_3d": True,
            "can_upload": True,
            "can_convert_from": [".rvt"],
            "can_convert_to": [".dwg", ".dxf"]
        },
        {
            "extension": ".pdf",
            "name": "Portable Document Format",
            "type": "Document",
            "supports_2d": True,
            "supports_3d": False,
            "can_upload": True,
            "can_convert_from": [".dwg", ".dxf"],
            "can_convert_to": [".dxf"]
        },
        {
            "extension": ".rvt",
            "name": "Revit Project File",
            "type": "BIM",
            "supports_2d": True,
            "supports_3d": True,
            "can_upload": True,
            "can_convert_from": [],
            "can_convert_to": [".ifc", ".dwg", ".dxf"]
        }
    ]
    
    return formats


@router.get("/building-codes", response_model=List[dict])
async def get_building_codes(
    region: Optional[str] = None,
    current_user = Depends(get_current_user)
) -> List[dict]:
    """
    Get available building codes and regulations
    """
    
    # Filter by region if specified
    all_codes = [
        {
            "id": "ibc_2021",
            "name": "International Building Code 2021",
            "region": "international",
            "country": "USA",
            "year": 2021,
            "categories": ["structural", "fire_safety", "accessibility", "energy"]
        },
        {
            "id": "eurocode",
            "name": "Eurocode Standards",
            "region": "europe",
            "country": "EU",
            "year": 2023,
            "categories": ["structural", "fire_safety", "energy"]
        },
        {
            "id": "turkish_building_code",
            "name": "Turkish Building Earthquake Code",
            "region": "middle_east",
            "country": "Turkey",
            "year": 2018,
            "categories": ["structural", "seismic", "fire_safety"]
        },
        {
            "id": "nbc_canada",
            "name": "National Building Code of Canada",
            "region": "north_america",
            "country": "Canada",
            "year": 2020,
            "categories": ["structural", "fire_safety", "accessibility", "energy"]
        }
    ]
    
    if region:
        all_codes = [code for code in all_codes if code["region"] == region]
    
    return all_codes