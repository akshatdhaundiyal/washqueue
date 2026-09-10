from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

import datetime
from sqlalchemy import select

try:
    from app.database import get_db
    from app.middleware.auth import require_admin_pin
    from app.schemas import (
        SmartPlugCreate, SmartPlugUpdate, SmartPlugResponse, 
        TelemetryReadingResponse, TelemetryHistoryResponse, TelemetryHistoryPoint,
        CalibrationUpdateRequest, CalibrationUpdateResponse
    )
    from app.repositories import SmartPlugRepository, TelemetryRepository, MachineRepository
    from app.smart_plug_providers.registry import get_provider
    from app.tuya_sync_service import TuyaSyncService
    from app.telemetry_service import process_plug_telemetry
    from app.models import TelemetryReading, SmartPlug, Machine
    from app.routers.websocket import ws_manager
except ImportError:
    from ..database import get_db
    from ..middleware.auth import require_admin_pin
    from ..schemas import (
        SmartPlugCreate, SmartPlugUpdate, SmartPlugResponse, 
        TelemetryReadingResponse, TelemetryHistoryResponse, TelemetryHistoryPoint,
        CalibrationUpdateRequest, CalibrationUpdateResponse
    )
    from ..repositories import SmartPlugRepository, TelemetryRepository, MachineRepository
    from ..smart_plug_providers.registry import get_provider
    from ..tuya_sync_service import TuyaSyncService
    from ..telemetry_service import process_plug_telemetry
    from ..models import TelemetryReading, SmartPlug, Machine
    from ..routers.websocket import ws_manager

router = APIRouter(prefix="/api/smart-plugs", tags=["smart-plugs"], dependencies=[Depends(require_admin_pin)])

@router.get("", response_model=List[SmartPlugResponse])
async def list_smart_plugs(db: AsyncSession = Depends(get_db)):
    """List all registered smart plugs with their latest live telemetry (Admin only)."""
    plugs = await SmartPlugRepository.get_all(db)
    response = []
    for p in plugs:
        plug_resp = SmartPlugResponse.model_validate(p)
        latest_reading = await TelemetryRepository.get_latest_for_plug(db, p.id)
        if latest_reading:
            plug_resp.latest_telemetry = TelemetryReadingResponse.model_validate(latest_reading)
        response.append(plug_resp)
    return response

@router.post("/sync", response_model=List[SmartPlugResponse])
async def sync_smart_plugs_from_cloud(db: AsyncSession = Depends(get_db)):
    """
    Automated Tuya Cloud synchronization:
    Discovers plugs, synchronizes changed keys/device IDs after resets, and resolves local IPs.
    """
    plugs = await TuyaSyncService.sync_all_plugs(db, auto_onboard_new=True)
    response = []
    for p in plugs:
        plug_resp = SmartPlugResponse.model_validate(p)
        latest_reading = await TelemetryRepository.get_latest_for_plug(db, p.id)
        if latest_reading:
            plug_resp.latest_telemetry = TelemetryReadingResponse.model_validate(latest_reading)
        response.append(plug_resp)
    return response

