import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Arquivo de chunks criado na etapa anterior
INPUT_PATH = Path("agente-pesquisador/data/processed/chunks.json")

# Limiar inicial para os testes.
# Vamos ajustar esse valor observando os resultados.
LIMIAR_SIMILARIDADE = 0.15


def carregar_chunks() -> list[dict]:
    """Carrega os chunks do arquivo JSON."""
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {INPUT_PATH.resolve()}"
        )

    with INPUT_PATH.open("r", encoding="utf-8") as arquivo:
        chunks = json.load(arquivo)

    if not chunks:
        raise ValueError("A base de conhecimento está vazia.")

    return chunks


def construir_indice(chunks: list[dict]):
    """Cria a representação TF-IDF dos FAQs."""

    # Indexamos pergunta e resposta, sem incluir a referência
    # bibliográfica no cálculo de relevância.
    documentos = [
        f"{chunk['pergunta']} {chunk['resposta']}"
        for chunk in chunks
    ]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
    )

    matriz = vectorizer.fit_transform(documentos)

    return vectorizer, matriz


def buscar_relevancia(
    pergunta_usuario: str,
    chunks: list[dict],
    vectorizer,
    matriz,
    top_k: int = 3,
) -> list[dict]:
    """Recupera os FAQs mais semelhantes à pergunta."""

    vetor_pergunta = vectorizer.transform([pergunta_usuario])

    pontuacoes = cosine_similarity(
        vetor_pergunta,
        matriz
    )[0]

    # Ordena os índices da maior para a menor similaridade.
    indices = pontuacoes.argsort()[::-1][:top_k]

    resultados = []

    for indice in indices:
        resultados.append({
            "chunk": chunks[indice],
            "similaridade": float(pontuacoes[indice]),
        })

    return resultados


def exibir_resultado(resultados: list[dict]) -> None:
    """Exibe o melhor resultado ou informa que não há evidência suficiente."""

    if not resultados:
        print("\nNenhum resultado encontrado.")
        return

    melhor = resultados[0]
    chunk = melhor["chunk"]
    score = melhor["similaridade"]

    print(f"\nMaior similaridade: {score:.3f}")

    if score < LIMIAR_SIMILARIDADE:
        print("Não encontrei conteúdo suficientemente semelhante na base.")
        print("O limiar é experimental e poderá ser ajustado.")
        return

    print("\nPossível conteúdo relevante:")
    print(f"\nID: {chunk['id']}")
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
    vectorizer, matriz = construir_indice(chunks)

    print("Busca de relevância — Bem-estar Digital")
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
            vectorizer,
            matriz,
        )

        exibir_resultado(resultados)


if __name__ == "__main__":
    main()
