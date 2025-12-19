import os
import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent

sys.path.insert(0, str(project_root))

os.environ["SECRET_KEY"] = "pleasework"
os.environ["WORKER_SECRET_TOKEN"] = "pleasework"
os.environ["ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

os.environ["POSTGRES_USER"] = "pleasework"
os.environ["POSTGRES_PASSWORD"] = "pleasework"
os.environ["POSTGRES_DB"] = "pleasework"
os.environ["POSTGRES_HOST"] = "pleasework"
os.environ["POSTGRES_PORT"] = "5432"

os.environ["REDIS_HOST"] = "pleasework"
os.environ["REDIS_PORT"] = "6379"
os.environ["REDIS_PASSWORD"] = "pleasework"
# ця штука тут треба щоб зімітувати змінні середовища. По іншому не працює(((
