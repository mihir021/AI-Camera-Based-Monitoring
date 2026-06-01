"""
services package — exports all module-level service singletons.
Import individual services directly to avoid circular imports.
"""

from app.services.user_service import user_service
from app.services.camera_service import camera_service
from app.services.upload_service import upload_service
from app.services.session_service import session_service
from app.services.analytics_service import analytics_service
from app.services.alert_service import alert_service
from app.services.incident_service import incident_service

__all__ = [
    "user_service",
    "camera_service",
    "upload_service",
    "session_service",
    "analytics_service",
    "alert_service",
    "incident_service",
]
