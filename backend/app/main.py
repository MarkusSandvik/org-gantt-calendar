from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.routers import (
    activities,
    audit_log,
    auth,
    baselines,
    calendar_events,
    dashboard,
    dependencies,
    export,
    health,
    import_export,
    invitations,
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

CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# These don't act on the ambient authority of an existing session — login
# and password-reset establish or bypass a session rather than use one —
# so there's nothing for a forged cross-site request to ride along on.
CSRF_EXEMPT_PATHS = {
    f"{API_PREFIX}/auth/login",
    f"{API_PREFIX}/auth/password-reset/request",
    f"{API_PREFIX}/auth/password-reset/confirm",
    f"{API_PREFIX}/invitations/accept",
}


@app.middleware("http")
async def csrf_protect(request: Request, call_next):
    """Double-submit CSRF check. Only meaningful once a session cookie
    exists — a mutating request with no session cookie has no session to
    forge on behalf of, and is instead rejected by each route's own
    get_current_user dependency (401) where authentication is required."""
    if request.method not in CSRF_SAFE_METHODS and request.url.path not in CSRF_EXEMPT_PATHS:
        session_cookie = request.cookies.get(settings.session_cookie_name)
        if session_cookie:
            csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
            csrf_header = request.headers.get("x-csrf-token")
            if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
                return JSONResponse(
                    status_code=403, content={"detail": "Missing or invalid CSRF token"}
                )
    return await call_next(request)


app.include_router(health.router, prefix=API_PREFIX)
app.include_router(auth.router, prefix=API_PREFIX)
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
app.include_router(audit_log.router, prefix=API_PREFIX)
app.include_router(baselines.router, prefix=API_PREFIX)
app.include_router(search.router, prefix=API_PREFIX)
app.include_router(import_export.router, prefix=API_PREFIX)
app.include_router(invitations.router, prefix=API_PREFIX)
app.include_router(export.router, prefix=API_PREFIX)
