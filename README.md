# CineReserve

API REST para reserva/compra de ingressos (projeto de vaga). Stack atual: Django + Django REST Framework + JWT + Postgres + Redis + Docker + Poetry.

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