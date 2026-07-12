# AIchat

Prod-style : FastAPI + MongoDB Atlas backend, React (TypeScript) frontend,
OpenAI streaming over SSE, JWT auth.

## Setup (once)

Create `backend/.env` from the example and fill in your values:

```bash
cp backend/.env.example backend/.env
# then edit backend/.env: MONGODB_URI, OPENAI_API_KEY, JWT_SECRET
```

## Run with scripts (dev, hot-reload)

Start this project's own Redis first (its own container on `localhost:6379` — never
another project's), then the app in two terminals:

```bash
# Once per session - this project's Redis (container: chatprod-redis)
./scripts/dev-redis.sh

# Terminal 1 - backend  (http://localhost:8000)
./scripts/dev-backend.sh

# Terminal 2 - frontend (http://localhost:5173)
./scripts/dev-frontend.sh
```

Redis is a separate running process the backend connects to (via `REDIS_URI`), not a
library. `dev-redis.sh` brings up ChatProd's own Redis; if port 6379 is already taken by
a different container, stop that one first (only one process can hold the port). Stop this
one with `docker compose stop redis`.

First run installs deps automatically (`uv sync` / `npm install`). If the frontend
deps are missing, run `npm install` inside `frontend/` once.

## Run with Docker (containers)

One command builds and starts both containers (Mongo stays on Atlas):

```bash
docker compose up --build
```

- App:     http://localhost:5173
- API:     http://localhost:8000
- Stop:    `docker compose down`

## Notes

- API docs (Swagger): http://localhost:8000/docs
- `--build` rebuilds the images after code changes; drop it for a plain restart.
