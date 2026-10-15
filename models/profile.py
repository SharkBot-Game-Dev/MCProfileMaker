from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ARRAY

from models.base import Base

class Profile(Base):
    __tablename__ = "profile"

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

    favoriteServerIps: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        default=list
    )

    background: Mapped[list[str]] = mapped_column(
        String,
        nullable=False,
    )