import re
from rank_bm25 import BM25Okapi
from  util.busca_semantica import ConsultorRAG
from  util.busca_lexical import ConsultorLexicalRAG


class BuscaHibrida:

    def __init__(self):

        self.consultor = ConsultorRAG()
        self.consultorLexical = ConsultorLexicalRAG()

        # Recuperar todos os chunks da coleção
        dados = self.consultor.colecao.get(
            include=["documents", "metadatas"]
        )

        self.ids = dados["ids"]
        self.documentos = dados["documents"]
        self.metadados = dados["metadatas"]

    # Busca híbrida
    def buscar(self, pergunta, top_k=5):

        if not pergunta or not pergunta.strip():
            raise ValueError("A pergunta não pode estar vazia.")

        total = len(self.ids)

        if total == 0:
            return []

        quantidade = min(top_k * 2, total)

        # 1. Busca semântica
        resultados_semanticos = self.consultor.buscar(
            pergunta,
            top_k=quantidade
        )

        # 2. Busca lexical (BM25)
        indices_bm25 = self.consultorLexical.buscar(
            pergunta,
            top_k=quantidade
        )

        # 3. Combinar rankings usando RRF
        ranking = {}

        # Resultados semânticos
        for posicao, chunk in enumerate(resultados_semanticos, start=1):

            id_chunk = chunk["id"]

            ranking[id_chunk] = (
                ranking.get(id_chunk, 0)
                + 1 / (60 + posicao)
            )

        # Resultados BM25
        for posicao, chunk in enumerate(indices_bm25, start=1):

            id_chunk = chunk["id"]

            ranking[id_chunk] = (
                ranking.get(id_chunk, 0)
                + 1 / (60 + posicao)
            )
        # 4. Ordenar pelo score híbrido
        melhores = sorted(
            ranking.items(),
            key=lambda item: item[1],
            reverse=True
        )[:top_k]

        # 5. Organizar no formato do ConsultorRAG
        documentos_por_id = {
            id_chunk: i
            for i, id_chunk in enumerate(self.ids)
        }

        resultados = []

        for id_chunk, score in melhores:

            indice = documentos_por_id[id_chunk]

            resultados.append({
                "id": id_chunk,
                "texto": self.documentos[indice],
                "metadados": self.metadados[indice],
                "score_hibrido": score
            })

        return resultados
