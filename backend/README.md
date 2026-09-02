<div align="center">

# Realtime Chat Backend

**An asynchronous FastAPI backend for private messaging, social connections, and real-time WebSocket delivery.**

[![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)

[Features](#features) • [Architecture](#architecture) • [Getting started](#getting-started) • [API overview](#api-overview) • [Testing](#testing)

</div>

## Overview

This project is the backend of a real-time chat application. It exposes a versioned REST API for authentication, user discovery, profiles, friendships, private conversations, and message history. A WebSocket endpoint delivers messages in real time while Redis Pub/Sub keeps delivery working across multiple backend processes.

The codebase is organized around clear application boundaries: API routes handle transport concerns, services contain business rules, repositories handle persistence, and adapters isolate infrastructure such as object storage.

## Features

- **Authentication and session security**
  - User registration and case-insensitive username handling
  - Argon2 password hashing
  - Short-lived JWT access tokens and refresh tokens
  - Refresh-token rotation with reuse detection and token-family revocation
  - Logout with Redis-backed access-token denylisting
- **Real-time private messaging**
  - Private conversation creation with canonical participant ordering
  - Participant-only message access and message sending
  - WebSocket delivery to all connected participants
  - Redis Pub/Sub fan-out for multi-process deployments
  - Connection keepalive and cleanup of disconnected sockets
- **Social features**
  - User search
  - Friend requests with accept/reject flows
  - Accepted-friend lists
- **Profiles and media**
  - Biography updates
  - JPEG, PNG, and WebP profile-picture uploads
  - S3-compatible storage through MinIO and presigned URLs
- **Abuse protection and maintainability**
  - Redis-backed rate limiting for authentication and WebSocket traffic
  - Async PostgreSQL access with SQLAlchemy and `asyncpg`
  - Alembic migrations
  - Unit and integration test suites with dependency overrides and fakes
  - Docker Compose development environment

## Architecture

```mermaid
flowchart LR
    Client[Web or mobile client]
    API[FastAPI REST API + WebSocket]
    Services[Application services]
    Repositories[Repositories + Unit of Work]
    Postgres[(PostgreSQL)]
    Redis[(Redis)]
    MinIO[(MinIO / S3 storage)]

    Client --> API
    API --> Services
    Services --> Repositories
    Repositories --> Postgres
    API --> Redis
    Services --> MinIO
    Redis -. token store, rate limits, Pub/Sub .- API
```

### Application layers

| Layer | Responsibility |
| --- | --- |
| `app/api` | REST endpoints, dependency injection, authentication boundaries, and rate-limit dependencies |
| `app/services` | Business rules for authentication, conversations, messages, friendships, profiles, and users |
| `app/repositories` | Database queries and persistence operations behind repository protocols |
| `app/models` | PostgreSQL domain models and constraints |
| `app/schemas` | Pydantic request and response contracts |
| `app/websocket` | WebSocket authentication, connection lifecycle, validation, and message fan-out |
| `app/adapters` | Infrastructure integrations, including MinIO file storage |
| `alembic` | Versioned database schema migrations |

## Tech stack

- **Python 3.12+**
- **FastAPI** and **Uvicorn** for the HTTP and WebSocket application
- **Pydantic Settings** for environment-based configuration
- **SQLAlchemy async** with **asyncpg** for PostgreSQL access
- **Alembic** for schema migrations
- **Redis** for token state, rate limiting, and WebSocket Pub/Sub
- **MinIO** through the S3-compatible `boto3` API for profile pictures
- **uv** for dependency and virtual-environment management
- **pytest**, **pytest-asyncio**, and **ruff** for development quality checks

## Getting started

### Prerequisites

Install the following tools:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Python 3.12 or newer](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/)
- [Git](https://git-scm.com/downloads)

> [!IMPORTANT]
> The application needs PostgreSQL, Redis, and MinIO. Docker Compose is the recommended way to run these services locally.

### Option 1: Run the full stack with Docker Compose

From the **repository root** (recommended — runs frontend + backend together):

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

Or from **this directory** (backend only):

```bash
cp .env.example .env
docker compose up --build
```

The backend starts on `http://localhost:8000`. On startup, the container applies the latest Alembic migrations before launching Uvicorn.

To stop the stack:

```bash
docker compose down
```

Available local services (from root compose):

| Service | Address | Purpose |
| --- | --- | --- |
| Frontend | `http://localhost:4200` | Angular SPA via nginx |
| Backend | `http://localhost:8000` | REST API and WebSocket server |
| PostgreSQL | `localhost:5432` | Application database |
| Redis | `localhost:6379` | Token state, rate limiting, and Pub/Sub |
| MinIO API | `http://localhost:9000` | Profile-picture object storage |
| MinIO Console | `http://localhost:9001` | Local storage administration |

### Option 2: Run the API locally

Start the infrastructure services first:

```bash
cp .env.example .env
docker compose up -d db redis minio
```

Install the Python dependencies, apply migrations, and start the development server:

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

> [!TIP]
> FastAPI provides interactive documentation at [`/docs`](http://localhost:8000/docs) and ReDoc at [`/redoc`](http://localhost:8000/redoc).

### Configuration

Copy `.env.example` to `.env` and update values for your environment. The most important settings are:

| Variable | Description | Example |
| --- | --- | --- |
| `SQLALCHEMY_DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://chat:chat@localhost:5432/chat` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `MINIO_ENDPOINT` | Internal MinIO endpoint used by the API | `localhost:9000` |
| `MINIO_PUBLIC_ENDPOINT` | Optional endpoint used in generated browser-facing URLs | `localhost:9000` |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | MinIO credentials | `minioadmin` / `minioadmin123` |
| `MINIO_BUCKET_NAME` | Bucket for uploaded profile pictures | `realtime-chat` |
| `MINIO_USE_SSL` | Whether MinIO connections use HTTPS | `false` |
| `MAX_UPLOAD_SIZE` | Maximum upload size in bytes | `10485760` |
| `SECRET_KEY` | Secret used to sign JWTs | A long random secret |
| `ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh-token lifetime | `7` |
| `BACKEND_CORS_ORIGINS` | JSON array of allowed frontend origins | `["http://localhost:4200", "http://localhost"]` |

> [!WARNING]
> Never commit `.env` or reuse the example credentials outside local development. Use a long, randomly generated `SECRET_KEY` in every deployed environment.

## API overview

All HTTP routes are prefixed with `/api/v1`. Protected endpoints use an access token in the `Authorization: Bearer <token>` header.

### Health and authentication

| Method | Endpoint | Description | Auth |
| --- | --- | --- | --- |
| `GET` | `/health` | Health response | — |
| `POST` | `/api/v1/auth/register` | Create a user and profile | — |
| `POST` | `/api/v1/auth/login` | Issue access and refresh tokens | — |
| `POST` | `/api/v1/auth/refresh` | Rotate a refresh token | — |
| `POST` | `/api/v1/auth/logout` | Revoke the current access and refresh tokens | Bearer |
| `GET` | `/api/v1/auth/me` | Return the authenticated user | Bearer |

### Users, profiles, friendships, and conversations

| Method | Endpoint | Description | Auth |
| --- | --- | --- | --- |
| `GET` | `/api/v1/users/search?q=<query>` | Search users by username, excluding the current user | Bearer |
| `GET` | `/api/v1/profile/me` | Get the current user’s profile | Bearer |
| `PATCH` | `/api/v1/profile/me` | Update the biography | Bearer |
| `POST` | `/api/v1/profile/me/picture` | Upload a profile picture | Bearer |
| `POST` | `/api/v1/friends/requests/{user_id}` | Send a friend request | Bearer |
| `GET` | `/api/v1/friends/requests` | List pending incoming requests | Bearer |
| `POST` | `/api/v1/friends/requests/{friendship_id}/respond?accept=true` | Accept or reject a request | Bearer |
| `GET` | `/api/v1/friends` | List accepted friends | Bearer |
| `POST` | `/api/v1/conversations` | Get or create a private conversation | Bearer |
| `GET` | `/api/v1/conversations` | List the current user’s conversations | Bearer |
| `POST` | `/api/v1/conversations/{conversation_id}/messages` | Send a message over HTTP | Bearer |
| `GET` | `/api/v1/conversations/{conversation_id}/messages` | Read message history | Bearer |

The message-history endpoint supports `before_id` for cursor-style pagination and `limit` for page size.

### Quick API example

Register a user:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "alice",
    "password": "strong-password-123",
    "first_name": "Alice",
    "last_name": "Smith"
  }'
```

Log in using the OAuth2 form fields expected by the API:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=alice&password=strong-password-123'
```

Use the returned access token with protected endpoints:

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

## WebSocket API

Connect to:

```text
ws://localhost:8000/api/v1/ws?token=<ACCESS_TOKEN>
```

Send a message as JSON:

```json
{
  "conversation_id": 1,
  "body": "Hello in real time!"
}
```

A successfully delivered message is sent to each connected participant in this envelope:

```json
{
  "type": "message",
  "data": {
    "message_id": 1,
    "conversation_id": 1,
    "sender_id": 1,
    "body": "Hello in real time!",
    "created_at": "2026-08-21T12:00:00Z",
    "edited_at": null,
    "deleted_at": null
  }
}
```

The server also sends `ping` frames at the application level when a connection is idle. Clients should reply with:

```json
{"type": "pong"}
```

Validation and authorization failures are returned without closing a healthy connection:

```json
{
  "type": "error",
  "detail": "Not a participant"
}
```

## Security model

- Passwords are stored as Argon2 hashes; plaintext passwords are never returned by the API.
- Access and refresh tokens are separate JWT types.
- Refresh tokens are rotated atomically in Redis. Replaying a rotated token revokes its entire token family.
- Logout deny-lists the presented access token until it expires and revokes the refresh-token chain.
- Message reads and writes require conversation membership.
- Authentication and WebSocket traffic are rate-limited through Redis.

Current application-level limits include three registration attempts per hour and five login attempts per minute per client IP, plus WebSocket connection and message limits.

## Database migrations

Create and apply migrations with Alembic from the `backend` directory:

```bash
# Apply all migrations
uv run alembic upgrade head

# Generate a migration after changing the models
uv run alembic revision --autogenerate -m "describe the schema change"

# Roll back one migration
uv run alembic downgrade -1
```

## Testing

The integration test suite uses the PostgreSQL test service exposed on port `5433`. Start the required test infrastructure, then run the test suite:

```bash
docker compose up -d test_db minio
uv run pytest
```

Run focused checks when iterating:

```bash
uv run pytest tests/unit
uv run pytest tests/integration
uv run ruff check .
```

## Project structure

```text
backend/
├── app/
│   ├── adapters/       # MinIO/S3-compatible file storage
│   ├── api/v1/         # Versioned REST endpoints
│   ├── core/           # Configuration, security, and exceptions
│   ├── db/             # Async SQLAlchemy and Redis clients
│   ├── models/         # Database entities
│   ├── repositories/   # Persistence abstractions and queries
│   ├── schemas/        # Pydantic request/response models
│   ├── services/       # Application and domain logic
│   └── websocket/      # WebSocket authentication and connection manager
├── alembic/             # Database migration history
├── tests/
│   ├── integration/    # API and WebSocket behavior tests
│   └── unit/           # Service and infrastructure unit tests
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```
