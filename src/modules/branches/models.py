"""
Branches model — Sprint 2 full schema.
Expands the Sprint 1 scaffold with address, contact, coordinates, photos, and description.
"""
from typing import Optional
from sqlalchemy import Boolean, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.common.base_model import BaseModel


class Branch(BaseModel):
    __tablename__ = "branches"

    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric(10, 7), nullable=True)
    map_embed_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photo_urls: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
