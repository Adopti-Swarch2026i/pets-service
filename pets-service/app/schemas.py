from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PetBase(BaseModel):
    name: str
    type: str
    breed: Optional[str]
    color: Optional[str]


class PetCreate(PetBase):
    status: str
    location: str
    description: str


class PetResponse(PetBase):
    id: int

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    id: int
    status: str
    location: str
    description: str
    created_at: datetime
    pet: PetResponse

    class Config:
        from_attributes = True
