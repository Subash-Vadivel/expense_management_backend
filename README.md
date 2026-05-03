# Farm Accounts API

FastAPI backend for the farm accounts management app.

## Setup

```bash
cd /Users/subashv/dev/Projects/farm/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

MongoDB should be running locally at `mongodb://localhost:27017`, or update `MONGODB_URI` in `.env`.

## API

Open the API docs at `http://localhost:8000/docs`.
