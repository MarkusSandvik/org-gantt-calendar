from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import (
    activities,
    calendar_events,
    dashboard,
    dependencies,
    health,
    milestones,
    projects,
    scheduling,
    search,
    tags,
    teams,
    users,
)

settings = get_settings()

app = FastAPI(title="Org Gantt & Calendar API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(health.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(teams.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(tags.router, prefix=API_PREFIX)
app.include_router(activities.router, prefix=API_PREFIX)
app.include_router(dependencies.router, prefix=API_PREFIX)
app.include_router(scheduling.router, prefix=API_PREFIX)
app.include_router(milestones.router, prefix=API_PREFIX)
app.include_router(calendar_events.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(search.router, prefix=API_PREFIX)
