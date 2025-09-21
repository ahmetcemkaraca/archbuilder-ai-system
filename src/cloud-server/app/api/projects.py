"""
Project management API endpoints for ArchBuilder.AI
Handles project creation, management, and Revit integration
"""

from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..core.auth.authentication import get_current_user, require_subscription_tier
from ..core.billing.billing_service import billing_service, track_usage
from ..core.database import get_db
from ..models.projects import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
    ProjectAnalysisRequest,
    ProjectAnalysisResponse,
    ProjectExportRequest,
    ProjectExportResponse,
    ProjectVersionResponse
)
from ..models.subscriptions import SubscriptionTier
from ..services.project_service import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@track_usage("revit_project_creation", cost_units=5)
async def create_project(
    request: ProjectCreateRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ProjectResponse:
    """
    Create new ArchBuilder.AI project
    
    Supports:
    - Empty project creation
    - Template-based project creation
    - AI-generated project initialization
    """
    
    # Check usage limits
    if not await billing_service.check_usage_limit(current_user.id, "revit_project_creation", db):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Project creation limit exceeded. Please upgrade your subscription."
        )
    
    try:
        project = await project_service.create_project(
            request=request,
            user_id=current_user.id
        )
        
        return project
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project creation failed: {str(e)}"
        )


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None
) -> List[ProjectResponse]:
    """
    List user's projects with pagination and filtering
    """
    
    try:
        projects = await project_service.list_user_projects(
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            status_filter=status_filter
        )
        
        return projects
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve projects: {str(e)}"
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ProjectResponse:
    """
    Get project details by ID
    """
    
    try:
        project = await project_service.get_project(
            project_id=project_id,
            user_id=current_user.id
        )
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )
        
        return project
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve project: {str(e)}"
        )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: ProjectUpdateRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ProjectResponse:
    """
    Update project details
    """
    
    try:
        project = await project_service.update_project(
            project_id=project_id,
            request=request,
            user_id=current_user.id
        )
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )
        
        return project
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project update failed: {str(e)}"
        )


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Delete project and all associated data
    """
    
    try:
        success = await project_service.delete_project(
            project_id=project_id,
            user_id=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or access denied"
            )
        
        return {
            "message": "Project deleted successfully",
            "project_id": project_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project deletion failed: {str(e)}"
        )


@router.post("/{project_id}/analyze", response_model=ProjectAnalysisResponse)
@track_usage("project_analysis", cost_units=8)
async def analyze_project(
    project_id: str,
    request: ProjectAnalysisRequest,
    current_user = Depends(require_subscription_tier(SubscriptionTier.PROFESSIONAL)),
    db: Session = Depends(get_db)
) -> ProjectAnalysisResponse:
    """
    Analyze existing Revit project for optimization opportunities
    
    Requires PROFESSIONAL subscription or higher
    Provides:
    - Performance analysis
    - Clash detection
    - Cost optimization
    - Compliance checking
    """
    
    try:
        analysis = await project_service.analyze_project(
            project_id=project_id,
            request=request,
            user_id=current_user.id
        )
        
        return analysis
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project analysis failed: {str(e)}"
        )


@router.post("/{project_id}/upload-revit")
@track_usage("revit_file_upload", cost_units=3)
async def upload_revit_file(
    project_id: str,
    file: UploadFile = File(...),
    version_note: str = Form(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Upload Revit file (.rvt) to project
    
    Supports:
    - Version management
    - Automatic backup
    - Project analysis trigger
    """
    
    # Validate file type
    if not file.filename.endswith('.rvt'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Revit (.rvt) files are supported"
        )
    
    # Check file size limits
    subscription = await billing_service.get_subscription_details(current_user.id, db)
    max_file_size = subscription.limits.cloud_storage_gb * 1024 * 1024 * 1024  # Convert GB to bytes
    
    if file.size > max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds subscription limit of {subscription.limits.cloud_storage_gb}GB"
        )
    
    try:
        upload_result = await project_service.upload_revit_file(
            project_id=project_id,
            file=file,
            version_note=version_note,
            user_id=current_user.id
        )
        
        return {
            "message": "Revit file uploaded successfully",
            "file_id": upload_result.file_id,
            "version": upload_result.version,
            "analysis_triggered": upload_result.analysis_triggered
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )


