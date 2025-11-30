ENV_FILE = ../.env

up:
	sudo docker compose --env-file $(ENV_FILE) up -d --build

down:
	sudo docker compose --env-file $(ENV_FILE) down

logs:
	sudo docker compose --env-file $(ENV_FILE) logs -f