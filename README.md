# CineReserve

Repository: https://github.com/heribertomonteiro/CineReserve.git

API REST para reserva e emissao de ingressos do cinema "Cinepolis Natal".

Stack principal:
- Python 3.13
- Django + Django REST Framework
- JWT (Simple JWT)
- PostgreSQL
- Redis (cache e lock distribuido)
- Celery + Celery Beat (tarefas assincronas)
- Poetry
- Docker + Docker Compose
- Swagger (drf-spectacular)
- GitHub Actions (CI/CD)

## 1. Visao Geral da Solucao

Este projeto implementa os casos de uso principais de uma bilheteria:
- Cadastro e login com JWT.
- Lista de filmes.
- Lista de sessoes por filme.
- Mapa de assentos com status `available`, `reserved` e `purchased`.
- Lock temporario de assento por 10 minutos com Redis.
- Checkout que transforma reserva temporaria em ticket definitivo no banco.
- Portal "Meus Ingressos" com filtros `active` e `history`.

Tambem inclui:
- Cache para endpoints de leitura de alta demanda.
- Rate limit para reduzir abuso.
- Task assincrona para e-mail de confirmacao de ticket.
- Pipeline CI/CD basico com testes automatizados.

## 2. Arquitetura (alto nivel)

Servicos no Docker Compose:
- `web`: API Django.
- `db`: PostgreSQL.
- `redis`: cache, lock e broker/backend do Celery.
- `celery_worker`: executa tarefas assincronas.
- `celery_beat`: agenda tarefas periodicas via scheduler em banco (`django-celery-beat`).

Fluxo resumido de reserva:
1. Usuario faz lock do assento (`cache.add`) por 600s.
2. Outro usuario nao consegue reservar o mesmo assento enquanto lock existir.
3. No checkout, a API valida o owner do lock.
4. Ticket e criado em transacao atomica.
5. Lock e removido.
6. Apos commit, task Celery envia e-mail de confirmacao.

## 3. Requisitos

Obrigatorio:
- Docker Desktop (Windows/macOS) ou Docker Engine + Compose (Linux).

Opcional:
- `curl` ou Postman para testar endpoints.

Nao e necessario instalar Python localmente para rodar o projeto.

## 4. Setup Plug-and-Play (primeira execucao)

### 4.1 Clonar e entrar na pasta

```bash
git clone [https://github.com/heribertomonteiro/CineReserve.git]
cd CineReserve
```

### 4.2 Criar o arquivo .env

Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

Linux/macOS (bash):

```bash
cp .env.example .env
```

### 4.3 Gerar `DJANGO_SECRET_KEY`

(**ESSE PASSO É OPCIONAL, APENAS PARA GERAR UMA SECRET KEY FORTE**)
Windows (PowerShell):

```powershell
docker compose run --rm web python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Linux/macOS (bash):

```bash
docker compose run --rm web python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

**Cole o valor gerado no `.env` em `DJANGO_SECRET_KEY`.**

### 4.4 Subir stack completa

```bash
docker compose up -d --build
```

### 4.5 Validar status dos servicos

```bash
docker compose ps
```

Esperado:
- `db` e `redis` com status healthy.
- `web`, `celery_worker` e `celery_beat` iniciados.

### 4.6 Criar superusuario (admin)

```bash
docker compose exec web python manage.py createsuperuser
```

## 5. Variaveis de Ambiente

Exemplo de `.env` para desenvolvimento:

```dotenv
DJANGO_SECRET_KEY=REPLACE_ME
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

POSTGRES_DB=cinereserve
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres456

DATABASE_URL=postgresql://postgres:postgres456@db:5432/cinereserve

REDIS_URL=redis://redis:6379/0

CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/1

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@cinereserve.local
```

Notas:
- `REDIS_URL` (db 0): cache e locks.
- `CELERY_*` (db 1): filas/resultados Celery.
- Em dev, e-mail vai para log do worker (`console backend`).

## 6. URLs Uteis

- Admin: http://localhost:8000/admin/
- Swagger: http://localhost:8000/api/docs/

## 7. Operacao no Dia a Dia

Subir:

```bash
docker compose up -d --build
```

Parar:

```bash
docker compose down
```

Parar e remover volumes (reset total local):

```bash
docker compose down -v
```

Logs:

```bash
docker compose logs -f --tail=200 web
docker compose logs -f --tail=200 celery_worker
docker compose logs -f --tail=200 celery_beat
```

Executar comando Django:

```bash
docker compose exec web python manage.py <comando>
```

## 8. Testes

Check geral:

```bash
docker compose exec -T web python manage.py check
```

Suite completa:

```bash
docker compose exec -T web python manage.py test -v 2
```

Por app:

```bash
docker compose exec -T web python manage.py test cinema -v 2
docker compose exec -T web python manage.py test movies -v 2
docker compose exec -T web python manage.py test users -v 2
```

## 9. Como o Assento e Protegido (Redis Lock)

- Chave de lock: `lock:session:{session_id}:seat:{seat_id}`.
- Aquisição: `cache.add(..., timeout=600)`.
- Resultado:
  - lock adquirido: assento reservado.
  - lock existente: conflito de reserva.
- Expiracao automatica: Redis TTL remove lock sem job extra.

## 10. Como o E-mail Assincrono Funciona (Celery)

1. Checkout cria `Ticket` em transacao atomica.
2. `transaction.on_commit(...)` dispara `send_ticket_confirmation_email.delay(ticket_id)`.
3. Worker Celery processa a task.
4. Em dev (`console backend`), o conteudo do e-mail aparece no log do `celery_worker`.

Exemplo de verificacao:

```bash
docker compose logs --tail=200 celery_worker
```

## 11. CI/CD

Pipeline em `.github/workflows/ci-cd.yml`:

CI:
- sobe Postgres e Redis como services;
- instala dependencias com Poetry;
- executa `check`, valida migrations e roda testes.

CD (push em `main`):
- build e push da imagem para GHCR.

