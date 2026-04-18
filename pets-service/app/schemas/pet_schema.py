from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PetBase(BaseModel):
    name: str
    type: str
    breed: Optional[str] = None
    color: Optional[str] = None
    age: Optional[str] = None


class PetCreate(PetBase):
    status: str
    location: str
    city: str
    description: str
    owner_phone: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)


class PetResponse(PetBase):
    id: int
    image_urls: List[str] = Field(default_factory=list)

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
