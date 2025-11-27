![тупоя](https://coolgifs.neocities.org/gifs/109.gif)

# Bullshido API

Асинхронний бекенд для сервісу генерації AI-відео **Bullshido**.
Побудований на сльозами і кров'ю на Python. Він шарить за авторизацію, керування завданнями через Redis та збереження даних у PostgreSQL.

## Стек

- **Core:** FastAPI
- **Database:** PostgreSQL + SQLModel
- **Migrations:** Alembic
- **Task Queue:** Redis + arq
- **Infrastructure:** Docker & Docker Compose

## Функціонал

- **JWT Авторизація** (Login, Register, Password reset flows).
- **Профіль користувача** (Редагування, видалення з каскадним очищенням даних).
- **Відео-генерація**:
    - Створення задач та відправка їх у чергу Redis.
    - Трекінг статусу (`queued` -> `processing` -> `completed` / `failed`).
    - Ендпоінт для звіту воркера про результат.
- **Галерея та Історія**: Пагінований вивід готових відео.

## Як запустити

### 1. Змінні оточення

- FastAPI
- sqlmodel
- alembic
- passlib
- python-jose