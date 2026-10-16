from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Voter(Base):
    __tablename__ = "voters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    has_voted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    vote: Mapped[Optional["Vote"]] = relationship(back_populates="voter", uselist=False)


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    party: Mapped[str | None] = mapped_column(String(120), nullable=True)
    votes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    received_votes: Mapped[list["Vote"]] = relationship(back_populates="candidate")


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # unique=True garantiza a nivel de BD que un votante solo vota una vez
    voter_id: Mapped[int] = mapped_column(
        ForeignKey("voters.id"), nullable=False, unique=True, index=True
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    voter: Mapped[Voter] = relationship(back_populates="vote")
    candidate: Mapped[Candidate] = relationship(back_populates="received_votes")
