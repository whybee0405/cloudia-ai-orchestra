from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client
from app.agents.scraper import scrape_brand_signals, ScrapeSignals

router = APIRouter(prefix="/api/clients/{client_id}", tags=["scrape"])


@router.post("/scrape", response_model=ScrapeSignals)
def scrape_client_website(client_id: UUID, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if not client.website_url:
        raise HTTPException(status_code=400, detail="Client has no website URL")

    result = scrape_brand_signals(client.name, client.website_url)
    if not result:
        raise HTTPException(status_code=422, detail="Could not extract brand signals from website")

    return result
