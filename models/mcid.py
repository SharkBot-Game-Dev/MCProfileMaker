from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base

class MCID(Base):
    __tablename__ = "mcid"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    mcid: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )