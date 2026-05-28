from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.schemas import (
    BrandGuidelinesCreate,
    BrandGuidelinesRead,
    ClientCreate,
    ClientRead,
    PlatformAccountRead,
)
from backend.db.models import BrandGuidelines, Client, PlatformAccount
from backend.db.session import get_db

router = APIRouter(tags=["settings"])


@router.get("/clients/by-brand-dna/{brand_dna_client_id}", response_model=ClientRead)
def get_client_by_brand_dna(brand_dna_client_id: str, db: Session = Depends(get_db)):
    client = db.execute(
        select(Client).where(Client.brand_dna_client_id == brand_dna_client_id)
    ).scalar_one_or_none()
    if not client:
        raise HTTPException(404, "No Campaign Director client linked to this Brand DNA client")
    return client


@router.get("/clients", response_model=list[ClientRead])
def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return db.query(Client).order_by(Client.name).offset(skip).limit(limit).all()


@router.post("/clients", response_model=ClientRead, status_code=201)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)):
    client = Client(**payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/clients/{client_id}", response_model=ClientRead)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(404, "Client not found")
    return client


@router.get("/guidelines/{client_id}", response_model=BrandGuidelinesRead)
def get_brand_guidelines(client_id: int, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(404, "Client not found")
    guidelines = (
        db.query(BrandGuidelines)
        .filter(BrandGuidelines.client_id == client_id)
        .first()
    )
    if not guidelines:
        raise HTTPException(404, "Brand guidelines not found")
    return guidelines


@router.put("/guidelines/{client_id}", response_model=BrandGuidelinesRead)
def upsert_brand_guidelines(
    client_id: int,
    payload: BrandGuidelinesCreate,
    db: Session = Depends(get_db),
):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(404, "Client not found")

    guidelines = (
        db.query(BrandGuidelines)
        .filter(BrandGuidelines.client_id == client_id)
        .first()
    )
    data = payload.model_dump(exclude_unset=True)

    if guidelines:
        for key, value in data.items():
            setattr(guidelines, key, value)
    else:
        guidelines = BrandGuidelines(client_id=client_id, **data)
        db.add(guidelines)

    db.commit()
    db.refresh(guidelines)
    return guidelines


@router.get("/accounts/{client_id}", response_model=list[PlatformAccountRead])
def list_platform_accounts(
    client_id: int,
    active_only: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(404, "Client not found")

    q = db.query(PlatformAccount).filter(PlatformAccount.client_id == client_id)
    if active_only is True:
        q = q.filter(PlatformAccount.is_active.is_(True))
    elif active_only is False:
        q = q.filter(PlatformAccount.is_active.is_(False))

    return q.order_by(PlatformAccount.platform).all()


@router.delete("/accounts/{account_id}", status_code=204)
def disconnect_platform_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(PlatformAccount, account_id)
    if not account:
        raise HTTPException(404, "Platform account not found")
    account.is_active = False
    db.commit()
