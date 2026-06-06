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

MongoDB should be running locally at `mongodb://localhost:27017`, or update `MONGODB_URI` in `.env`.

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
