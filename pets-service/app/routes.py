from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models, schemas
from .database import get_db
from .firebase_auth import verify_token
from typing import Optional

router = APIRouter(prefix="/api/pets", tags=["Pets"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total = db.query(models.Report).count()
    lost = db.query(models.Report).filter(models.Report.status == "lost").count()
    found = db.query(models.Report).filter(models.Report.status == "found").count()

    return {"total_reports": total, "lost": lost, "found": found}


@router.get("", response_model=list[schemas.ReportResponse])
def list_pets(
    status: Optional[str] = None,
    type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Report).join(models.Pet)

    if status:
        query = query.filter(models.Report.status == status)

    if type:
        query = query.filter(models.Pet.type == type)

    return query.all()


@router.get("/{id}", response_model=schemas.ReportResponse)
def get_pet(id: int, db: Session = Depends(get_db)):
    report = db.query(models.Report).filter(models.Report.id == id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    return report


@router.post("", response_model=schemas.ReportResponse)
def create_pet(
    pet_data: schemas.PetCreate,
    user=Depends(verify_token),
    db: Session = Depends(get_db),
):
    new_pet = models.Pet(
        name=pet_data.name,
        type=pet_data.type,
        breed=pet_data.breed,
        color=pet_data.color,
    )

    db.add(new_pet)
    db.commit()
    db.refresh(new_pet)

    new_report = models.Report(
        status=pet_data.status,
        location=pet_data.location,
        description=pet_data.description,
        pet_id=new_pet.id,
        owner_id=user["uid"],
    )

    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return new_report


@router.put("/{id}")
def update_pet(
    id: int,
    pet_data: schemas.PetCreate,
    user=Depends(verify_token),
    db: Session = Depends(get_db),
):
    report = db.query(models.Report).filter(models.Report.id == id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Not found")

    if report.owner_id != user["uid"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    report.status = pet_data.status
    report.location = pet_data.location
    report.description = pet_data.description

    db.commit()
    return report


@router.delete("/{id}")
def delete_pet(id: int, user=Depends(verify_token), db: Session = Depends(get_db)):
    report = db.query(models.Report).filter(models.Report.id == id).first()

    if not report:
        raise HTTPException(status_code=404)

    if report.owner_id != user["uid"]:
        raise HTTPException(status_code=403)

    db.delete(report)
    db.commit()

    return {"message": "Deleted"}
