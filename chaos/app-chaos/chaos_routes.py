"""
API Routes for Chaos Engineering Control

Provides endpoints to control chaos injection at runtime.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

from .chaos_middleware import (
    ChaosType,
    ChaosConfig,
    enable_chaos,
    disable_chaos,
    get_chaos_stats,
    update_chaos_config,
)

router = APIRouter(prefix="/chaos", tags=["chaos"])


class ChaosStatusResponse(BaseModel):
    """Response model for chaos status"""
    enabled: bool
    total_requests: int
    chaos_injected: int
    chaos_rate: float
    configured_probability: float


class ChaosEnableRequest(BaseModel):
    """Request model for enabling chaos"""
    enabled: bool
    probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    latency_ms_max: Optional[int] = Field(None, ge=0, le=30000)
    chaos_types: Optional[List[ChaosType]] = None


class ChaosConfigUpdateRequest(BaseModel):
    """Request model for updating chaos configuration"""
    chaos_probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    latency_ms_min: Optional[int] = Field(None, ge=0)
    latency_ms_max: Optional[int] = Field(None, ge=0, le=30000)
    error_codes: Optional[List[int]] = None
    timeout_ms: Optional[int] = Field(None, ge=0)
    chaos_types: Optional[List[ChaosType]] = None


@router.get("/status", response_model=ChaosStatusResponse)
async def get_chaos_status():
    """
    Get current chaos injection status and statistics.

    Returns:
        Current status including enabled state, request counts, and chaos rate
    """
    stats = get_chaos_stats()
    if stats is None:
        raise HTTPException(
            status_code=503,
            detail="Chaos middleware not initialized",
        )
    return stats


@router.post("/enable")
async def enable_chaos_injection(request: ChaosEnableRequest):
    """
    Enable or disable chaos injection.

    Args:
        request: Configuration for enabling chaos

    Returns:
        Success message with updated status
    """
    if request.enabled:
        enable_chaos()

        # Update configuration if provided
        updates = {}
        if request.probability is not None:
            updates["chaos_probability"] = request.probability
        if request.latency_ms_max is not None:
            updates["latency_ms_max"] = request.latency_ms_max
        if request.chaos_types is not None:
            updates["chaos_types"] = request.chaos_types

        if updates:
            update_chaos_config(**updates)

        return {
            "message": "Chaos injection enabled",
            "status": get_chaos_stats(),
        }
    else:
        disable_chaos()
        return {
            "message": "Chaos injection disabled",
            "status": get_chaos_stats(),
        }


@router.post("/disable")
async def disable_chaos_injection():
    """
    Disable chaos injection.

    Returns:
        Success message with updated status
    """
    disable_chaos()
    return {
        "message": "Chaos injection disabled",
        "status": get_chaos_stats(),
    }


@router.put("/config")
async def update_chaos_configuration(request: ChaosConfigUpdateRequest):
    """
    Update chaos injection configuration.

    Args:
        request: New configuration parameters

    Returns:
        Success message with updated configuration
    """
    updates = {}

    if request.chaos_probability is not None:
        updates["chaos_probability"] = request.chaos_probability
    if request.latency_ms_min is not None:
        updates["latency_ms_min"] = request.latency_ms_min
    if request.latency_ms_max is not None:
        updates["latency_ms_max"] = request.latency_ms_max
    if request.error_codes is not None:
        updates["error_codes"] = request.error_codes
    if request.timeout_ms is not None:
        updates["timeout_ms"] = request.timeout_ms
    if request.chaos_types is not None:
        updates["chaos_types"] = request.chaos_types

    update_chaos_config(**updates)

    return {
        "message": "Chaos configuration updated",
        "updates": updates,
        "status": get_chaos_stats(),
    }


@router.post("/reset")
async def reset_chaos_stats():
    """
    Reset chaos injection statistics.

    Returns:
        Success message
    """
    # Reset counters
    update_chaos_config(chaos_probability=0.1)

    return {
        "message": "Chaos statistics would be reset (not implemented in current version)",
        "status": get_chaos_stats(),
    }


@router.get("/types")
async def list_chaos_types():
    """
    List available chaos types.

    Returns:
        List of available chaos types with descriptions
    """
    return {
        "chaos_types": [
            {
                "type": ChaosType.LATENCY,
                "description": "Inject random latency into requests",
            },
            {
                "type": ChaosType.ERROR,
                "description": "Return HTTP error responses",
            },
            {
                "type": ChaosType.EXCEPTION,
                "description": "Raise exceptions during request processing",
            },
            {
                "type": ChaosType.TIMEOUT,
                "description": "Simulate request timeouts",
            },
            {
                "type": ChaosType.RATE_LIMIT,
                "description": "Simulate rate limiting",
            },
            {
                "type": ChaosType.PARTIAL_FAILURE,
                "description": "Return degraded/partial responses",
            },
            {
                "type": ChaosType.DATA_CORRUPTION,
                "description": "Corrupt response data (not yet implemented)",
            },
        ]
    }


@router.get("/health")
async def chaos_health():
    """
    Health check endpoint for chaos controller.

    Returns:
        Health status
    """
    stats = get_chaos_stats()
    return {
        "status": "healthy",
        "chaos_available": stats is not None,
    }
