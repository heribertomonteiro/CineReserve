# CineReserve

API REST para reserva/compra de ingressos (projeto de vaga). Stack atual: Django + Django REST Framework + JWT + Postgres + Redis + Docker + Poetry.

> Observação de operação: criação/edição/remoção de **Filmes**, **Salas (Rooms)** e **Sessões** é feita via **Django Admin** (`/admin/`).

## Pré-requisitos

- Docker Desktop (Windows) com Docker Compose
- Docker Engine (Linux) / Docker Desktop (macOS) com Docker Compose

## Configuração (primeira vez)

1) Crie seu arquivo `.env` a partir do exemplo:

Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

Linux/macOS (bash):

```bash
cp .env.example .env
```

2) Gere uma `DJANGO_SECRET_KEY` forte e cole no `.env`:

Windows (PowerShell):

```powershell
docker compose run --rm web python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Linux/macOS (bash):

```bash
docker compose run --rm web python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

3) Suba os containers:

Windows (PowerShell):

```powershell
docker compose up -d --build
```

Linux/macOS (bash):

```bash
docker compose up -d --build
```

4) Rode as migrações e crie um superusuário:

Windows (PowerShell):

```powershell
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Linux/macOS (bash):

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

## URLs úteis

- Admin: http://localhost:8000/admin/
- API base: http://localhost:8000/api/
- JWT login: http://localhost:8000/api/auth/login/
- JWT refresh: http://localhost:8000/api/auth/refresh/
- Swagger (se habilitado): http://localhost:8000/api/docs/
- OpenAPI schema (se habilitado): http://localhost:8000/api/schema/

## Endpoints principais

Auth
- `POST /api/auth/register/` - cadastro de usuário
- `POST /api/auth/login/` - obter `access` e `refresh`
- `POST /api/auth/refresh/` - renovar token `access`

Movies
- `GET /api/movies/` - listar filmes (paginado)
- `GET /api/movies/{id}/` - detalhe do filme
- Operações de criação/edição/remoção são feitas via Django Admin

Sessions / Tickets
- `GET /api/sessions/` - listar sessões (paginado)
- `GET /api/movies/{movie_id}/sessions/` - sessões por filme (cacheado)
- `GET /api/sessions/{session_id}/seats/` - mapa de assentos (cacheado)
- `POST /api/sessions/{session_id}/seats/{seat_id}/lock/` - reservar assento por 10 min
- `DELETE /api/sessions/{session_id}/seats/{seat_id}/lock/` - liberar reserva
- `POST /api/tickets/` - checkout (gera ingresso)
- `GET /api/me/tickets/?scope=active|history` - ingressos do usuário (paginado)

Admin operations
- `Movie`, `Room` e `Session`: CRUD exclusivo via Django Admin

## Executar testes

Windows (PowerShell):

```powershell
docker compose exec -T web python manage.py check
docker compose exec -T web python manage.py test -v 2
```

Linux/macOS (bash):

```bash
docker compose exec -T web python manage.py check
docker compose exec -T web python manage.py test -v 2
```

Testes por app:

```bash
docker compose exec -T web python manage.py test cinema -v 2
docker compose exec -T web python manage.py test movies -v 2
docker compose exec -T web python manage.py test users -v 2
```

## Sanity check de documentação

Verifique se os endpoints de documentação sobem com status `200`:

```powershell
Invoke-WebRequest http://localhost:8000/api/schema/ -UseBasicParsing
Invoke-WebRequest http://localhost:8000/api/docs/ -UseBasicParsing
```

## Logs

Windows (PowerShell):

```powershell
# tudo
docker compose logs -f

# só o Django
docker compose logs -f --tail=200 web
```

Linux/macOS (bash):

```bash
# tudo
docker compose logs -f

# só o Django
docker compose logs -f --tail=200 web
```