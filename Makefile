.PHONY: install dev check db-upgrade db-revision

install:
	.venv/bin/pip install -r requirements.txt

dev:
	.venv/bin/uvicorn app.main:app --reload

check:
	.venv/bin/python -c "import app.main; print('backend import ok')"

db-upgrade:
	.venv/bin/alembic upgrade head

db-revision:
	.venv/bin/alembic revision --autogenerate -m "$(message)"
