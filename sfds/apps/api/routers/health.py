"""
Health Router — system readiness and connectivity checks.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health():
    return {"status": "ok", "system": "SFDS v3", "version": "3.1.0"}


@router.get("/ready")
async def readiness():
    """
    Check connectivity to all data stores.
    Used by Docker healthcheck and load balancers.
    """
    from packages.config.connections import check_connections
    status = await check_connections()
    all_ok = all(v for v in status.values())
    return {
        "ready": all_ok,
        "services": status,
    }
