"""Shadow Permission Analyzer — FastAPI application entry-point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import verify_connectivity
from app.api.routes import router as api_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Shadow Permission Analyzer",
    description="Detects hidden privilege-escalation paths in IAM graphs.",
    version="1.0.0",
)

# CORS
origins = settings.allowed_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router)


# ---------------------------------------------------------------------------
# Startup event
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup():
    if verify_connectivity():
        logging.getLogger(__name__).info("Neo4j is reachable — ready to serve.")
    else:
        logging.getLogger(__name__).warning(
            "Neo4j is NOT reachable. Endpoints that query the database will fail."
        )