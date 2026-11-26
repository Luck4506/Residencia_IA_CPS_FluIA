"""
Módulo de integração do Agente de Ação com o RAG (Recuperador Híbrido).
Recebe um DiagnosticoEntrada, constrói a consulta e retorna ChunksRecuperados padronizados.
"""

import os
import sys
from pathlib import Path
from typing import List

# Configura modo offline para HuggingFace/SentenceTransformers se não houver rede
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# Garante que o diretório raiz do rag_agente_acao esteja acessível para imports de 'util'
RAIZ_RAG = Path(__file__).resolve().parent.parent
if str(RAIZ_RAG) not in sys.path:
    sys.path.insert(0, str(RAIZ_RAG))

from util.busca_hibrida import BuscaHibrida
from .modelos import DiagnosticoEntrada, ChunkRecuperado


class RecuperadorAgente:
    """
    Adaptador de RAG responsável por formular a consulta a partir do diagnóstico
    e retornar chunks estruturados para o Agente de Ação.
    """

    def __init__(self, top_k: int = 3):
        """
        Inicializa a Busca Híbrida existente (ChromaDB + BM25 + RRF).
        top_k=3 foi o valor com melhor equilíbrio de precisão e cobertura nos testes de baseline.
        """
        self.top_k = top_k
        self.busca_hibrida = BuscaHibrida()

    def construir_consulta(self, diagnostico: DiagnosticoEntrada) -> str:
        """
        Monta uma consulta semântica e lexical rica, combinando o diagnóstico do problema
        com os objetivos declarados do usuário.
        """
        partes = [diagnostico.diagnostico.strip()]

        if diagnostico.objetivos_usuario:
            objetivos_texto = " ".join(diagnostico.objetivos_usuario).strip()
            partes.append(objetivos_texto)

        # Se houver dados do evento (ex: aplicativo específico), reforça na consulta
        app = diagnostico.evento_detectado.get("aplicativo")
        if app and app.lower() not in partes[0].lower():
            partes.append(f"Aplicativo: {app}")

        consulta = " ".join(partes)
        return consulta

    def _padronizar_id_chunk(self, raw_id: str) -> str:
        """
        Converte IDs internos como 'chunk-001' para 'CHUNK 01' para manter
        consistência com a base de conhecimento e os testes.
        """
        if raw_id.lower().startswith("chunk-"):
            try:
                num = int(raw_id.split("-")[1])
                return f"CHUNK {num:02d}"
            except (IndexError, ValueError):
                pass
        return raw_id.upper()

    def recuperar(self, diagnostico: DiagnosticoEntrada) -> List[ChunkRecuperado]:
        """
        Executa a recuperação híbrida e retorna os chunks formatados como ChunkRecuperado.
        """
        consulta = self.construir_consulta(diagnostico)
        resultados_brutos = self.busca_hibrida.buscar(consulta, top_k=self.top_k)

        chunks_formatados: List[ChunkRecuperado] = []
        for item in resultados_brutos:
            chunk = ChunkRecuperado(
                id=self._padronizar_id_chunk(item["id"]),
                texto=item["texto"],
                metadados=item.get("metadados", {}),
                score_hibrido=item.get("score_hibrido", 0.0)
            )
            chunks_formatados.append(chunk)

        return chunks_formatados

    def formatar_para_prompt(self, chunks: List[ChunkRecuperado]) -> str:
        """
        Organiza os chunks recuperados em formato textual claro e legível
        para serem consumidos no prompt da LLM.
        """
        if not chunks:
            return "Nenhum conhecimento relevante recuperado da base."

        blocos = []
        for i, chunk in enumerate(chunks, start=1):
            bloco = (
                f"--- {chunk.id} (Relevância RRF: {chunk.score_hibrido:.4f}) ---\n"
                f"{chunk.texto.strip()}"
            )
            blocos.append(bloco)

        return "\n\n".join(blocos)


# ============================================================================
# TESTE DA INTEGRAÇÃO COM UM CASO REAL DO DATASET
# ============================================================================

if __name__ == "__main__":
    import json

    print("=== TESTE DE RECUPERAÇÃO DO AGENTE DE AÇÃO COM CASO REAL ===")

    caminho_dataset = RAIZ_RAG / "avaliacao" / "diagnosticos_teste.json"
    with open(caminho_dataset, "r", encoding="utf-8") as f:
        dados_dataset = json.load(f)

    # Pegamos o primeiro diagnóstico (D001) para teste
    caso_bruto = dados_dataset["diagnosticos"][0]
    diagnostico_teste = DiagnosticoEntrada.from_dict(caso_bruto)

    print(f"\n[Diagnóstico de Entrada]: {diagnostico_teste.diagnostico_id}")
    print(f"Texto: {diagnostico_teste.diagnostico}")
    print(f"Objetivos: {diagnostico_teste.objetivos_usuario}")
    print(f"Restrições/Divergências: {diagnostico_teste.restricoes}")

    recuperador = RecuperadorAgente(top_k=3)
    consulta_gerada = recuperador.construir_consulta(diagnostico_teste)
    print(f"\n[Consulta Montada para o RAG]:\n'{consulta_gerada}'\n")

    chunks_recuperados = recuperador.recuperar(diagnostico_teste)
    print(f"[Chunks Recuperados ({len(chunks_recuperados)})]:")
    for chunk in chunks_recuperados:
        print(f" -> {chunk.id} | Score RRF: {chunk.score_hibrido:.4f}")

    print("\n[Formatação para o Prompt da LLM (Amostra do Primeiro Chunk)]:\n")
    print(recuperador.formatar_para_prompt([chunks_recuperados[0]]))
