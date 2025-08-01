DOCKER_IMAGE = "mipal-backend"

.PHONY: run
run:
	uv run --env-file .env python3 cmd_server/server/main.py

.PHONY: run-worker
run-worker:
	uv run --env-file .env  python3 cmd_server/worker/main.py

.PHONY: container
container:
	docker build -t $(DOCKER_IMAGE) -f docker/Dockerfile .

.PHONY: run-container
run-container:
	docker run  -p 80:80 --env-file .env $(DOCKER_IMAGE)



.PHONY: run-codex
run-codex:
	uv run --env-file .env python3 cmd_server/code_execution_server/main.py


