from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


class PetBase(BaseModel):
    name: str
    # En entrada (PetCreate) lo restringimos al enum de events.md §4.1; en
    # respuesta lo dejamos como str libre para no romper datos legacy.
    type: str
    breed: Optional[str] = None
    color: Optional[str] = None
    age: Optional[str] = None


class PetCreate(PetBase):
    type: Literal["dog", "cat", "other"]
    status: Literal["lost", "found", "reunited"]
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
