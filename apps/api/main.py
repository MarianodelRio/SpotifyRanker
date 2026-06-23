import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.routers.auth import router as auth_router
from apps.api.routers.feedback import router as feedback_router
from apps.api.routers.import_router import router as import_router
from apps.api.routers.library_router import router as library_router
from apps.api.routers.model_router import router as model_router
from apps.api.routers.playlist_router import router as playlist_router
from apps.api.routers.profile_router import router as profile_router

logger = logging.getLogger(__name__)

app = FastAPI(title="TasteRanker API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(feedback_router)
app.include_router(import_router)
app.include_router(library_router)
app.include_router(model_router)
app.include_router(playlist_router)
app.include_router(profile_router)


@app.exception_handler(Exception)
async def _unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
