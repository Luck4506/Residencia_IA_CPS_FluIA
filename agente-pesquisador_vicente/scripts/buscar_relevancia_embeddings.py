
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

INPUT_PATH = Path("agente-pesquisador/data/processed/chunks.json")

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Limiar inicial experimental; será calibrado com os testes.
LIMIAR_SIMILARIDADE = 0.85
 
def carregar_chunks() -> list[dict]:
    """Carrega os chunks da base de conhecimento."""
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {INPUT_PATH.resolve()}"
        )

    with INPUT_PATH.open("r", encoding="utf-8") as arquivo:
        chunks = json.load(arquivo)

    if not chunks:
        raise ValueError("A base de conhecimento está vazia.")

    return chunks


def construir_indice(chunks, modelo):
    """Gera embeddings para as perguntas e respostas."""

    documentos = [
        f"Pergunta: {chunk['pergunta']}\n"
        f"Resposta: {chunk['resposta']}"
        for chunk in chunks
    ]

    embeddings = modelo.encode(
        documentos,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    return embeddings


def buscar_relevancia(pergunta, chunks, modelo, embeddings_base, top_k=3):
    """Busca os chunks semanticamente mais semelhantes."""

    embedding_pergunta = modelo.encode(
        [pergunta],
        normalize_embeddings=True,
    )

    pontuacoes = cosine_similarity(
        embedding_pergunta,
        embeddings_base,
    )[0]

    indices = pontuacoes.argsort()[::-1][:top_k]

    return [
        {
            "chunk": chunks[indice],
            "similaridade": float(pontuacoes[indice]),
        }
        for indice in indices
    ]


def exibir_resultado(resultados):
    """Exibe o melhor resultado ou recusa a recuperação."""

    if not resultados:
        print("\nNenhum resultado encontrado.")
        return

    melhor = resultados[0]
    chunk = melhor["chunk"]
    score = melhor["similaridade"]

    print(f"\nMaior similaridade: {score:.3f}")

    if score < LIMIAR_SIMILARIDADE:
        print(
            "Não encontrei conteúdo suficientemente semelhante "
            "na base consultada."
        )
        return

    print("\nFAQ recuperado:")
    print(f"ID: {chunk['id']}")
    print(f"Pergunta: {chunk['pergunta']}")
    print(f"Resposta: {chunk['resposta']}")
    print(
        "Referência bibliográfica: "
        f"{chunk['referencia_bibliografica']}"
    )

    print("\nOutros resultados:")
    for resultado in resultados[1:]:
        item = resultado["chunk"]
        print(
            f"- {item['id']} | "
            f"similaridade: {resultado['similaridade']:.3f} | "
            f"{item['pergunta']}"
        )


def main():
    chunks = carregar_chunks()

    print("Carregando modelo de embeddings...")
    modelo = SentenceTransformer(MODEL_NAME)

    print("Gerando embeddings da base...")
    embeddings_base = construir_indice(chunks, modelo)

    print("\nBusca semântica — Bem-estar Digital")
    print("Digite 'sair' para encerrar.")

    while True:
        pergunta = input("\nSua pergunta: ").strip()

        if pergunta.lower() == "sair":
            print("Busca encerrada.")
            break

        if not pergunta:
            print("Digite uma pergunta antes de continuar.")
            continue

        resultados = buscar_relevancia(
            pergunta,
            chunks,
            modelo,
            embeddings_base,
        )

        exibir_resultado(resultados)


if __name__ == "__main__":
    main()
