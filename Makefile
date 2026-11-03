.PHONY: install test app check

install:
	python -m pip install -r requirements.txt

test:
	python -m pytest -q

app:
	python -m streamlit run app/Home.py

check:
	python -m json.tool questions/bank.json >/dev/null
	python -m json.tool RiskMatch_pipeline.ipynb >/dev/null
	python -m pytest -q

