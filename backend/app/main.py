from .core import app
from .extended import router

app.include_router(router)
