PY := .venv/bin/python
PIP := .venv/bin/pip
PYTEST := .venv/bin/pytest

.PHONY: setup traces traces-real traces-deepseek battery battery-personas fetch-data test api ui demo

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

# intelligent test-case batteries: discrimination + adversarial (deterministic)
battery:
	cd backend && ../$(PY) -m gauntlet.generate --mode discrimination --seed 0
	cd backend && ../$(PY) -m gauntlet.generate --mode adversarial --target rules --seed 0
	cd backend && ../$(PY) -m gauntlet.generate --mode adversarial --target llm --seed 0

# real DeepSeek persona rows: battery comparison + synthetic leaderboard
# (needs DEEPSEEK_API_KEY; retires the generic deepseek row in favour of the personas)
battery-personas:
	cd backend && set -a && . ../.env && set +a && \
		../$(PY) -m gauntlet.precompute --mode discrimination && \
		../$(PY) -m gauntlet.precompute --mode adversarial_rules && \
		../$(PY) -m gauntlet.precompute --mode adversarial_llm && \
		rm -f ../traces/results.json ../traces/S?_deepseek.json && \
		../$(PY) -m gauntlet.run --all && \
		../$(PY) -m gauntlet.run --all --agents ds-cautious,ds-balanced,ds-aggressive

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
