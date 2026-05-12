from apps.api.routers.decision import router as decision_router
from apps.api.routers.formation import router as formation_router
from apps.api.routers.graph import router as graph_router
from apps.api.routers.time_series import router as time_router
from apps.api.routers.vector import router as vector_router
from apps.api.routers.health import router as health_router
from apps.api.routers.system import router as system_router

__all__ = [
    "decision_router",
    "formation_router",
    "graph_router",
    "time_router",
    "vector_router",
    "health_router",
    "system_router",
]
