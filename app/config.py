import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / 'storage'
INDEX_PATH = STORAGE_DIR / 'esg.index'
CHUNKS_PATH = STORAGE_DIR / 'chunks.json'

GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'intfloat/multilingual-e5-base')
SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.45'))
TOP_K = int(os.getenv('TOP_K', '5'))
MAX_HISTORY_TURNS = int(os.getenv('MAX_HISTORY_TURNS', '5'))