@router.get("/{id}/instant-telemetry")
async def get_instant_telemetry(id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Performs an immediate, instantaneous telemetry poll for this plug (local LAN or cloud fallback)
    and persists the reading in the time-series database.
    """
    plug = await SmartPlugRepository.get_by_id(db, id)
    if not plug:
        raise HTTPException(status_code=404, detail="Smart plug not found")

    await process_plug_telemetry(db, plug)
    await db.commit()

    latest_reading = await TelemetryRepository.get_latest_for_plug(db, plug.id)
    return {
        "status": "success",
        "plug_id": str(plug.id),
        "name": plug.name,
        "is_online": plug.is_online,
        "telemetry": TelemetryReadingResponse.model_validate(latest_reading) if latest_reading else None
    }

@router.post("/{id}/switch")
async def toggle_smart_plug_switch(id: UUID, on: bool, db: AsyncSession = Depends(get_db)):
    """
    Remotely toggles smart plug relay switch state ON or OFF (Admin only).
    """
    plug = await SmartPlugRepository.get_by_id(db, id)
    if not plug:
        raise HTTPException(status_code=404, detail="Smart plug not found")

    provider = get_provider(plug.provider)
    success = await provider.set_switch(
        device_id=plug.device_id,
        local_key=plug.local_key,
        ip_address=plug.ip_address,
        on=on,
        protocol_version=plug.protocol_version
    )

    # Immediately poll new telemetry state
    await process_plug_telemetry(db, plug)
    await db.commit()

    return {
        "status": "success" if success else "failed",
        "switch_on": on if success else None,
        "message": f"Smart plug relay turned {'ON' if on else 'OFF'}."
    }

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

@router.post("/{id}/switch")
async def toggle_smart_plug_switch(id: UUID, on: bool, db: AsyncSession = Depends(get_db)):
    """
    Remotely toggles a smart plug relay switch ON or OFF (Admin only).
    Uses local socket connection first, and falls back to Tuya Cloud API.
    """
    plug = await SmartPlugRepository.get_by_id(db, id)
    if not plug:
        raise HTTPException(status_code=404, detail="Smart plug not found")

    provider = get_provider(plug.provider)
    success = await provider.set_switch(
        device_id=plug.device_id,
        local_key=plug.local_key,
        ip_address=plug.ip_address,
        on=on,
        protocol_version=plug.protocol_version
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to toggle smart plug switch")

    # Refresh telemetry immediately to record the new switch state
    try:
        telemetry = await provider.get_telemetry(
            device_id=plug.device_id,
            local_key=plug.local_key,
            ip_address=plug.ip_address,
            protocol_version=plug.protocol_version
        )
        if telemetry:
            reading = TelemetryReading(
                plug_id=plug.id,
                voltage_v=telemetry.voltage_v,
                current_ma=telemetry.current_ma,
                power_w=telemetry.power_w,
                energy_kwh=telemetry.energy_kwh,
                switch_on=on
            )
            db.add(reading)
            plug.is_online = True
            await db.commit()
    except Exception:
        pass

    return {
        "status": "success",
        "plug_id": str(id),
        "switch_on": on
    }

@router.get("/{id}/history", response_model=TelemetryHistoryResponse)
async def get_plug_telemetry_history(
    id: UUID, 
    hours: int = 4, 
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the 4-hour historical telemetry series for a smart plug socket,
    with local (high-res WS) vs cloud (periodic fallback) source tags.
    """
    plug = await SmartPlugRepository.get_by_id(db, id)
    if not plug:
        raise HTTPException(status_code=404, detail="Smart plug not found")
        
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    
    # Query readings ordered chronologically
    result = await db.execute(
        select(TelemetryReading)
        .where(TelemetryReading.plug_id == id)
        .where(TelemetryReading.recorded_at >= cutoff)
        .order_by(TelemetryReading.recorded_at.asc())
    )
    readings = result.scalars().all()
    
    # Fallback to last 150 readings if no data within strict time cutoff
    if not readings:
        fallback_res = await db.execute(
            select(TelemetryReading)
            .where(TelemetryReading.plug_id == id)
            .order_by(TelemetryReading.recorded_at.desc())
            .limit(150)
        )
        readings = list(reversed(fallback_res.scalars().all()))

    powers = [r.power_w for r in readings if r.power_w is not None]
    peak_w = max(powers) if powers else 0.0
    avg_w = sum(powers) / len(powers) if powers else 0.0

    local_count = sum(1 for r in readings if (getattr(r, "source", None) or "local") == "local")
    cloud_count = sum(1 for r in readings if getattr(r, "source", None) == "cloud")

    series = [
        TelemetryHistoryPoint(
            timestamp=r.recorded_at.isoformat() if r.recorded_at else "",
            power_w=round(r.power_w or 0.0, 1),
            voltage_v=round(r.voltage_v, 1) if r.voltage_v is not None else None,
            current_ma=round(r.current_ma, 1) if r.current_ma is not None else None,
            source=getattr(r, "source", None) or "local"
        )
        for r in readings
    ]

    return TelemetryHistoryResponse(
        plug_id=plug.id,
        plug_name=plug.name or "Wipro Smart Plug",
        hours=hours,
        peak_power_w=round(peak_w, 1),
        avg_power_w=round(avg_w, 1),
        local_points_count=local_count,
        cloud_points_count=cloud_count,
        series=series
    )

@router.patch("/{id}/calibration", response_model=CalibrationUpdateResponse)
async def update_plug_calibration(
    id: UUID,
    req: CalibrationUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Instantly tunes smart plug inference thresholds (Running cutoff, Idle cutoff, Soak debounce seconds).
    Optionally applies the same thresholds to all smart plugs linked to similar machines.
    """
    plug = await SmartPlugRepository.get_by_id(db, id)
    if not plug:
        raise HTTPException(status_code=404, detail="Smart plug not found")

    plug.power_threshold_running = req.power_threshold_running
    plug.power_threshold_idle = req.power_threshold_idle
    plug.debounce_seconds = req.debounce_seconds

    similar_count = 0
    if req.apply_to_similar_machines and plug.machine_id:
        target_machine = await MachineRepository.get_by_id(db, plug.machine_id)
        if target_machine:
            # Determine machine category / keyword (e.g. 'Washer' or 'Dryer')
            name_parts = target_machine.name.split()
            keyword = next((p for p in name_parts if any(kw in p.lower() for kw in ["washer", "dryer", "ifb", "lg", "speedqueen", "samsung"])), name_parts[0])

            # Query all other smart plugs with assigned machines
            all_plugs = await SmartPlugRepository.get_all(db)
            for other_plug in all_plugs:
                if other_plug.id != plug.id and other_plug.machine_id:
                    m = await MachineRepository.get_by_id(db, other_plug.machine_id)
                    if m and keyword.lower() in m.name.lower():
                        other_plug.power_threshold_running = req.power_threshold_running
                        other_plug.power_threshold_idle = req.power_threshold_idle
                        other_plug.debounce_seconds = req.debounce_seconds
                        similar_count += 1

    await db.commit()
    await db.refresh(plug)

    # Broadcast real-time WebSocket update for calibration change
    await ws_manager.broadcast({
        "type": "calibration_updated",
        "plug_id": str(plug.id),
        "power_threshold_running": plug.power_threshold_running,
        "power_threshold_idle": plug.power_threshold_idle,
        "debounce_seconds": plug.debounce_seconds,
        "similar_updated": similar_count
    })

    msg = f"Calibration updated successfully for {plug.name or 'Smart Plug'}."
    if similar_count > 0:
        msg += f" Applied to {similar_count} similar machine(s)."

    return CalibrationUpdateResponse(
        plug_id=plug.id,
        plug_name=plug.name,
        power_threshold_running=plug.power_threshold_running,
        power_threshold_idle=plug.power_threshold_idle,
        debounce_seconds=plug.debounce_seconds,
        similar_plugs_updated=similar_count,
        message=msg
    )


@router.post("/{id}/auto-calibrate")
async def auto_calibrate_smart_plug(
    id: UUID,
    apply: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyzes all recorded telemetry for this smart plug in the database:
    - Calculates standby baseline idle draw
    - Detects longest soak/pause duration
    - Classifies machine archetype profile
    - Returns recommended thresholds and optionally applies them to DB.
    """
    plug = await SmartPlugRepository.get_by_id(db, id)
    if not plug:
        raise HTTPException(status_code=404, detail="Smart plug not found")

    result = await db.execute(
        select(TelemetryReading)
        .where(TelemetryReading.plug_id == id)
        .order_by(TelemetryReading.recorded_at.asc())
        .limit(1500)
    )
    readings = result.scalars().all()
    if not readings or len(readings) < 10:
        return {
            "status": "insufficient_data",
            "message": "Fewer than 10 telemetry samples recorded. Run a wash cycle or test simulation first.",
            "recommended_running_w": 10.0,
            "recommended_idle_w": 5.0,
            "recommended_debounce_seconds": 120,
            "archetype": "Standard Automatic Washer",
            "applied": False
        }

    powers = [r.power_w for r in readings if r.power_w is not None]
    if not powers:
        raise HTTPException(status_code=400, detail="No valid power readings found")

    peak_power = max(powers)
    sorted_p = sorted(powers)
    ten_pct = max(1, len(sorted_p) // 10)
    baseline_idle = sum(sorted_p[:ten_pct]) / ten_pct

    has_started = False
    in_pause = False
    pause_start = 0.0
    pauses = []

    active_ref = baseline_idle + 5.0
    idle_ref = baseline_idle + 2.0

    t0 = readings[0].recorded_at
    for r in readings:
        p = r.power_w or 0.0
        t = (r.recorded_at - t0).total_seconds()
        if p >= active_ref:
            has_started = True
            if in_pause:
                pauses.append(t - pause_start)
                in_pause = False
        elif has_started and p < idle_ref:
            if not in_pause:
                in_pause = True
                pause_start = t

    max_pause_sec = max(pauses) if pauses else 0.0

    if peak_power > 1200.0:
        archetype = "Front-Load with Internal Heater"
        icon = "🔥"
    elif max_pause_sec >= 150.0:
        archetype = "Top-Load Pulsator (Deep Soak)"
        icon = "🌀"
    elif max_pause_sec < 90.0 and peak_power <= 600.0:
        archetype = "Inverter Direct-Drive Front-Load"
        icon = "🌊"
    else:
        archetype = "Standard Multi-Stage Washer"
        icon = "🧺"

    rec_run = round(max(8.0, baseline_idle + 5.0), 1)
    rec_idle = round(max(3.0, baseline_idle + 2.0), 1)
    rec_deb = max(90, int(max_pause_sec * 1.25) + 15) if max_pause_sec > 0 else 120

    if apply:
        plug.power_threshold_running = rec_run
        plug.power_threshold_idle = rec_idle
        plug.debounce_seconds = rec_deb
        await db.commit()
        await db.refresh(plug)

        await ws_manager.broadcast({
            "type": "calibration_updated",
            "plug_id": str(plug.id),
            "power_threshold_running": plug.power_threshold_running,
            "power_threshold_idle": plug.power_threshold_idle,
            "debounce_seconds": plug.debounce_seconds
        })

    return {
        "status": "success",
        "archetype": f"{icon} {archetype}",
        "sample_count": len(readings),
        "peak_power_w": round(peak_power, 1),
        "baseline_idle_w": round(baseline_idle, 1),
        "longest_pause_seconds": round(max_pause_sec, 1),
        "recommended_running_w": rec_run,
        "recommended_idle_w": rec_idle,
        "recommended_debounce_seconds": rec_deb,
        "applied": apply
    }


@router.post("/{id}/simulate-cycle")
async def simulate_smart_plug_cycle(
    id: UUID,
    minutes: float = 25.0,
    db: AsyncSession = Depends(get_db)
):
    """
    Injects a realistic synthetic wash cycle into the database for this smart plug
    so admins can visually test and tune the calibration studio without running physical appliances.
    """
    import math, random
    plug = await SmartPlugRepository.get_by_id(db, id)
    if not plug:
        raise HTTPException(status_code=404, detail="Smart plug not found")

    total_seconds = int(minutes * 60)
    step_seconds = 2
    now = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=total_seconds)
    entries = []
    cum_kwh = 0.0

    for s in range(0, total_seconds, step_seconds):
        progress = s / total_seconds
        v = round(220.0 + random.uniform(-2.0, 2.0), 1)

        if progress < 0.05:
            p = round(random.uniform(0.5, 1.2), 1)
        elif progress < 0.15:
            p = round(18.0 + random.uniform(-1.5, 1.5), 1)
        elif progress < 0.40:
            osc = math.sin(s * 0.2)
            p = round(max(10.0, 210.0 + 40.0 * osc + random.uniform(-15.0, 15.0)), 1)
        elif progress < 0.55:
            p = round(random.uniform(0.8, 2.0), 1)
        elif progress < 0.70:
            osc = math.sin(s * 0.25)
            p = round(160.0 + 50.0 * osc + random.uniform(-10.0, 10.0), 1)
        elif progress < 0.90:
            spin_prog = (progress - 0.70) / 0.20
            p = round(320.0 + 220.0 * spin_prog + random.uniform(-15.0, 15.0), 1)
        else:
            p = round(random.uniform(0.4, 1.0), 1)

        ma = round((p / v) * 1000.0, 1) if p > 0 else 0.0
        pt_time = now + datetime.timedelta(seconds=s)
        cum_kwh += (p * step_seconds) / 3600000.0

        entries.append(TelemetryReading(
            plug_id=plug.id,
            voltage_v=v,
            current_ma=ma,
            power_w=p,
            energy_kwh=round(cum_kwh, 4),
            switch_on=True,
            source="simulated",
            recorded_at=pt_time
        ))

    db.add_all(entries)
    await db.commit()

    return {
        "status": "success",
        "message": f"Injected {len(entries)} telemetry samples for a {minutes}m test wash cycle.",
        "samples_injected": len(entries)
    }

