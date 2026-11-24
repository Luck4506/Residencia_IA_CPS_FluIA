from typing import List, Optional, Tuple

from Residencia_IA_CPS_FluIA.analise_alerta.schemas import RagChunk
from Residencia_IA_CPS_FluIA.rag_agente_acao.util.consulta import ConsultorRAG


def distancia_cosseno_para_score(distancia: float) -> float:
    """Converte distância cosseno do ChromaDB em similaridade (0.0 a 1.0)."""
    similaridade = 1.0 - float(distancia)
    return max(0.0, min(1.0, round(similaridade, 4)))


def consultar_rag_para_analista(
    consultor: ConsultorRAG,
    query: str,
    top_k: int = 5,
) -> Tuple[str, List[RagChunk]]:
    """
    Consulta o ConsultorRAG original (sem alterá-lo) e converte o retorno
    para (rag_status, lista_de_RagChunk) compatíveis com AlertAnalysisInput.
    """
    try:
        resultados = consultor.buscar(pergunta=query, top_k=top_k)
    except Exception:
        return "error", []

    if not resultados:
        return "empty", []

    chunks: List[RagChunk] = []
    for item in resultados:
        metadados = item.get("metadados") or {}
        score = distancia_cosseno_para_score(item.get("distancia", 1.0))

        secao_bruta = (
            metadados.get("secao")
            or metadados.get("section")
            or metadados.get("titulo")
            or (f"chunk_{metadados['numero']}" if "numero" in metadados else None)
        )
        section: Optional[str] = str(secao_bruta) if secao_bruta is not None else None

        chunks.append(
            RagChunk(
                chunk_id=str(item.get("id", "")),
                source=str(
                    metadados.get("arquivo_origem")
                    or metadados.get("source")
                    or "base_conhecimento"
                ),
                content=str(item.get("texto", "")),
                score=score,
                section=section,
            )
        )

    return "ok", chunks
