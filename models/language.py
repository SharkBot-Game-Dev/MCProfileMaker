from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class UserLanguage(Base):
    __tablename__ = "user_language"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    language: Mapped[str] = mapped_column(String(2), nullable=False)
