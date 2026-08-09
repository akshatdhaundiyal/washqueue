from fastapi import Header, HTTPException, status
try:
    from app.config import settings
except ImportError:
    from config import settings

async def require_admin_pin(x_admin_pin: str = Header(None, alias="X-Admin-PIN")):
    """
    FastAPI Security Dependency that verifies the 4-digit Admin PIN header.
    """
    if not x_admin_pin or x_admin_pin != settings.admin_pin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Invalid or missing Admin PIN."
        )
    return True
