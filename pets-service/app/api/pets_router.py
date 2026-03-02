"""
API Router — single responsibility: HTTP interface (Dummy / Passive).

This router contains ZERO business logic and ZERO database access.
It simply receives HTTP requests, delegates to PetService, and returns
the result.  All error handling is done by exceptions/error_handlers.py.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional, List, Dict

from app.db.database import get_db
from app.core.security import verify_token
from app.schemas.pet_schema import PetCreate, ReportResponse
from app.services.pet_service import PetService

router = APIRouter(prefix="/api/pets", tags=["Pets"])


# ── Dependency ───────────────────────────────────────────

def _get_service(db: Session = Depends(get_db)) -> PetService:
    """Provides a PetService instance per request via dependency injection."""
    return PetService(db)


# ── Endpoints ────────────────────────────────────────────


@router.get("/stats")
def get_stats(service: PetService = Depends(_get_service)) -> Dict[str, int]:
    return service.get_stats()


@router.get("", response_model=List[ReportResponse])
def list_pets(
    status: Optional[str] = None,
    type: Optional[str] = None,
    service: PetService = Depends(_get_service),
):
    return service.list_reports(status=status, pet_type=type)


@router.get("/{id}", response_model=ReportResponse)
def get_pet(id: int, service: PetService = Depends(_get_service)):
    return service.get_report(id)


@router.post("", response_model=ReportResponse)
def create_pet(
    pet_data: PetCreate,
    user=Depends(verify_token),
    service: PetService = Depends(_get_service),
):
    return service.create_report(pet_data, user["uid"])


@router.put("/{id}")
def update_pet(
    id: int,
    pet_data: PetCreate,
    user=Depends(verify_token),
    service: PetService = Depends(_get_service),
):
    return service.update_report(id, pet_data, user["uid"])


@router.delete("/{id}")
def delete_pet(
    id: int,
    user=Depends(verify_token),
    service: PetService = Depends(_get_service),
):
    return service.delete_report(id, user["uid"])