@router.get("/{project_id}/versions", response_model=List[ProjectVersionResponse])
async def get_project_versions(
    project_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[ProjectVersionResponse]:
    """
    Get all versions of project files
    """
    
    try:
        versions = await project_service.get_project_versions(
            project_id=project_id,
            user_id=current_user.id
        )
        
        return versions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve project versions: {str(e)}"
        )


@router.post("/{project_id}/export", response_model=ProjectExportResponse)
async def export_project(
    project_id: str,
    request: ProjectExportRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ProjectExportResponse:
    """
    Export project in various formats
    
    Supported formats:
    - Revit (.rvt)
    - IFC (.ifc)
    - DWG (.dwg)
    - PDF drawings
    """
    
    try:
        export_result = await project_service.export_project(
            project_id=project_id,
            request=request,
            user_id=current_user.id
        )
        
        return export_result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project export failed: {str(e)}"
        )


@router.post("/{project_id}/clone", response_model=ProjectResponse)
async def clone_project(
    project_id: str,
    new_project_name: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ProjectResponse:
    """
    Clone existing project with new name
    """
    
    try:
        cloned_project = await project_service.clone_project(
            project_id=project_id,
            new_project_name=new_project_name,
            user_id=current_user.id
        )
        
        return cloned_project
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project cloning failed: {str(e)}"
        )


@router.get("/{project_id}/collaboration")
async def get_collaboration_info(
    project_id: str,
    current_user = Depends(require_subscription_tier(SubscriptionTier.PROFESSIONAL)),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get project collaboration information
    
    Requires PROFESSIONAL subscription or higher
    """
    
    try:
        collaboration_info = await project_service.get_collaboration_info(
            project_id=project_id,
            user_id=current_user.id
        )
        
        return collaboration_info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve collaboration info: {str(e)}"
        )


@router.post("/{project_id}/share")
async def share_project(
    project_id: str,
    email: str,
    permission_level: str = "read",
    current_user = Depends(require_subscription_tier(SubscriptionTier.PROFESSIONAL)),
    db: Session = Depends(get_db)
) -> dict:
    """
    Share project with another user
    
    Requires PROFESSIONAL subscription or higher
    Permission levels: read, write, admin
    """
    
    valid_permissions = ["read", "write", "admin"]
    if permission_level not in valid_permissions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permission level. Must be one of: {valid_permissions}"
        )
    
    try:
        share_result = await project_service.share_project(
            project_id=project_id,
            email=email,
            permission_level=permission_level,
            user_id=current_user.id
        )
        
        return {
            "message": "Project shared successfully",
            "shared_with": email,
            "permission_level": permission_level,
            "share_id": share_result.share_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project sharing failed: {str(e)}"
        )


@router.get("/templates", response_model=List[dict])
async def get_project_templates(
    current_user = Depends(get_current_user)
) -> List[dict]:
    """
    Get available project templates
    """
    
    templates = [
        {
            "id": "residential_house",
            "name": "Residential House",
            "description": "Single-family house template with standard rooms",
            "category": "Residential",
            "preview_image": "https://example.com/templates/residential_house.jpg",
            "tier_required": "FREE"
        },
        {
            "id": "office_building",
            "name": "Office Building",
            "description": "Commercial office space with flexible layouts",
            "category": "Commercial",
            "preview_image": "https://example.com/templates/office_building.jpg",
            "tier_required": "STARTER"
        },
        {
            "id": "apartment_complex",
            "name": "Apartment Complex",
            "description": "Multi-unit residential building template",
            "category": "Residential",
            "preview_image": "https://example.com/templates/apartment_complex.jpg",
            "tier_required": "PROFESSIONAL"
        },
        {
            "id": "retail_space",
            "name": "Retail Space",
            "description": "Commercial retail store with customer flow optimization",
            "category": "Commercial",
            "preview_image": "https://example.com/templates/retail_space.jpg",
            "tier_required": "STARTER"
        }
    ]
    
    return templates