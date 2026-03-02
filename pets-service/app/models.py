from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    type = Column(String)  # dog, cat, etc
    breed = Column(String)
    color = Column(String)

    reports = relationship("Report", back_populates="pet")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String)  # lost / found
    location = Column(String)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pet_id = Column(Integer, ForeignKey("pets.id"))
    owner_id = Column(String)  # Firebase UID

    pet = relationship("Pet", back_populates="reports")
