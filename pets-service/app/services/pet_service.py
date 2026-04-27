"""
Service layer — single responsibility: business logic & orchestration.

Consumes the PetRepository for data access, enforces domain rules,
and raises domain exceptions (never HTTPException).
"""

from typing import Optional, Dict, List, Iterable
from datetime import datetime, timezone
import cloudinary.uploader

from sqlalchemy.orm import Session
from firebase_admin import auth as fb_auth

from app.crud.pet_repository import PetRepository
from app.schemas.pet_schema import (
    PetCreate,
    PetResponse,
    ReportResponse,
    PaginatedReportResponse,
)
from app.exceptions.pet_exceptions import (
    ImageUploadError,
    PetNotFoundError,
    NotPetOwnerError,
)
from app.models.pet_model import Report
from app.messaging.publisher import get_publisher


MAX_SIZE_MB = 5


class PetService:
    """Orchestrates business logic for pets and reports."""

    def __init__(self, db: Session):
        self._repository = PetRepository(db)

    # ── Stats ────────────────────────────────────────────

    def get_stats(self) -> Dict[str, int]:
        total = self._repository.count_all_reports()
        lost = self._repository.count_reports_by_status("lost")
        found = self._repository.count_reports_by_status("found")
        reunited = self._repository.count_reports_by_status("reunited")
        return {
            "total_reports": total,
            "lost": lost,
            "found": found,
            "reunited": reunited,
        }

    # -- Upload images --
    def upload_image(
        self, file_content: bytes, content_type: str, owner_id: str
    ) -> str:
        if len(file_content) > MAX_SIZE_MB * 1024 * 1024:
            raise ImageUploadError(f"File exceeds the {MAX_SIZE_MB}MB limit.")

        try:
            result = cloudinary.uploader.upload(
                file_content,
                folder=f"pets/{owner_id}",
                allowed_formats=["jpg", "jpeg", "png", "webp"],
                transformation={"quality": "auto", "fetch_format": "auto"},
            )
        except Exception as e:
            raise ImageUploadError(f"Could not upload image: {str(e)}")

        return result["secure_url"]

    # ── List & Detail ────────────────────────────────────

    def list_reports(
        self,
        status: Optional[str] = None,
        pet_type: Optional[str] = None,
        city: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedReportResponse:
        records, total = self._repository.get_all_reports(
            status=status,
            pet_type=pet_type,
            city=city,
            search=search,
            page=page,
            page_size=page_size,
        )
        names = self._resolve_names_bulk(r.owner_id for r in records)
        results = [
            self._to_response(r, names.get(r.owner_id, r.owner_id))
            for r in records
        ]
        return PaginatedReportResponse(
            total=total,
            page=page,
            page_size=page_size,
            results=results,
        )

    def get_report(self, report_id: int) -> ReportResponse:
        report = self._repository.get_report_by_id(report_id)
        if not report:
            raise PetNotFoundError(f"Report with id {report_id} not found")
        name = self._resolve_name(report.owner_id)
        return self._to_response(report, name)

    # ── Create ───────────────────────────────────────────

    def create_report(self, data: PetCreate, owner_id: str) -> ReportResponse:
        report = self._repository.create_pet_and_report(data, owner_id)
        name = self._resolve_name(owner_id)

        get_publisher().publish("pet.report.created", {
            "petId": report.pet.id,
            "reportId": report.id,
            "ownerId": owner_id,
            "type": report.pet.type,
            "breed": report.pet.breed,
            "color": report.pet.color,
            "status": report.status,
            "city": report.city,
            "createdAt": report.created_at.isoformat(),
        })

        return self._to_response(report, name)

    # ── Update ───────────────────────────────────────────

    def update_report(
        self, report_id: int, data: PetCreate, owner_id: str
    ) -> ReportResponse:
        report = self._get_owned_report(report_id, owner_id)
        old_status = report.status
        updated = self._repository.update_report(report, data)
        name = self._resolve_name(owner_id)

        if updated.status == "reunited" and old_status != "reunited":
            get_publisher().publish("pet.report.reunited", {
                "petId": updated.pet.id,
                "reportId": updated.id,
                "ownerId": owner_id,
                "reunitedAt": datetime.now(timezone.utc).isoformat(),
            })
        else:
            get_publisher().publish("pet.report.updated", {
                "petId": updated.pet.id,
                "reportId": updated.id,
                "status": updated.status,
                "updatedAt": datetime.now(timezone.utc).isoformat(),
            })

        return self._to_response(updated, name)

    # ── Delete ───────────────────────────────────────────

    def delete_report(self, report_id: int, owner_id: str) -> Dict[str, str]:
        report = self._get_owned_report(report_id, owner_id)
        self._repository.delete_report(report)
        return {"message": "Deleted"}

    # ── Private helpers ────────────────────────────

    def _get_owned_report(self, report_id: int, owner_id: str) -> Report:
        """Centralised guard: fetch report and verify ownership."""
        report = self._repository.get_report_by_id(report_id)
        if not report:
            raise PetNotFoundError(f"Report with id {report_id} not found")
        if report.owner_id != owner_id:
            raise NotPetOwnerError()
        return report

    def _resolve_name(self, uid: str) -> str:
        """Resolve a Firebase UID to a human-readable name.

        Falls back to email and then UID if the user has no display name
        or cannot be fetched.
        """
        try:
            user = fb_auth.get_user(uid)
            return user.display_name or user.email or uid
        except Exception:
            return uid

    def _resolve_names_bulk(self, uids: Iterable[str]) -> Dict[str, str]:
        """Batch-resolve Firebase UIDs via get_users (avoids N calls)."""
        unique = {u for u in uids if u}
        if not unique:
            return {}
        try:
            identifiers = [fb_auth.UidIdentifier(u) for u in unique]
            result = fb_auth.get_users(identifiers)
            names: Dict[str, str] = {}
            for user in result.users:
                names[user.uid] = user.display_name or user.email or user.uid
            for nf in result.not_found:
                uid = getattr(nf, "uid", None)
                if uid:
                    names[uid] = uid
            for uid in unique:
                names.setdefault(uid, uid)
            return names
        except Exception:
            return {uid: uid for uid in unique}

    def _to_response(self, report: Report, owner_name: str) -> ReportResponse:
        return ReportResponse(
            id=report.id,
            status=report.status,
            location=report.location,
            city=report.city,
            description=report.description,
            owner_name=owner_name,
            owner_phone=report.owner_phone,
            owner_id=report.owner_id,
            created_at=report.created_at,
            pet=PetResponse(
                id=report.pet.id,
                name=report.pet.name,
                type=report.pet.type,
                breed=report.pet.breed,
                color=report.pet.color,
                age=report.pet.age,
                image_urls=list(report.pet.image_urls or []),
            ),
        )
