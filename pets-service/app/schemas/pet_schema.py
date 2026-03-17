from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PetBase(BaseModel):
    name: str
    type: str
    breed: Optional[str] = None
    color: Optional[str] = None


class PetCreate(PetBase):
    status: str
    location: str
    city: str
    description: str
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    image_url: Optional[str] = None


class PetResponse(PetBase):
    id: int
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    id: int
    status: str
    location: str
    city: str
    description: str
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_id: str
    created_at: datetime
    pet: PetResponse

    class Config:
        from_attributes = True


class PaginatedReportResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[ReportResponse]
