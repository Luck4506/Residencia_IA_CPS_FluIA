import chromadb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "data" / "base_conhecimento"

cliente = chromadb.PersistentClient(
    path=str(DB_DIR)
)

colecao = cliente.get_collection(
    name="bem_estar_digital"
)

# Recupera os registros armazenados
dados = colecao.get(
    include=["documents", "metadatas", "embeddings"]
)

print(f"Total de registros: {len(dados['ids'])}")

# Exibe o primeiro registro
if dados["ids"]:

    print("\nID:")
    print(dados["ids"][0])

    print("\nDOCUMENTO:")
    print(dados["documents"][0])

    print("\nMETADADOS:")
    print(dados["metadatas"][0])

    print("\nEMBEDDING:")
    embedding = dados["embeddings"][0]

    print(f"Dimensões: {len(embedding)}")
    print(f"Primeiros 10 valores: {embedding[:10]}")
