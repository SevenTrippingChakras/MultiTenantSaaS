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

Two terminals:

```bash
# Terminal 1 - backend  (http://localhost:8000)
./scripts/dev-backend.sh

# Terminal 2 - frontend (http://localhost:5173)
./scripts/dev-frontend.sh
```

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
