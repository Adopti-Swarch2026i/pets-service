"""
Service layer — single responsibility: business logic & orchestration.

Consumes the PetRepository for data access, enforces domain rules,
and raises domain exceptions (never HTTPException).
"""

from typing import Optional, Dict, List

from sqlalchemy.orm import Session

from app.crud.pet_repository import PetRepository
from app.schemas.pet_schema import PetCreate
from app.exceptions.pet_exceptions import PetNotFoundError, NotPetOwnerError
from app.models.pet_model import Report


class PetService:
    """Orchestrates business logic for pets and reports."""

    def __init__(self, db: Session):
        self._repository = PetRepository(db)

    # ── Stats ────────────────────────────────────────────

    def get_stats(self) -> Dict[str, int]:
        total = self._repository.count_all_reports()
        lost = self._repository.count_reports_by_status("lost")
        found = self._repository.count_reports_by_status("found")
        return {"total_reports": total, "lost": lost, "found": found}

    # ── List & Detail ────────────────────────────────────

    def list_reports(
        self,
        status: Optional[str] = None,
        pet_type: Optional[str] = None,
    ) -> List[Report]:
        return self._repository.get_all_reports(status=status, pet_type=pet_type)

    def get_report(self, report_id: int) -> Report:
        report = self._repository.get_report_by_id(report_id)
        if not report:
            raise PetNotFoundError(f"Report with id {report_id} not found")
        return report

    # ── Create ───────────────────────────────────────────

    def create_report(self, data: PetCreate, owner_id: str) -> Report:
        return self._repository.create_pet_and_report(data, owner_id)

    # ── Update ───────────────────────────────────────────

    def update_report(self, report_id: int, data: PetCreate, owner_id: str) -> Report:
        report = self._get_owned_report(report_id, owner_id)
        return self._repository.update_report(report, data)

    # ── Delete ───────────────────────────────────────────

    def delete_report(self, report_id: int, owner_id: str) -> Dict[str, str]:
        report = self._get_owned_report(report_id, owner_id)
        self._repository.delete_report(report)
        return {"message": "Deleted"}

    # ── Private helpers (DRY) ────────────────────────────

    def _get_owned_report(self, report_id: int, owner_id: str) -> Report:
        """Centralised guard: fetch report and verify ownership.

        Eliminates the duplicated not-found + forbidden checks
        that were previously in update_pet and delete_pet.
        """
        report = self._repository.get_report_by_id(report_id)
        if not report:
            raise PetNotFoundError(f"Report with id {report_id} not found")
        if report.owner_id != owner_id:
            raise NotPetOwnerError()
        return report
