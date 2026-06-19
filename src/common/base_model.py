from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base
from src.common.mixins.timestamp_mixin import TimestampMixin


class BaseModel(TimestampMixin, Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
