import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("MODEL", "gpt-4o")
EMBED_MODEL = "text-embedding-3-small"

ORDERS_FILE = "data/orders.json"
REFUNDS_FILE = "data/refunds.json"
ESCALATIONS_FILE = "data/escalations.json"
POLICY_DIR = "policies"
CHROMA_DIR = "data/chroma"
