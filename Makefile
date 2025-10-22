.PHONY: help build run stop logs clean test deploy

# Docker image settings
IMAGE_NAME := chatter
IMAGE_TAG := latest
REGISTRY := 192.168.2.1:5000/kevsrobots

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker image
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

build-no-cache: ## Build Docker image without cache
	docker build --no-cache -t $(IMAGE_NAME):$(IMAGE_TAG) .

run: ## Run container with docker-compose
	docker-compose up -d

run-logs: ## Run container with logs
	docker-compose up

stop: ## Stop all containers
	docker-compose down

restart: ## Restart containers
	docker-compose restart

logs: ## Show container logs
	docker-compose logs -f app

logs-all: ## Show all container logs
	docker-compose logs -f

shell: ## Open shell in app container
	docker-compose exec app /bin/bash

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U chatter_user -d kevsrobots_cms

clean: ## Stop containers and remove volumes
	docker-compose down -v

ps: ## Show container status
	docker-compose ps

test: ## Run tests in container
	docker-compose exec app pytest tests/ -v

# Production deployment commands
tag-prod: ## Tag image for production registry
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(REGISTRY)/$(IMAGE_NAME):$$(date +%Y%m%d-%H%M%S)

push-prod: tag-prod ## Push image to production registry
	docker push $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push $(REGISTRY)/$(IMAGE_NAME):$$(date +%Y%m%d-%H%M%S)

deploy-prod: build tag-prod push-prod ## Build, tag and push to production
	@echo "Image pushed to $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)"
	@echo "Deploy on server with: docker pull $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)"

# Development commands
dev: ## Start in development mode
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

backup-db: ## Backup database
	docker-compose exec postgres pg_dump -U chatter_user kevsrobots_cms > backup-$$(date +%Y%m%d-%H%M%S).sql

restore-db: ## Restore database (usage: make restore-db FILE=backup.sql)
	docker-compose exec -T postgres psql -U chatter_user kevsrobots_cms < $(FILE)

health: ## Check application health
	curl -f http://localhost:8000/health || echo "Health check failed"

api-docs: ## Open API documentation
	open http://localhost:8000/docs
