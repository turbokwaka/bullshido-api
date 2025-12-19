ENV_FILE = .env

up:
	sudo docker compose --env-file $(ENV_FILE) up -d

down:
	sudo docker compose --env-file $(ENV_FILE) down

logs:
	sudo docker compose --env-file $(ENV_FILE) logs -f

logs-api:
	sudo docker compose --env-file $(ENV_FILE) logs -f api

restart:
	sudo docker compose --env-file $(ENV_FILE) restart

restart-api:
	sudo docker compose --env-file $(ENV_FILE) restart api

ps:
	sudo docker compose --env-file $(ENV_FILE) ps

clean:
	sudo docker compose --env-file $(ENV_FILE) down -v
