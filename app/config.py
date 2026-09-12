import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / 'storage'
INDEX_PATH = STORAGE_DIR / 'esg.index'
CHUNKS_PATH = STORAGE_DIR / 'chunks.json'
PDF_DIR = BASE_DIR / 'data' / 'pdfs'
MARKDOWN_DIR = BASE_DIR / 'data' / 'markdown'

APP_NAME = os.getenv('APP_NAME', 'Verdia ESG Assistant')
APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '').strip()
GROQ_MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b').strip()
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'intfloat/multilingual-e5-base').strip()
SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.45'))
TOP_K = int(os.getenv('TOP_K', '5'))
MAX_HISTORY_TURNS = int(os.getenv('MAX_HISTORY_TURNS', '5'))
RAG_ENABLED = os.getenv('RAG_ENABLED', 'true').strip().lower() in {'1', 'true', 'yes', 'on'}
ALLOWED_ORIGINS = [item.strip() for item in os.getenv('ALLOWED_ORIGINS', '*').split(',') if item.strip()]
