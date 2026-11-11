import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "data" / "base_conhecimento"
NOME_COLECAO = "bem_estar_digital"
MODELO_EMBEDDING = (
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

class ConsultorRAG:

    def __init__(self):

        print("Carregando modelo de embeddings...")

        self.modelo = SentenceTransformer(
            MODELO_EMBEDDING
        )

        print("Conectando ao ChromaDB...")

        self.cliente = chromadb.PersistentClient(
            path=str(DB_DIR)
        )

        self.colecao = self.cliente.get_collection(
            name=NOME_COLECAO
        )

        print(
            f"Base carregada: {self.colecao.count()} chunks"
        )

    # BUSCA SEMÂNTICA
    def buscar(self, pergunta, top_k=5):

        if not pergunta or not pergunta.strip():
            raise ValueError("A pergunta não pode estar vazia.")

        total_chunks = self.colecao.count()

        if total_chunks == 0:
            return []

        quantidade = min(top_k, total_chunks)

        # 1. Transformar a pergunta em embedding
        embedding_pergunta = self.modelo.encode(
            pergunta,
            normalize_embeddings=True
        )

        # 2. Consultar o ChromaDB
        resultados = self.colecao.query(
            query_embeddings=[
                embedding_pergunta.tolist()
            ],
            n_results=quantidade,
            include=[
                "documents",
                "metadatas",
                "distances"
            ]
        )

        # 3. Organizar os resultados
        chunks_recuperados = []

        for i in range(len(resultados["ids"][0])):

            chunk = {
                "id": resultados["ids"][0][i],
                "texto": resultados["documents"][0][i],
                "metadados": resultados["metadatas"][0][i],
                "distancia": resultados["distances"][0][i]
            }

            chunks_recuperados.append(chunk)

        return chunks_recuperados

# ==========================================
# INTERFACE DE TERMINAL
# ==========================================

def main():

    consultor = ConsultorRAG()

    print("\n=== CONSULTA À BASE DE CONHECIMENTO ===")
    print("Digite 'sair' para encerrar.\n")

    while True:

        pergunta = input("Pergunta: ").strip()

        if pergunta.lower() in ["sair", "exit", "quit"]:
            break

        try:

            resultados = consultor.buscar(
                pergunta,
                top_k=5
            )

            print("\n=== CHUNKS RECUPERADOS ===")

            for i, chunk in enumerate(resultados, start=1):

                print(f"\n[{i}] {chunk['id']}")

                print(
                    f"Distância: {chunk['distancia']:.4f}"
                )

                print("\nTexto:")
                print(chunk["texto"])

                """ print("\nMetadados:")
                for campo, valor in chunk["metadados"].items():
                    print(f"  {campo}: {valor}") """

                print("-" * 60)

        except Exception as erro:
            print(f"Erro na consulta: {erro}")

    print("\nConsulta encerrada.")


if __name__ == "__main__":
    main()
