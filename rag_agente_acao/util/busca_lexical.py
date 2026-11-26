import re
from rank_bm25 import BM25Okapi
from util.busca_semantica import ConsultorRAG

class ConsultorLexicalRAG:

    def __init__(self):

        # Acessar a coleção do ChromaDB
        self.consultor = ConsultorRAG()

        # Recuperar os documentos armazenados
        dados = self.consultor.colecao.get(
            include=["documents", "metadatas"]
        )

        self.ids = dados["ids"]
        self.documentos = dados["documents"]
        self.metadados = dados["metadatas"]

        # Criar índice BM25
        corpus = [
            self.tokenizar(texto)
            for texto in self.documentos
        ]

        self.bm25 = BM25Okapi(corpus)

    # Separar o texto em palavras
    def tokenizar(self, texto):

        return re.findall(
            r"\w+",
            texto.lower()
        )

    # BUSCA LEXICAL (BM25)
    def buscar(self, pergunta, top_k=5):

        if not pergunta or not pergunta.strip():
            raise ValueError("A pergunta não pode estar vazia.")

        total = len(self.documentos)

        if total == 0:
            return []

        # Transformar pergunta em tokens
        tokens = self.tokenizar(pergunta)

        # Calcular pontuação BM25
        pontuacoes = self.bm25.get_scores(tokens)

        # Ordenar documentos pela pontuação
        indices = sorted(
            range(total),
            key=lambda i: pontuacoes[i],
            reverse=True
        )[:min(top_k, total)]

        # Organizar resultados
        resultados = []

        for indice in indices:

            chunk = {
                "id": self.ids[indice],
                "texto": self.documentos[indice],
                "metadados": self.metadados[indice],
                "distancia": pontuacoes[indice]
            }

            resultados.append(chunk)

        return resultados


# ==========================================
# INTERFACE DE TERMINAL
# ==========================================

def main():

    consultor = ConsultorLexicalRAG()

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
                print(f"Pontuação BM25: {chunk['distancia']:.4f}")
                print("\nTexto:")
                print(chunk["texto"])
                print("-" * 60)

        except Exception as erro:
            print(f"Erro na consulta: {erro}")

    print("\nConsulta encerrada.")


if __name__ == "__main__":
    main()
