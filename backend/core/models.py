import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    filename: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    domain: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )

    chunks = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    facts = relationship(
        "Fact",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id"),
        nullable=False,
    )

    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    chunk_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    has_facts: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    document = relationship(
        "Document",
        back_populates="chunks",
    )

    facts = relationship(
        "Fact",
        back_populates="chunk",
        cascade="all, delete-orphan",
    )


class Fact(Base):
    __tablename__ = "facts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id"),
        nullable=False,
    )

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chunks.id"),
        nullable=False,
    )

    entity: Mapped[str] = mapped_column(Text, nullable=False)
    attribute: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    unit: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_scope: Mapped[str | None] = mapped_column(Text, nullable=True)

    qualifiers: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(768),
        nullable=True,
    )

    document = relationship("Document", back_populates="facts")
    chunk = relationship("Chunk", back_populates="facts")
