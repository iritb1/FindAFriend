from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router
from utils.logger import Logger

logger = Logger("api")

app = FastAPI(
    title="Adoption Assistant API",
    description=(
        "AI-powered adoption assistant for animal rescue shelters. "
        "Ask for a dog or cat by size, age, color, breed, or temperament - "
        "get full and partial matches with the gaps explained honestly."
    ),
)

ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(router)

# Serve the built React app from frontend/dist (produced by `npm run build`).
# Docker layout: /app/frontend/dist (sibling of /app/api).
# Local layout: <project_root>/frontend/dist (frontend/ is sibling of backend/).
_HERE = Path(__file__).resolve().parent
_FRONTEND_CANDIDATES = [
    _HERE.parent / "frontend" / "dist",
    _HERE.parent.parent / "frontend" / "dist",
]
FRONTEND_DIST = next(
    (path for path in _FRONTEND_CANDIDATES if path.exists()),
    _FRONTEND_CANDIDATES[0],
)

if FRONTEND_DIST.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIST / "assets")),
        name="assets",
    )

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(str(FRONTEND_DIST / "index.html"))
else:
    logger.warning(
        f"Frontend build not found at {FRONTEND_DIST}. "
        "Run `cd frontend && npm install && npm run build` to enable the UI."
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."},
    )
