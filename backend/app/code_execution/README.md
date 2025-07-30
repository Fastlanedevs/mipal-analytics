# Code Execution Module

This module is responsible for handling the secure and isolated execution of user-submitted Python code.

## Overview

The primary goal is to accept Python code snippets via an API, execute them within sandboxed Docker containers, manage a pool of these sandboxes for efficiency, and return the execution results (stdout, stderr, exit code, output files).

## Architecture

The module follows a layered architecture:

-   **`api/`**: Defines the FastAPI web endpoints, request/response Data Transfer Objects (DTOs), dependency injection setup, and request handlers.
    -   `routes.py`: Defines the API routes (e.g., `/execute/async`, `/execute/sync`, `/execute/{id}/status`).
    -   `handlers.py`: Contains the logic triggered by API requests, orchestrating calls to the service layer.
    -   `dto.py`: Defines Pydantic models for API request bodies and responses.
    -   `dependencies.py`: Sets up dependency injection for handlers.
-   **`service/`**: Contains the core business logic and orchestration.
    -   `execution_service.py`: Manages the overall execution lifecycle (queueing, assigning sandboxes, storing results).
    -   `sandbox_service.py`: Manages the pool of Docker sandboxes (creation, scaling, health checks, allocation).
    -   `queue_service.py`: Handles the queuing of execution requests using Redis.
-   **`repository/`**: Responsible for data persistence and retrieval.
    -   `execution_repository.py`: Interface and implementation for storing/retrieving `CodeExecution` data (likely in a SQL database).
    -   `sandbox_repository.py`: Interface and implementation for storing/retrieving `DockerSandbox` state and pool configuration.
    -   `sql_schema/`: Defines SQLAlchemy models for database tables.
-   **`adapter/`**: Contains adapters for external systems, primarily Docker.
    -   `docker_adapter.py`: Provides an abstraction layer for interacting with the Docker API (creating containers, executing commands, managing lifecycle).
-   **`entity/`**: Defines the core domain entities and value objects.
    -   `code_execution_entity.py`: Represents a single code execution request.
    -   `docker_sandbox_entity.py`: Represents a single Docker sandbox container.
    -   `value_objects.py`: Defines immutable objects like statuses (`ExecutionStatus`, `SandboxStatus`), results (`ExecutionResult`), etc.
    -   `aggregates.py`: Defines aggregate roots like `SandboxPool` for managing collections of entities.

## Key Technologies

-   **FastAPI**: For building the asynchronous API.
-   **Docker**: For creating isolated code execution environments (sandboxes).
-   **SQLAlchemy**: For interacting with the relational database (e.g., PostgreSQL) via repositories.
-   **Redis**: For implementing the execution queue and potentially caching results/status.
-   **Pydantic**: For data validation and defining entities/DTOs.

## Workflow

1.  A client sends a request to an API endpoint in `api/routes.py`.
2.  The corresponding `api/handlers.py` method receives the request.
3.  The handler calls the `service/execution_service.py` to submit the execution.
4.  The `execution_service` creates an execution record via `repository/execution_repository.py` and queues it using `service/queue_service.py`.
5.  A background worker (or the service itself) dequeues the request and asks `service/sandbox_service.py` for an available sandbox.
6.  The `sandbox_service` manages the pool (using `repository/sandbox_repository.py` for state and `adapter/docker_adapter.py` for container actions) and provides a sandbox ID.
7.  The `execution_service` instructs the `sandbox_service` to execute the code in the assigned sandbox.
8.  The `sandbox_service` uses the `docker_adapter` to run the code inside the container.
9.  Results are passed back through the services.
10. The `execution_service` updates the execution record in the repository with the results or errors.
11. The `sandbox_service` cleans and releases the sandbox back to the pool.
12. The client can poll the API (`/execute/{id}/status` or `/execute/{id}/result`) to retrieve the outcome. 