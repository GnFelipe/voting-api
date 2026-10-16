from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.database import get_db
from app.models import Candidate, Vote, Voter
from app.schemas import CandidateStats, VoteCreate, VoteOut, VotingStatistics

router = APIRouter(prefix="/votes", tags=["Votes"], dependencies=[Depends(require_auth)])


def _pct(part: int, total: int) -> float:
    return round(part * 100 / total, 2) if total else 0.0


@router.post("", response_model=VoteOut, status_code=status.HTTP_201_CREATED)
def cast_vote(payload: VoteCreate, db: Session = Depends(get_db)):
    """Emite un voto: valida votante/candidato, marca has_voted e incrementa votes."""
    # with_for_update bloquea la fila del votante (PostgreSQL) para evitar doble voto concurrente
    voter = db.get(Voter, payload.voter_id, with_for_update=True)
    if not voter:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Votante no encontrado")
    if voter.has_voted:
        raise HTTPException(status.HTTP_409_CONFLICT, "El votante ya emitio su voto")

    candidate = db.get(Candidate, payload.candidate_id)
    if not candidate:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidato no encontrado")

    vote = Vote(voter_id=voter.id, candidate_id=candidate.id)
    db.add(vote)
    voter.has_voted = True
    # Incremento atomico en la BD (evita condiciones de carrera con read-modify-write)
    db.execute(
        update(Candidate).where(Candidate.id == candidate.id).values(votes=Candidate.votes + 1)
    )
    try:
        db.commit()  # una sola transaccion: voto + has_voted + contador
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El votante ya emitio su voto")
    db.refresh(vote)
    return vote


@router.get("", response_model=list[VoteOut])
def list_votes(
    response: Response,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    candidate_id: int | None = Query(None, description="Filtra por candidato"),
    db: Session = Depends(get_db),
):
    """Lista todos los votos emitidos. Total en el header X-Total-Count."""
    stmt = select(Vote)
    if candidate_id is not None:
        stmt = stmt.where(Vote.candidate_id == candidate_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(Vote.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get("/statistics", response_model=VotingStatistics)
def statistics(db: Session = Depends(get_db)):
    """Votos y porcentaje por candidato, y total de votantes que han votado."""
    total_votes = db.scalar(select(func.count(Vote.id))) or 0
    total_voters = db.scalar(select(func.count(Voter.id))) or 0
    voters_who_voted = db.scalar(
        select(func.count(Voter.id)).where(Voter.has_voted.is_(True))
    ) or 0

    # Se cuenta desde la tabla votes (fuente de verdad)
    rows = db.execute(
        select(Candidate, func.count(Vote.id).label("n"))
        .outerjoin(Vote, Vote.candidate_id == Candidate.id)
        .group_by(Candidate.id)
        .order_by(func.count(Vote.id).desc(), Candidate.id)
    ).all()

    return VotingStatistics(
        total_votes=total_votes,
        total_voters=total_voters,
        voters_who_voted=voters_who_voted,
        participation_percentage=_pct(voters_who_voted, total_voters),
        candidates=[
            CandidateStats(
                candidate_id=c.id,
                name=c.name,
                party=c.party,
                votes=n,
                percentage=_pct(n, total_votes),
            )
            for c, n in rows
        ],
    )
