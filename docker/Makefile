ENV_FILE = .env

deploy:
	docker compose --env-file $(ENV_FILE) up -d --build
	docker image prune -f
up:
	docker compose --env-file $(ENV_FILE) up -d

down:
	docker compose --env-file $(ENV_FILE) down

logs:
	docker compose --env-file $(ENV_FILE) logs -f

logs-api:
	docker compose --env-file $(ENV_FILE) logs -f api

restart:
	docker compose --env-file $(ENV_FILE) restart

restart-api:
	docker compose --env-file $(ENV_FILE) restart api

ps:
	docker compose --env-file $(ENV_FILE) ps

clean:
	docker compose --env-file $(ENV_FILE) down -v
