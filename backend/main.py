from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from core.config import settings
from core.database import init_db
from routers import analytics, clean, insights, reports, upload, visualize

# Path to the frontend public/ directory (one level up from backend/)
PUBLIC_DIR = Path(__file__).parent.parent / "public"


# ── Lifespan (startup / shutdown) ────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB tables
    await init_db()
    settings.upload_dir   # ensures upload dir exists
    settings.output_dir   # ensures output dir exists
    yield
    # Shutdown: nothing to clean up


# ── App ───────────────────────────────────────────────────────
app = FastAPI(
    title="Analytic AI API",
    description=(
        "🚀 **Analytic AI** — Full-stack business intelligence backend.\n\n"
        "Upload CSV/Excel data → auto-clean → run NumPy KPI analytics → "
        "generate charts → get AI-written insights → download PDF/Excel reports.\n\n"
        "Built for African SMEs. Kenya (KES) currency-ready.\n\n"
        "**Frontend dashboard**: http://127.0.0.1:8000/app"
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS — allow all origins so dashboard can call API ────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve the frontend at /app ────────────────────────────────
if PUBLIC_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="frontend")

# ── Routers ───────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(clean.router)
app.include_router(analytics.router)
app.include_router(visualize.router)
app.include_router(insights.router)
app.include_router(reports.router)


# ── Home / Health ─────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return JSONResponse({
        "service": "Analytic AI API",
        "version": settings.APP_VERSION,
        "status": "running",
        "dashboard": "http://127.0.0.1:8000/app/dashboard.html",
        "docs": "/docs",
        "currency": settings.DEFAULT_CURRENCY,
    })


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}

