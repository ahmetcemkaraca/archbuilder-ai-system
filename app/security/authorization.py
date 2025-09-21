from fastapi import Depends, HTTPException, status
from typing import List, Callable

from app.models.database import User, UserRole
from app.security.authentication import get_current_active_user

def check_roles(required_roles: List[UserRole]) -> Callable:
    """Belirtilen rollerden birine sahip olup olmadığını kontrol eden bir yetkilendirme bağımlılığı oluşturur."""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in [role.value for role in required_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu işlemi gerçekleştirmek için yeterli ayrıcalığınız yok."
            )
        return current_user
    return role_checker

def is_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Kullanıcının yönetici olup olmadığını kontrol eder."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yönetici ayrıcalıkları gerekli."
        )
    return current_user

def is_architect(current_user: User = Depends(get_current_active_user)) -> User:
    """Kullanıcının mimar olup olmadığını kontrol eder."""
    if current_user.role not in [UserRole.ARCHITECT.value, UserRole.ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mimar veya yönetici ayrıcalıkları gerekli."
        )
    return current_user

def can_edit_project(project_owner_id: str) -> Callable:
    """Kullanıcının belirli bir projeyi düzenleyip düzenleyemeyeceğini kontrol eder."""
    def project_editor_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.id != project_owner_id and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu projeyi düzenlemek için yetkiniz yok."
            )
        return current_user
    return project_editor_checker

