"""Configurações usadas pelos scripts."""
from pathlib import Path

# Os caminhos não dependem de onde o terminal foi aberto.
BASE = Path(__file__).resolve().parents[1]
RAW = BASE / 'data/raw'
PROCESSED = BASE / 'data/processed'
DB_PATH = BASE / 'data/chromadb'
MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
PREFERENCIAS = ('todos', 'geral', 'android', 'mac', 'windows')
