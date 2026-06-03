"""
API Router — single responsibility: HTTP interface (Dummy / Passive).

This router contains ZERO business logic and ZERO database access.
It simply receives HTTP requests, delegates to PetService, and returns
the result.  All error handling is done by exceptions/error_handlers.py.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict

from app.db.database import get_db, get_read_db
from app.core.security import verify_token
from app.schemas.pet_schema import PetCreate, ReportResponse, PaginatedReportResponse
from app.services.pet_service import PetService
from app.cache import cached, invalidate_cache_pattern

router = APIRouter(prefix="/api/pets", tags=["Pets"])


# ── Dependency ───────────────────────────────────────────


def _get_service(db: Session = Depends(get_db)) -> PetService:
    """Provides a PetService instance per request via dependency injection."""
    return PetService(db)


def _get_read_service(db: Session = Depends(get_read_db)) -> PetService:
    """PetService bound to read replica for GET endpoints."""
    return PetService(db)


# ── Endpoints ────────────────────────────────────────────


@router.get("/stats")
@cached(ttl_seconds=30, key_fn=lambda *a, **k: "pets:stats")
def get_stats(service: PetService = Depends(_get_read_service)) -> Dict[str, int]:
    return service.get_stats()


@router.get("", response_model=PaginatedReportResponse)
@cached(
    ttl_seconds=15,
    key_fn=lambda *a, **k: (
        f"pets:list:{k.get('status','all')}:{k.get('type','all')}:"
        f"{k.get('city','all')}:{k.get('search','all')}:"
        f"{k.get('page',1)}:{k.get('page_size',20)}"
    ),
)
def list_pets(
    status: Optional[str] = None,
    type: Optional[str] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    service: PetService = Depends(_get_read_service),
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
@cached(ttl_seconds=60, key_fn=lambda *a, **k: f"pets:id:{a[0] if a else k.get('id',0)}")
def get_pet(id: int, service: PetService = Depends(_get_read_service)):
    return service.get_report(id)


@router.post("", response_model=ReportResponse)
def create_pet(
    pet_data: PetCreate,
    user=Depends(verify_token),
    service: PetService = Depends(_get_service),
):
    result = service.create_report(pet_data, user["uid"])
    invalidate_cache_pattern("pets:*")
    return result


@router.put("/{id}")
def update_pet(
    id: int,
    pet_data: PetCreate,
    user=Depends(verify_token),
    service: PetService = Depends(_get_service),
):
    result = service.update_report(id, pet_data, user["uid"])
    invalidate_cache_pattern("pets:*")
    return result


@router.delete("/{id}")
def delete_pet(
    id: int,
    user=Depends(verify_token),
    service: PetService = Depends(_get_service),
):
    result = service.delete_report(id, user["uid"])
    invalidate_cache_pattern("pets:*")
    return result


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
