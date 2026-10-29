"""Ponto de importação do fluxo RAG; implementação separada por etapa."""
from .geracao import Ollama, SEM_EVIDENCIA, responder
from .ingestao import criar_chunks, ler_documentos
from .recuperacao import E5, preparar, indexar, recuperar
