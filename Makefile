.PHONY: install dev check

install:
	.venv/bin/pip install -r requirements.txt

dev:
	.venv/bin/uvicorn app.main:app --reload

check:
	.venv/bin/python -c "import app.main; print('backend import ok')"
