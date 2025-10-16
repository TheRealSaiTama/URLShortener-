from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class UrlMap(Base):
    __tablename__ = "url_map"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    target: Mapped[str] = mapped_column(String(2048))
