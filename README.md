# API Sistema de Votaciones

API RESTful para gestionar votantes, candidatos y votos, con estadisticas de resultados.

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2 · PostgreSQL · JWT (opcional) · Docker

## Caracteristicas

- CRUD de votantes y candidatos, emision de votos y estadisticas.
- Un votante solo puede votar una vez (validacion en la API **y** restriccion `UNIQUE` en BD).
- Voto, `has_voted` y contador `votes` se actualizan en **una sola transaccion**; el contador se incrementa de forma atomica en SQL y el votante se bloquea (`SELECT ... FOR UPDATE`) para evitar doble voto concurrente.
- Un votante no puede ser candidato y viceversa.
- Extras: autenticacion JWT opcional, paginacion y filtros, tests automatizados, Swagger.

## Ejecucion local

### Opcion A: Docker (recomendada)

```bash
docker compose up --build
```

API en http://localhost:8000 · Swagger en http://localhost:8000/docs

### Opcion B: sin Docker

Requiere PostgreSQL. Crea la BD y el usuario:

```sql
CREATE USER voting WITH PASSWORD 'voting';
CREATE DATABASE voting OWNER voting;
```

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # ajusta DATABASE_URL si hace falta
export DATABASE_URL=postgresql+psycopg2://voting:voting@localhost:5432/voting
uvicorn app.main:app --reload
```

Las tablas se crean automaticamente al iniciar.

### Tests (usan SQLite, no requieren PostgreSQL)

```bash
pip install -r requirements-dev.txt
pytest -v
```

## Variables de entorno

| Variable | Defecto | Descripcion |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg2://voting:voting@localhost:5432/voting` | Conexion a la BD |
| `AUTH_ENABLED` | `false` | `true` protege todos los endpoints con JWT |
| `JWT_SECRET` | (dev) | Secreto de firma. **Cambialo en produccion** |
| `JWT_EXPIRE_MINUTES` | `60` | Vigencia del token |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `admin123` | Credenciales de `/auth/login` |

## Endpoints

| Metodo | Ruta | Descripcion | Codigos |
|---|---|---|---|
| POST | `/voters` | Registrar votante | 201, 409, 422 |
| GET | `/voters` | Listar (`page`, `page_size`, `name`, `has_voted`) | 200 |
| GET | `/voters/{id}` | Detalle | 200, 404 |
| DELETE | `/voters/{id}` | Eliminar | 204, 404, 409 |
| POST | `/candidates` | Registrar candidato | 201, 409, 422 |
| GET | `/candidates` | Listar (`page`, `page_size`, `name`, `party`) | 200 |
| GET | `/candidates/{id}` | Detalle | 200, 404 |
| DELETE | `/candidates/{id}` | Eliminar | 204, 404, 409 |
| POST | `/votes` | Emitir voto | 201, 404, 409, 422 |
| GET | `/votes` | Listar votos (`page`, `page_size`, `candidate_id`) | 200 |
| GET | `/votes/statistics` | Estadisticas | 200 |
| POST | `/auth/login` | Obtener JWT | 200, 401 |

Las listas devuelven el total de registros en el header `X-Total-Count`.

## Decisiones de diseno

- **Voter vs Candidate:** el modelo de candidato no tiene email, por lo que la identidad se compara por **nombre** (sin distinguir mayusculas). Si el nombre ya existe en la otra entidad, responde `409`.
- **Borrados:** no se puede eliminar un votante que ya voto ni un candidato con votos (`409`), para no alterar los resultados.
- **Estadisticas:** los conteos se calculan desde la tabla `votes` (fuente de verdad); los porcentajes se redondean a 2 decimales y son `0` si aun no hay votos.
- **Errores:** `404` no encontrado, `409` conflicto de negocio (duplicados, doble voto), `422` datos invalidos.

## Ejemplos con curl

```bash
# Registrar votantes
curl -X POST localhost:8000/voters -H "Content-Type: application/json" \
  -d '{"name":"Ana Torres","email":"ana@example.com"}'
curl -X POST localhost:8000/voters -H "Content-Type: application/json" \
  -d '{"name":"Luis Mora","email":"luis@example.com"}'

# Registrar candidatos
curl -X POST localhost:8000/candidates -H "Content-Type: application/json" \
  -d '{"name":"Carlos Perez","party":"Partido Azul"}'
curl -X POST localhost:8000/candidates -H "Content-Type: application/json" \
  -d '{"name":"Sofia Rios","party":"Partido Verde"}'

# Emitir votos
curl -X POST localhost:8000/votes -H "Content-Type: application/json" \
  -d '{"voter_id":1,"candidate_id":1}'
curl -X POST localhost:8000/votes -H "Content-Type: application/json" \
  -d '{"voter_id":2,"candidate_id":1}'

# Segundo voto del mismo votante -> 409
curl -i -X POST localhost:8000/votes -H "Content-Type: application/json" \
  -d '{"voter_id":1,"candidate_id":2}'

# Listados, detalle, borrado
curl "localhost:8000/voters?page=1&page_size=10&has_voted=true"
curl localhost:8000/candidates/1
curl -X DELETE localhost:8000/candidates/2

# Estadisticas
curl localhost:8000/votes/statistics
```

Con JWT activo (`AUTH_ENABLED=true`):

```bash
TOKEN=$(curl -s -X POST localhost:8000/auth/login -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl localhost:8000/voters -H "Authorization: Bearer $TOKEN"
```

En Swagger (`/docs`) usa el boton **Authorize** y pega el token.

## Estadisticas generadas

Ejemplo de respuesta de `GET /votes/statistics` (4 votantes, 3 votaron):

```json
{
  "total_votes": 3,
  "total_voters": 4,
  "voters_who_voted": 3,
  "participation_percentage": 75.0,
  "candidates": [
    {"candidate_id": 1, "name": "Carlos Perez", "party": "Partido Azul",  "votes": 2, "percentage": 66.67},
    {"candidate_id": 2, "name": "Sofia Rios",   "party": "Partido Verde", "votes": 1, "percentage": 33.33},
    {"candidate_id": 3, "name": "Mario Lopez",  "party": null,            "votes": 0, "percentage": 0.0}
  ]
}
```

> Captura: ![Estadisticas](docs/estadisticas.png)
