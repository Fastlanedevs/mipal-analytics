DOCKER_IMAGE = "mipal-backend"
.PHONY: install
install:
	uv pip install -r pyproject.toml --all-extras

#create uuid from command line
.PHONY: uuid
uuid:
	hexdump -vn16 -e'4/4 "%08X" 1 "\n"' /dev/urandom

.PHONY: run
run:
	uv run --env-file .env python3 cmd_server/server/main.py

.PHONY: run-worker
run-worker:
	uv run --env-file .env  python3 cmd_server/worker/main.py

.PHONY: run-worker-prod
run-worker-prod:
	uv run --env-file .env.prod  python3 cmd_server/worker/main.py

.PHONY: run-deep-research
run-deep-research:
	uv run --env-file .env python3 cmd_server/deep_research_worker/main.py

.PHONY: container
container:
	docker build -t $(DOCKER_IMAGE) -f docker/Dockerfile .

.PHONY: run-container
run-container:
	docker run  -p 80:80 --env-file .env $(DOCKER_IMAGE)

.PHONY: update-requirements
update-requirements:
	pip-compile pyproject.toml --output-file=requirements.txt

.PHONY: update-requirements-dev
update-requirements-dev:
	pip-compile pyproject.toml --extra=dev --output-file=requirements-dev.txt

.PHONY: proto
proto:
	protoc  --python_out=protobuf app/*/proto/*.proto

.PHONY: run-codex
run-codex:
	uv run --env-file .env python3 cmd_server/code_execution_server/main.py


.PHONY: run-custom
run-custom:
	uv run --env-file .env python3 app/main.py

.PHONY: run-market
run-market:
	uv run --env-file .env python3 app/pal/market_analyser/market_analyser.py

.PHONY: run-docx
run-docx:
	uv run --env-file .env python3 app/pal/rfp/document_generator.py

.PHONY: run-chart-worker
run-chart-worker:
	uv run --env-file .env python3 cmd_server/worker/main.py
