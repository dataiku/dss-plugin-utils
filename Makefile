test-one:
	@echo "[START] Running unit tests on ${f}..."
	@( \
		rm -rf env; \
		python3 -m venv env/; \
		source env/bin/activate; \
		pip3 install --upgrade pip; \
		pip install --no-cache-dir -r tests/${f}/requirements.txt; \
		pip install --no-cache-dir -r utils/${f}/requirements.txt; \
		export PYTHONPATH="$(PYTHONPATH):$(PWD)/utils"; \
		pytest -o junit_family=xunit2 --junitxml=unit.xml tests/${f} || true; \
		deactivate; \
	)
	@echo "[SUCCESS] Running unit tests: Done!"


test-all: ./utils/*
	@echo "[START] Running unit tests on all..."
	for file in $^ ; do \
		python3 -m venv env/; \
		source env/bin/activate; \
		pip3 install --upgrade pip; \
		pip install --no-cache-dir -r tests/$${file}/requirements.txt; \
		pip install --no-cache-dir -r utils/$${file}/requirements.txt; \
		export PYTHONPATH="$(PYTHONPATH):$(PWD)/utils"; \
		pytest -o junit_family=xunit2 --junitxml=unit.xml tests/${file} || true; \
		deactivate; \
	done
	@echo "[SUCCESS] Running unit tests: Done!"