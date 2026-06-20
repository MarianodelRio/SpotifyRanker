from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers.auth import router as auth_router
from apps.api.routers.feedback import router as feedback_router
from apps.api.routers.import_router import router as import_router
from apps.api.routers.library_router import router as library_router

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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
