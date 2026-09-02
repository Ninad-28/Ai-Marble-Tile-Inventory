from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 480))

GATEKEEPER_ENABLED = os.getenv("GATEKEEPER_ENABLED", "false").lower() in ("1", "true", "yes")
GATEKEEPER_THRESHOLD = float(os.getenv("GATEKEEPER_THRESHOLD", "0.70"))
GATEKEEPER_CHECKPOINT_PATH = os.getenv(
    "GATEKEEPER_CHECKPOINT_PATH",
    "model_cache/gatekeeper_mobilenetv3_best.pt",
)