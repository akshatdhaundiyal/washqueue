from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

try:
    from app.database import get_db
    from app.middleware.auth import require_admin_pin
    from app.schemas import SmartPlugCreate, SmartPlugUpdate, SmartPlugResponse, TelemetryReadingResponse
    from app.repositories import SmartPlugRepository, TelemetryRepository
    from app.smart_plug_providers.registry import get_provider
except ImportError:
    from database import get_db
    from middleware.auth import require_admin_pin
    from schemas import SmartPlugCreate, SmartPlugUpdate, SmartPlugResponse, TelemetryReadingResponse
    from repositories import SmartPlugRepository, TelemetryRepository
    from smart_plug_providers.registry import get_provider

router = APIRouter(prefix="/api/smart-plugs", tags=["smart-plugs"], dependencies=[Depends(require_admin_pin)])

@router.get("", response_model=List[SmartPlugResponse])
async def list_smart_plugs(db: AsyncSession = Depends(get_db)):
    """List all registered smart plugs (Admin only)."""
    plugs = await SmartPlugRepository.get_all(db)
    return [SmartPlugResponse.model_validate(p) for p in plugs]

@router.post("", response_model=SmartPlugResponse, status_code=status.HTTP_201_CREATED)
async def create_smart_plug(req: SmartPlugCreate, db: AsyncSession = Depends(get_db)):
    """Register a new smart plug (Admin only)."""
    plug = await SmartPlugRepository.create(db, **req.model_dump())
    await db.commit()
    return SmartPlugResponse.model_validate(plug)

@router.put("/{id}", response_model=SmartPlugResponse)
async def update_smart_plug(id: UUID, req: SmartPlugUpdate, db: AsyncSession = Depends(get_db)):
    """Update smart plug configuration (Admin only)."""
    updated = await SmartPlugRepository.update(db, id, **req.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Smart plug not found")
    await db.commit()
    return SmartPlugResponse.model_validate(updated)

@router.delete("/{id}")
async def delete_smart_plug(id: UUID, db: AsyncSession = Depends(get_db)):
    """Unregister a smart plug (Admin only)."""
    deleted = await SmartPlugRepository.delete(db, id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Smart plug not found")
    await db.commit()
    return {"status": "success", "message": "Smart plug removed."}

@router.post("/{id}/test")
async def test_smart_plug_connection(id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Tests local LAN connection to a smart plug using tinytuya (Admin only).
    """
    plug = await SmartPlugRepository.get_by_id(db, id)
    if not plug:
        raise HTTPException(status_code=404, detail="Smart plug not found")
        
    try:
        provider = get_provider(plug.provider)
        status_data = await provider.get_status(
            device_id=plug.device_id,
            local_key=plug.local_key,
            ip_address=plug.ip_address,
            protocol_version=plug.protocol_version
        )
        telemetry = await provider.get_telemetry(
            device_id=plug.device_id,
            local_key=plug.local_key,
            ip_address=plug.ip_address,
            protocol_version=plug.protocol_version
        )
        
        # Update plug online status
        await SmartPlugRepository.update(db, id, is_online=status_data.is_online)
        await db.commit()

        return {
            "status": "success" if status_data.is_online else "failed",
            "is_online": status_data.is_online,
            "switch_on": status_data.switch_on,
            "voltage_v": telemetry.voltage_v,
            "current_ma": telemetry.current_ma,
            "power_w": telemetry.power_w,
            "raw_dps": telemetry.raw_dps
        }
    except Exception as e:
        return {
            "status": "error",
            "is_online": False,
            "detail": str(e)
        }
