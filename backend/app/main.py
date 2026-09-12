"""Application entry point with compatibility exports used by tests."""

from .core import app, fetch_github_issues, httpx, settings
from .extended import router

app.include_router(router)
