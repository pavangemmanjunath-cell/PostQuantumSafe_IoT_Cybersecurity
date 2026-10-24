"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .. import __version__
from ..config import Settings, get_settings
from ..orchestrator import AssessmentPipeline
from .routes import assessments, simulations, system
from .state import AppState, AssessmentStore

DESCRIPTION = """
Explainable multi-agent post-quantum risk assessment for clinical IoT and healthcare AI (**research prototype**).

* `POST /api/v1/assessments` — run the agent pipeline on one system.
* `WS /api/v1/ws/assessments` — same, streaming every agent step live.
* `/api/v1/tools` — the evidence tools the agents call, exposed as APIs.
* `/api/v1/simulations` — IoT fleet simulator with attack injection, mitigations and a live WebSocket stream.
* PDF reports state whether the assessed environment is safe.
"""


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="TIPPSS SafeGuard-PQ API", version=__version__, description=DESCRIPTION,
                  license_info={"name": "Apache-2.0", "identifier": "Apache-2.0"})
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False,
                       allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"],
                       expose_headers=["Content-Disposition"])
    app.state.core = AppState(settings=settings, pipeline=AssessmentPipeline(settings),
                              assessments=AssessmentStore(settings.assessment_store_size))
    app.include_router(system.router, prefix="/api/v1")
    app.include_router(assessments.router, prefix="/api/v1")
    app.include_router(simulations.router, prefix="/api/v1")
    return app


app = create_app()
