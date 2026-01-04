"""
Dashboard authentication module.

Handles JWT validation with Supabase and RBAC for dashboard users.
"""

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from enum import Enum
from dataclasses import dataclass

from app.services.supabase import supabase

security = HTTPBearer()


class UserRole(str, Enum):
    """Dashboard user roles with hierarchical permissions."""
    VIEWER = "viewer"
    OPERATOR = "operator"
    MANAGER = "manager"
    ADMIN = "admin"


ROLE_HIERARCHY = {
    UserRole.VIEWER: 0,
    UserRole.OPERATOR: 1,
    UserRole.MANAGER: 2,
    UserRole.ADMIN: 3,
}


@dataclass
class DashboardUser:
    """Represents an authenticated dashboard user."""
    id: str
    email: str
    role: UserRole
    nome: str
    ativo: bool = True

    def has_permission(self, required_role: UserRole) -> bool:
        """Check if user has at least the required role level."""
        return ROLE_HIERARCHY[self.role] >= ROLE_HIERARCHY[required_role]


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> DashboardUser:
    """
    Validate Supabase JWT and return dashboard user.

    Raises:
        HTTPException: If token is invalid or user doesn't have dashboard access.
    """
    token = credentials.credentials

    try:
        # Verify token with Supabase
        user_response = supabase.auth.get_user(token)
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalido"
            )

        auth_user = user_response.user

        # Get dashboard user data
        result = supabase.table("dashboard_users").select("*").eq(
            "supabase_user_id", auth_user.id
        ).single().execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario nao tem acesso ao dashboard"
            )

        user_data = result.data

        if not user_data.get("ativo", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario desativado"
            )

        return DashboardUser(
            id=user_data["id"],
            email=auth_user.email,
            role=UserRole(user_data["role"]),
            nome=user_data["nome"],
            ativo=user_data.get("ativo", True)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Erro de autenticacao: {str(e)}"
        )


def require_role(required_role: UserRole):
    """
    Dependency factory to check minimum role requirement.

    Usage:
        @router.post("/admin-only")
        async def admin_action(user: DashboardUser = Depends(require_role(UserRole.ADMIN))):
            ...
    """
    async def check_role(user: DashboardUser = Depends(get_current_user)):
        if not user.has_permission(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requer permissao: {required_role.value}"
            )
        return user
    return check_role


# Convenience dependencies
async def require_viewer(user: DashboardUser = Depends(get_current_user)) -> DashboardUser:
    """Any authenticated dashboard user."""
    return user


async def require_operator(user: DashboardUser = Depends(require_role(UserRole.OPERATOR))) -> DashboardUser:
    """Operator or higher."""
    return user


async def require_manager(user: DashboardUser = Depends(require_role(UserRole.MANAGER))) -> DashboardUser:
    """Manager or higher."""
    return user


async def require_admin(user: DashboardUser = Depends(require_role(UserRole.ADMIN))) -> DashboardUser:
    """Admin only."""
    return user
