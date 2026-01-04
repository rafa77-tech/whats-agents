"""
Dashboard API routes.

Provides REST endpoints for the Julia Dashboard frontend.
"""

from fastapi import APIRouter, Depends
from typing import Annotated

from app.core.auth import (
    DashboardUser,
    get_current_user,
    require_role,
    require_viewer,
    require_operator,
    require_manager,
    require_admin,
    UserRole,
)

# Main router for all dashboard endpoints
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Type alias for authenticated user dependency
CurrentUser = Annotated[DashboardUser, Depends(get_current_user)]

# Re-export auth utilities
__all__ = [
    "router",
    "CurrentUser",
    "DashboardUser",
    "UserRole",
    "get_current_user",
    "require_role",
    "require_viewer",
    "require_operator",
    "require_manager",
    "require_admin",
]
