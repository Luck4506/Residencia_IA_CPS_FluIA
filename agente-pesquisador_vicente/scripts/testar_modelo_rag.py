from pathlib import Path
import chromadb
import ollama
from sentence_transformers import SentenceTransformer

# Configurações do projeto
DB_PATH = Path("agente-pesquisador/data/chromadb")
COLLECTION_NAME = "bem_estar_digital"

MODEL_NAME = "qwen2.5:3b"
EMBEDDING_MODEL = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

LIMIAR_SIMILARIDADE = 0.45
TOP_K = 3

def carregar_recursos():
    """Carrega o modelo de embeddings e abre o banco vetorial."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Banco vetorial não encontrado: {DB_PATH.resolve()}. "
            "Execute primeiro scripts/indexar_base.py."
        )

    print("Carregando modelo de embeddings...")
    modelo_embeddings = SentenceTransformer(EMBEDDING_MODEL)

    cliente = chromadb.PersistentClient(path=str(DB_PATH))

    try:
        colecao = cliente.get_collection(
            name=COLLECTION_NAME
        )
    except Exception as erro:
        raise RuntimeError(
            "Coleção não encontrada. Execute o script de indexação."
        ) from erro

    if colecao.count() == 0:
        raise ValueError("A coleção está vazia.")

    print(f"Banco carregado: {colecao.count()} registros.")

    return modelo_embeddings, colecao


def perguntar_ao_qwen(pergunta, contexto=None):
    """Consulta o Qwen diretamente ou com contexto do RAG."""

    if contexto is None:
        instrucao = (
            "Responda à pergunta do usuário em português. "
            "Esta é uma resposta sem consulta à base de conhecimento. "
            "Se não souber responder, admita a incerteza."
        )
        mensagem_usuario = pergunta

    else:
        instrucao = """
Você é o FluIA, um assistente de bem-estar digital que responde
com base exclusivamente no contexto fornecido.

Regras:
1. Use somente informações sustentadas pelo contexto.
2. Não invente fatos, referências ou recomendações.
3. Se o contexto não contiver informações suficientes,
   diga claramente que não encontrou informação suficiente
   na base de conhecimento.
4. Diferencie o que o contexto afirma de qualquer conclusão
   que não possa ser sustentada por ele.
5. Responda em português, de forma clara e objetiva.
"""

        mensagem_usuario = f"""
CONTEXTO RECUPERADO DA BASE:

{contexto}

PERGUNTA DO USUÁRIO:
{pergunta}

Responda seguindo rigorosamente as instruções.
"""

    resposta = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": instrucao},
            {"role": "user", "content": mensagem_usuario},
        ],
        options={
            "temperature": 0.1,
            "num_predict": 300,
        },
    )

    return resposta["message"]["content"]


def recuperar_contexto(pergunta, modelo_embeddings, colecao):
    """Busca os trechos mais semelhantes no ChromaDB."""

    embedding = modelo_embeddings.encode(
        [pergunta],
        normalize_embeddings=True,
    )[0].tolist()

    resultados = colecao.query(
        query_embeddings=[embedding],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"],
    )

    documentos = resultados["documents"][0]
    metadados = resultados["metadatas"][0]
    distancias = resultados["distances"][0]

    trechos = []

    for documento, metadata, distancia in zip(
        documentos, metadados, distancias
    ):
        # A coleção usa distância cosseno.
        similaridade = 1.0 - distancia

        print(
            f"- Similaridade: {similaridade:.3f} | "
            f"Pergunta: {metadata.get('pergunta', 'N/D')}"
        )

        if similaridade >= LIMIAR_SIMILARIDADE:
            referencia = metadata.get(
                "referencia_bibliografica", "Não informada"
            )
            trechos.append(
                f"{documento}\nReferência: {referencia}"
            )

    if not trechos:
        return None

    return "\n\n---\n\n".join(trechos)


def main():
    modelo_embeddings, colecao = carregar_recursos()

    print("\nTeste comparativo: Qwen puro x Qwen + RAG")
    print("Digite 'sair' para encerrar.")

    while True:
        pergunta = input("\nSua pergunta: ").strip()

        if pergunta.lower() == "sair":
            break

        if not pergunta:
            print("Digite uma pergunta.")
            continue

        try:
            print("\n" + "=" * 60)
            print("1. RESPOSTA DO QWEN SEM RAG")
            print("=" * 60)

            resposta_pura = perguntar_ao_qwen(pergunta)
            print(resposta_pura)

            print("\n" + "=" * 60)
            print("2. RECUPERAÇÃO DE CONTEXTO")
            print("=" * 60)

            contexto = recuperar_contexto(
                pergunta, modelo_embeddings, colecao
            )

            print("\n" + "=" * 60)
            print("3. RESPOSTA DO QWEN COM RAG")
            print("=" * 60)

            if contexto is None:
                print(
                    "Nenhum trecho atingiu o limiar de similaridade. "
                    "O modelo não será consultado nesta etapa."
                )
                print(
                    "Resposta: Não encontrei informação "
                    "suficiente na base de conhecimento."
                )
                continue

            resposta_rag = perguntar_ao_qwen(
                pergunta, contexto=contexto
            )
            print(resposta_rag)

        except Exception as erro:
            print(f"\nErro durante o teste: {erro}")
            print(
                "Verifique se o Ollama está aberto e se o modelo "
                "foi baixado corretamente."
            )


if __name__ == "__main__":
    main()
