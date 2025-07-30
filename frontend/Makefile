DOCKER_IMAGE = "mipal-ui"
.PHONY: container
container:
	docker build -t $(DOCKER_IMAGE) -f docker/Dockerfile .

.PHONY: run-container
run-container:
	docker run  -p 3000:3000 --env-file .env $(DOCKER_IMAGE)