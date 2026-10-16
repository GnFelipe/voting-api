from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class VoterCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120, examples=["Ana Torres"])
    email: EmailStr = Field(examples=["ana@example.com"])


class VoterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    has_voted: bool


class CandidateCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120, examples=["Carlos Perez"])
    party: str | None = Field(default=None, max_length=120, examples=["Partido Azul"])

    @field_validator("party")
    @classmethod
    def empty_party_to_none(cls, v: str | None) -> str | None:
        return v or None


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    party: str | None
    votes: int


class VoteCreate(BaseModel):
    voter_id: int = Field(gt=0, examples=[1])
    candidate_id: int = Field(gt=0, examples=[1])


class VoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voter_id: int
    candidate_id: int
    created_at: datetime


class CandidateStats(BaseModel):
    candidate_id: int
    name: str
    party: str | None
    votes: int
    percentage: float


class VotingStatistics(BaseModel):
    total_votes: int
    total_voters: int
    voters_who_voted: int
    participation_percentage: float
    candidates: list[CandidateStats]


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
