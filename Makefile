PY := .venv/bin/python
PIP := .venv/bin/pip
PYTEST := .venv/bin/pytest

.PHONY: setup traces test api ui demo

setup:
	python3 -m venv .venv
	$(PIP) install -q -r backend/requirements.txt
	cd frontend && npm install --no-fund --no-audit

traces:
	cd backend && ../$(PY) -m gauntlet.run --all

test:
	$(PYTEST) backend/tests -q

api:
	cd backend && ../.venv/bin/uvicorn gauntlet.api:app --port 8000

ui:
	cd frontend && npm run dev

demo: traces
	cd frontend && npm run build
	cd backend && ../.venv/bin/uvicorn gauntlet.api:app --port 8000
