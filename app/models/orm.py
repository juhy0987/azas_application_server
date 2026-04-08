from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
  pass


class DocumentRow(Base):
  __tablename__ = "documents"

  id: Mapped[str] = mapped_column(String, primary_key=True)
  title: Mapped[str] = mapped_column(String, nullable=False)
  subtitle: Mapped[str] = mapped_column(String, nullable=False, default="")

  blocks: Mapped[list[BlockRow]] = relationship(
    back_populates="document",
    cascade="all, delete-orphan",
    foreign_keys="[BlockRow.document_id]",
  )


class BlockRow(Base):
  __tablename__ = "blocks"

  id: Mapped[str] = mapped_column(String, primary_key=True)
  document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
  parent_block_id: Mapped[str | None] = mapped_column(String, nullable=True)
  type: Mapped[str] = mapped_column(String, nullable=False)
  position: Mapped[int] = mapped_column(Integer, nullable=False)
  content_json: Mapped[str] = mapped_column(Text, nullable=False)

  document: Mapped[DocumentRow] = relationship(
    back_populates="blocks",
    foreign_keys=[document_id],
  )
