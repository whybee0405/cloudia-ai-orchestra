from fastapi import FastAPI
from app.api.clients import router as clients_router
from app.api.brand_dna import router as brand_dna_router
from app.api.personas import router as personas_router
from app.api.internal import router as internal_router
from app.api.suggestions import router as suggestions_router
from app.api.logo import router as logo_router
from app.api.scrape import router as scrape_router
from app.api.reporting import router as reporting_router


def register_routes(app: FastAPI) -> None:
    app.include_router(clients_router)
    app.include_router(brand_dna_router)
    app.include_router(personas_router)
    app.include_router(internal_router)
    app.include_router(suggestions_router)
    app.include_router(logo_router)
    app.include_router(scrape_router)
    app.include_router(reporting_router)
