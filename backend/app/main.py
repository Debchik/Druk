"""Application entry point with compatibility exports used by tests and API wiring."""

from .core import app, fetch_github_issues, httpx, settings
from .extended import router
from .bug_reports import router as bug_reports_router

app.include_router(router)
app.include_router(bug_reports_router)
