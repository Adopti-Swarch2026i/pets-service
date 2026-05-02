"""
API Router — single responsibility: HTTP interface (Dummy / Passive).

This router contains ZERO business logic and ZERO database access.
It simply receives HTTP requests, delegates to PetService, and returns
the result.  All error handling is done by exceptions/error_handlers.py.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict

from app.db.database import get_db
from app.core.security import verify_token
from app.schemas.pet_schema import PetCreate, ReportResponse, PaginatedReportResponse
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


@router.get("", response_model=PaginatedReportResponse)
def list_pets(
    status: Optional[str] = None,
    type: Optional[str] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    service: PetService = Depends(_get_service),
):
    return service.list_reports(
        status=status,
        pet_type=type,
        city=city,
        search=search,
        page=page,
        page_size=page_size,
    )


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


@router.api_route(
    "/upload-image",
    methods=["POST", "PUT", "PATCH"],
    deprecated=True,
    summary="DEPRECATED — usar POST /api/media/upload",
    description=(
        "Este endpoint fue reemplazado por el `media-service`. "
        "Los nuevos clientes deben subir imágenes a `POST /api/media/upload` "
        "(vía gateway). Este endpoint responde 410 Gone."
    ),
)
async def upload_image_deprecated():
    raise HTTPException(
        status_code=410,
        detail={
            "error": "Gone",
            "message": "Este endpoint fue removido. Usa POST /api/media/upload (media-service).",
            "replacement": "/api/media/upload",
        },
    )
