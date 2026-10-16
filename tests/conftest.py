import os

# Debe definirse ANTES de importar la app: los tests usan SQLite, sin necesitar PostgreSQL
os.environ["DATABASE_URL"] = "sqlite:///./test_voting.db"
os.environ["AUTH_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def make_voter(client, name="Ana Torres", email="ana@example.com"):
    r = client.post("/voters", json={"name": name, "email": email})
    assert r.status_code == 201, r.text
    return r.json()


def make_candidate(client, name="Carlos Perez", party="Partido Azul"):
    r = client.post("/candidates", json={"name": name, "party": party})
    assert r.status_code == 201, r.text
    return r.json()
