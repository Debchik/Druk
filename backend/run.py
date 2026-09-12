from app.main import app
from app.extended import router

app.include_router(router)
