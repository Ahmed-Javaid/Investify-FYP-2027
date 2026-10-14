# Investify POC spike (brief section 3).
#
# Targets are ordered by the pipeline they drive: setup -> data -> features ->
# spike -> test -> app. Everything after `data` runs offline from data/store
# and .cache, so the panel demo never depends on a network at defence time.

.PHONY: help setup data features spike engine test app clean-artifacts

PY := PYTHONPATH=src uv run

help:
	@echo "setup     install the pinned environment (uv sync)"
	@echo "data      pull the news corpora (network; Alpaca needs .env credentials)"
	@echo "features  build both feature matrices from the store + FinBERT cache"
	@echo "spike     run the leakage harness on both corpora -> artifacts/"
	@echo "engine    train, calibrate, attribute -> decision records for both corpora"
	@echo "test      run the full suite, including the leak canary"
	@echo "app       launch the two-tab demo"

setup:
	uv sync

# Network. The FNSPID subset takes hours (see artifacts/phase0_report.md);
# the Alpaca pull takes about a minute and needs ALPACA_API_KEY /
# ALPACA_API_SECRET in .env.
data:
	$(PY) python scripts/phase0_pull_nasdaq_ticker_news.py
	$(PY) python scripts/pull_alpaca_nvda_news.py

# Prices come from yfinance on the first run and from the append-only store
# thereafter; FinBERT scores are cached by content hash, so re-runs are fast.
features:
	$(PY) python scripts/build_phase1_feature_matrix.py
	$(PY) python scripts/build_alpaca_feature_matrix.py

spike:
	$(PY) python -m investify.harness.run_spike
	$(PY) python -m investify.harness.run_spike --corpus alpaca

engine:
	$(PY) python scripts/build_decision_records.py
	$(PY) python scripts/build_decision_records.py --corpus alpaca

test:
	uv run pytest -q

app:
	$(PY) streamlit run app/streamlit_app.py

# Deliberately does NOT delete artifacts/ -- that directory is committed
# evidence, not scratch (see ../AGENTS.md). Removes only derived local state.
clean-artifacts:
	rm -f data/store/feature_matrix.parquet data/store/feature_matrix_alpaca.parquet
