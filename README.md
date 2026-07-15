# Farm Accounts API

FastAPI backend for the farm accounts management app.

## Setup

```bash
cd /Users/subashv/dev/Projects/farm/backend
python3 -m venv .venv
source .venv/bin/activate
make install
cp .env.example .env
```

Set the Postgres connection fields in `.env`:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-password
POSTGRES_HOST=db.ifezrdgcotfqqwdjogvy.supabase.co
POSTGRES_PORT=5432
POSTGRES_DBNAME=postgres
POSTGRES_SSLMODE=require
```

## Database

Apply migrations:

```bash
make db-upgrade
```

Create a new migration after model changes:

```bash
make db-revision message="describe change"
```

## Development

Start the API:

```bash
make dev
```

Run a lightweight import check:

```bash
make check
```

## API

Open the API docs at `http://localhost:8000/docs`.
