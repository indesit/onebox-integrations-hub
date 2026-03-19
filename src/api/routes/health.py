"""GET /health — liveness + dependency readiness (HUB-004)."""

from fastapi import APIRouter

from src.core.queue import get_redis

router = APIRouter(tags=["ops"])


@router.get("/health", summary="Hub health check")
async def health_check() -> dict:
    checks: dict[str, str] = {}

    # Redis
    try:
        get_redis().ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
