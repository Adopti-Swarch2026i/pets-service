"""
Repository layer — single responsibility: data access.

All database interactions for Pet and Report entities
are encapsulated here, keeping services and routers
completely decoupled from SQLAlchemy.
"""

from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.pet_model import Pet, Report
from app.schemas.pet_schema import PetCreate


class PetRepository:
    """Handles all CRUD operations for Pet and Report entities."""

    def __init__(self, db: Session):
        self._db = db

    # ── Queries ──────────────────────────────────────────

    def count_all_reports(self) -> int:
        return self._db.query(Report).count()

    def count_reports_by_status(self, status: str) -> int:
        return self._db.query(Report).filter(Report.status == status).count()

    def get_all_reports(
        self,
        status: Optional[str] = None,
        pet_type: Optional[str] = None,
    ) -> List[Report]:
        query = self._db.query(Report).join(Pet)

        if status:
            query = query.filter(Report.status == status)
        if pet_type:
            query = query.filter(Pet.type == pet_type)

        return query.all()

    def get_report_by_id(self, report_id: int) -> Optional[Report]:
        return self._db.query(Report).filter(Report.id == report_id).first()

    # ── Mutations ────────────────────────────────────────

    def create_pet_and_report(self, data: PetCreate, owner_id: str) -> Report:
        """Creates a Pet and its associated Report in a single transaction."""
        new_pet = Pet(
            name=data.name,
            type=data.type,
            breed=data.breed,
            color=data.color,
        )
        self._db.add(new_pet)
        self._db.flush()  # get new_pet.id without committing

        new_report = Report(
            status=data.status,
            location=data.location,
            description=data.description,
            pet_id=new_pet.id,
            owner_id=owner_id,
        )
        self._db.add(new_report)
        self._db.commit()
        self._db.refresh(new_report)

        return new_report

    def update_report(self, report: Report, data: PetCreate) -> Report:
        report.status = data.status
        report.location = data.location
        report.description = data.description
        self._db.commit()
        self._db.refresh(report)
        return report

    def delete_report(self, report: Report) -> None:
        self._db.delete(report)
        self._db.commit()
