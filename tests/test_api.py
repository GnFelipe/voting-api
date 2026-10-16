from tests.conftest import make_candidate, make_voter


# ---------- Votantes ----------
def test_create_and_get_voter(client):
    v = make_voter(client)
    assert v["has_voted"] is False
    r = client.get(f"/voters/{v['id']}")
    assert r.status_code == 200 and r.json()["email"] == "ana@example.com"


def test_voter_validation_errors(client):
    assert client.post("/voters", json={"name": "X", "email": "no-es-email"}).status_code == 422
    assert client.post("/voters", json={"email": "a@b.com"}).status_code == 422
    assert client.post("/voters", json={"name": "  ", "email": "a@b.com"}).status_code == 422


def test_duplicate_email_conflict(client):
    make_voter(client)
    r = client.post("/voters", json={"name": "Otra", "email": "ANA@example.com"})
    assert r.status_code == 409


def test_voter_not_found(client):
    assert client.get("/voters/999").status_code == 404
    assert client.delete("/voters/999").status_code == 404


def test_delete_voter(client):
    v = make_voter(client)
    assert client.delete(f"/voters/{v['id']}").status_code == 204
    assert client.get(f"/voters/{v['id']}").status_code == 404


def test_list_voters_pagination_and_filter(client):
    for i in range(5):
        make_voter(client, name=f"Votante {i}", email=f"v{i}@example.com")
    r = client.get("/voters", params={"page": 2, "page_size": 2})
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.headers["X-Total-Count"] == "5"
    r = client.get("/voters", params={"name": "votante 3"})
    assert [v["email"] for v in r.json()] == ["v3@example.com"]
    assert client.get("/voters", params={"has_voted": True}).json() == []


# ---------- Candidatos ----------
def test_candidate_crud(client):
    c = make_candidate(client)
    assert c["votes"] == 0
    assert client.get(f"/candidates/{c['id']}").json()["party"] == "Partido Azul"
    r = client.post("/candidates", json={"name": "Sin Partido"})
    assert r.status_code == 201 and r.json()["party"] is None
    assert client.get("/candidates", params={"party": "azul"}).json()[0]["id"] == c["id"]
    assert client.delete(f"/candidates/{c['id']}").status_code == 204
    assert client.get(f"/candidates/{c['id']}").status_code == 404


def test_candidate_requires_name(client):
    assert client.post("/candidates", json={"party": "X"}).status_code == 422


# ---------- Voter != Candidate ----------
def test_voter_cannot_be_candidate_and_viceversa(client):
    make_voter(client, name="Juan Gomez", email="juan@example.com")
    r = client.post("/candidates", json={"name": "juan gomez", "party": "P"})
    assert r.status_code == 409

    make_candidate(client, name="Laura Diaz")
    r = client.post("/voters", json={"name": "LAURA DIAZ", "email": "laura@example.com"})
    assert r.status_code == 409


# ---------- Votos ----------
def test_cast_vote_updates_voter_and_candidate(client):
    v = make_voter(client)
    c = make_candidate(client)
    r = client.post("/votes", json={"voter_id": v["id"], "candidate_id": c["id"]})
    assert r.status_code == 201
    assert r.json()["voter_id"] == v["id"]
    assert client.get(f"/voters/{v['id']}").json()["has_voted"] is True
    assert client.get(f"/candidates/{c['id']}").json()["votes"] == 1
    assert len(client.get("/votes").json()) == 1


def test_voter_cannot_vote_twice(client):
    v = make_voter(client)
    c = make_candidate(client)
    assert client.post("/votes", json={"voter_id": v["id"], "candidate_id": c["id"]}).status_code == 201
    r = client.post("/votes", json={"voter_id": v["id"], "candidate_id": c["id"]})
    assert r.status_code == 409
    assert client.get(f"/candidates/{c['id']}").json()["votes"] == 1


def test_vote_with_invalid_ids(client):
    v = make_voter(client)
    c = make_candidate(client)
    assert client.post("/votes", json={"voter_id": v["id"], "candidate_id": 999}).status_code == 404
    assert client.post("/votes", json={"voter_id": 999, "candidate_id": c["id"]}).status_code == 404
    assert client.post("/votes", json={"voter_id": v["id"]}).status_code == 422
    # un voto fallido no debe marcar al votante
    assert client.get(f"/voters/{v['id']}").json()["has_voted"] is False


def test_cannot_delete_voter_or_candidate_with_votes(client):
    v = make_voter(client)
    c = make_candidate(client)
    client.post("/votes", json={"voter_id": v["id"], "candidate_id": c["id"]})
    assert client.delete(f"/voters/{v['id']}").status_code == 409
    assert client.delete(f"/candidates/{c['id']}").status_code == 409


# ---------- Estadisticas ----------
def test_statistics_empty(client):
    r = client.get("/votes/statistics")
    assert r.status_code == 200
    assert r.json() == {
        "total_votes": 0,
        "total_voters": 0,
        "voters_who_voted": 0,
        "participation_percentage": 0.0,
        "candidates": [],
    }


def test_statistics(client):
    c1 = make_candidate(client, name="Carlos Perez", party="Azul")
    c2 = make_candidate(client, name="Sofia Rios", party="Verde")
    c3 = make_candidate(client, name="Mario Lopez", party=None)
    voters = [make_voter(client, name=f"V{i}", email=f"v{i}@x.com") for i in range(4)]
    for voter, cand in [(voters[0], c1), (voters[1], c1), (voters[2], c2)]:
        assert client.post("/votes", json={"voter_id": voter["id"], "candidate_id": cand["id"]}).status_code == 201

    s = client.get("/votes/statistics").json()
    assert s["total_votes"] == 3
    assert s["total_voters"] == 4
    assert s["voters_who_voted"] == 3
    assert s["participation_percentage"] == 75.0
    by_id = {c["candidate_id"]: c for c in s["candidates"]}
    assert by_id[c1["id"]]["votes"] == 2 and by_id[c1["id"]]["percentage"] == 66.67
    assert by_id[c2["id"]]["votes"] == 1 and by_id[c2["id"]]["percentage"] == 33.33
    assert by_id[c3["id"]]["votes"] == 0 and by_id[c3["id"]]["percentage"] == 0.0
    assert s["candidates"][0]["candidate_id"] == c1["id"]  # ordenado por votos


# ---------- Autenticacion JWT ----------
def test_jwt_auth(client, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    assert client.get("/voters").status_code == 401
    assert client.get("/voters", headers={"Authorization": "Bearer basura"}).status_code == 401
    assert client.post("/auth/login", json={"username": "admin", "password": "mal"}).status_code == 401

    r = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert client.get("/voters", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.get("/health").status_code == 200  # health siempre publico
