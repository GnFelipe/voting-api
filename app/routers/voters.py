from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import require_auth
from app.database import get_db
from app.models import Candidate, Vote, Voter
from app.schemas import VoterCreate, VoterOut

router = APIRouter(prefix="/voters", tags=["Voters"], dependencies=[Depends(require_auth)])


@router.post("", response_model=VoterOut, status_code=status.HTTP_201_CREATED)
def create_voter(payload: VoterCreate, db: Session = Depends(get_db)):
    """Registra un votante. Email unico; el nombre no puede coincidir con un candidato."""
    email = payload.email.lower()

    if db.scalar(select(Candidate.id).where(func.lower(Candidate.name) == payload.name.lower()).limit(1)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Esta persona ya esta registrada como candidato"
        )
    if db.scalar(select(Voter.id).where(Voter.email == email).limit(1)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un votante con ese email")

    voter = Voter(name=payload.name, email=email)
    db.add(voter)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un votante con ese email")
    db.refresh(voter)
    return voter


@router.get("", response_model=list[VoterOut])
def list_voters(
    response: Response,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    name: str | None = Query(None, description="Filtra por nombre (contiene)"),
    has_voted: bool | None = Query(None, description="Filtra por estado de voto"),
    db: Session = Depends(get_db),
):
    """Lista votantes con paginacion y filtros. Total en el header X-Total-Count."""
    stmt = select(Voter)
    if name:
        stmt = stmt.where(func.lower(Voter.name).contains(name.lower(), autoescape=True))
    if has_voted is not None:
        stmt = stmt.where(Voter.has_voted.is_(has_voted))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(Voter.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get("/{voter_id}", response_model=VoterOut)
def get_voter(voter_id: int, db: Session = Depends(get_db)):
    voter = db.get(Voter, voter_id)
    if not voter:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Votante no encontrado")
    return voter


@router.delete("/{voter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_voter(voter_id: int, db: Session = Depends(get_db)):
    """Elimina un votante. Si ya voto se rechaza (409) para no alterar los resultados."""
    voter = db.get(Voter, voter_id)
    if not voter:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Votante no encontrado")
    if voter.has_voted or db.scalar(select(Vote.id).where(Vote.voter_id == voter_id).limit(1)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "No se puede eliminar un votante que ya emitio su voto"
        )
    db.delete(voter)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
