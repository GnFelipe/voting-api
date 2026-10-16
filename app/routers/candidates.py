from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.database import get_db
from app.models import Candidate, Vote, Voter
from app.schemas import CandidateCreate, CandidateOut

router = APIRouter(
    prefix="/candidates", tags=["Candidates"], dependencies=[Depends(require_auth)]
)


@router.post("", response_model=CandidateOut, status_code=status.HTTP_201_CREATED)
def create_candidate(payload: CandidateCreate, db: Session = Depends(get_db)):
    """Registra un candidato. Su nombre no puede coincidir con el de un votante."""
    if db.scalar(select(Voter.id).where(func.lower(Voter.name) == payload.name.lower()).limit(1)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Esta persona ya esta registrada como votante"
        )
    candidate = Candidate(name=payload.name, party=payload.party)
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("", response_model=list[CandidateOut])
def list_candidates(
    response: Response,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    name: str | None = Query(None, description="Filtra por nombre (contiene)"),
    party: str | None = Query(None, description="Filtra por partido (contiene)"),
    db: Session = Depends(get_db),
):
    """Lista candidatos con paginacion y filtros. Total en el header X-Total-Count."""
    stmt = select(Candidate)
    if name:
        stmt = stmt.where(func.lower(Candidate.name).contains(name.lower(), autoescape=True))
    if party:
        stmt = stmt.where(func.lower(Candidate.party).contains(party.lower(), autoescape=True))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(Candidate.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidato no encontrado")
    return candidate


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """Elimina un candidato. Si ya tiene votos se rechaza (409) para no alterar resultados."""
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidato no encontrado")
    if candidate.votes > 0 or db.scalar(
        select(Vote.id).where(Vote.candidate_id == candidate_id).limit(1)
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "No se puede eliminar un candidato que ya tiene votos"
        )
    db.delete(candidate)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
