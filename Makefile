PY := .venv/bin/python
PIP := .venv/bin/pip
PYTEST := .venv/bin/pytest

.PHONY: setup traces traces-real traces-deepseek fetch-data test api ui demo

setup:
	python3 -m venv .venv
	$(PIP) install -q -r backend/requirements.txt
	cd frontend && npm install --no-fund --no-audit

traces:
	cd backend && ../$(PY) -m gauntlet.run --all

fetch-data:
	cd backend && ../$(PY) -m gauntlet.fetch_data --auto

traces-real:
	cd backend && ../$(PY) -m gauntlet.run --all --data real

# real-model rows (needs DEEPSEEK_API_KEY; merges into existing results.json)
traces-deepseek:
	cd backend && set -a && . ../.env && set +a && \
		../$(PY) -m gauntlet.run --all --agents deepseek && \
		../$(PY) -m gauntlet.run --all --data real --agents deepseek

test:
	$(PYTEST) backend/tests -q

api:
	cd backend && ../.venv/bin/uvicorn gauntlet.api:app --port 8000

ui:
	cd frontend && npm run dev

demo: traces
	cd frontend && npm run build
	cd backend && ../.venv/bin/uvicorn gauntlet.api:app --port 8000
