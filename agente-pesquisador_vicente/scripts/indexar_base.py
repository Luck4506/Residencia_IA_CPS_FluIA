import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

INPUT_PATH = Path("agente-pesquisador/data/processed/chunks.json")
DB_PATH = Path("agente-pesquisador/data/chromadb")

COLLECTION_NAME = "bem_estar_digital"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {INPUT_PATH.resolve()}"
        )

    with INPUT_PATH.open("r", encoding="utf-8") as arquivo:
        chunks = json.load(arquivo)

    if not chunks:
        raise ValueError("A base de conhecimento está vazia.")

    print("Carregando modelo de embeddings...")
    modelo = SentenceTransformer(MODEL_NAME)

    documentos = [
        f"Pergunta: {chunk['pergunta']}\n"
        f"Resposta: {chunk['resposta']}"
        for chunk in chunks
    ]

    ids = [chunk["id"] for chunk in chunks]

    metadados = [
        {
            "pergunta": chunk["pergunta"],
            "referencia_bibliografica": chunk[
                "referencia_bibliografica"
            ],
        }
        for chunk in chunks
    ]

    print("Gerando embeddings...")
    embeddings = modelo.encode(
        documentos,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).tolist()

    # Cria ou abre o banco persistente.
    cliente = chromadb.PersistentClient(path=str(DB_PATH))

    # Nesta versão, recriamos a coleção para refletir
    # exatamente o conteúdo atual do chunks.json.
    colecoes = [
        c.name for c in cliente.list_collections()
    ]

    if COLLECTION_NAME in colecoes:
        cliente.delete_collection(COLLECTION_NAME)

    colecao = cliente.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    colecao.add(
        ids=ids,
        documents=documentos,
        metadatas=metadados,
        embeddings=embeddings,
    )

    print(f"\nIndexação concluída: {colecao.count()} chunks.")
    print(f"Banco salvo em: {DB_PATH.resolve()}")


if __name__ == "__main__":
    main()
