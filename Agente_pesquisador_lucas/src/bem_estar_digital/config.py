"""Configuração reproduzível da base; Llama não participa dos embeddings."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
MODELO_E5 = "intfloat/multilingual-e5-small"
REVISAO_E5 = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
TAMANHO = 350
SOBREPOSICAO = 50
TOP_K = 5
CONFIG = {"versao": 2, "modelo_embeddings": MODELO_E5, "revisao_embeddings": REVISAO_E5, "tokens": TAMANHO,
          "sobreposicao": SOBREPOSICAO, "prefixos": "passage/query", "limpeza": 2}


def caminhos(base=RAIZ / "data"):
    base = Path(base)
    return {"base": base, "raw": base / "raw", "sources": base / "sources.csv",
            "processed": base / "processed", "chroma": base / "chroma",
            "manifest": base / "processed/manifest.json"}
