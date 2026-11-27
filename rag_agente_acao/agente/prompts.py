"""
Módulo de prompts do Agente de Ação.
Define as instruções do sistema para o raciocínio ReAct simplificado
e geração de chamadas estruturadas em JSON.
"""

import json
from typing import List, Dict, Any
from .modelos import DiagnosticoEntrada


SYSTEM_PROMPT_DECISAO = """Você é o Agente de Ação especializado em Bem-Estar Digital.

Sua missão é analisar o diagnóstico comportamental do usuário, cruzar com as estratégias científicas recuperadas do RAG e selecionar uma intervenção prática e empática, acionando a ferramenta correta via JSON.

DIRETRIZES OBRIGATÓRIAS DE RACIOCÍNIO (ReAct Simplificado):

1. ANÁLISE DE RESTRIÇÕES E OBJETIVOS:
   - Respeite rigorosamente os objetivos e restrições do usuário.
   - Se o usuário possui uma restrição explícita (ex: "utiliza o aplicativo para trabalho"), NUNCA recomende bloqueio total ou intervenções que prejudiquem essa necessidade.
   - Não invente informações clínicas ou diagnósticos médicos.

2. AVALIAÇÃO DOS CHUNKS RECUPERADOS:
   - Analise os chunks fornecidos no contexto.
   - Descarte chunks cuja SITUAÇÃO ou RESTRIÇÕES sejam incompatíveis com o caso do usuário.
   - Não selecione uma estratégia apenas pelo score de recuperação; priorize a adequação real ao contexto.
   - Se nenhum chunk for aplicável, decida conscientemente por NÃO agir (sem_acao).

3. SELEÇÃO DE FERRAMENTA:
   - Só utilize ferramentas expressamente listadas no catálogo de FERRAMENTAS DISPONÍVEIS.
   - NUNCA invente nomes de ferramentas.
   - Preencha todos os parâmetros obrigatórios exigidos pela ferramenta.
   - Se nenhuma ferramenta for adequada para executar a estratégia, não force a execução.

4. TOMADA DE DECISÃO:
   - Se houver intervenção viável: identifique o CHUNK de referência, a estratégia, a ferramenta e seus parâmetros.
   - Se NÃO houver intervenção viável: defina "estrategia_selecionada" como null, "ferramenta_solicitada" como null e justifique o motivo no pensamento.

FORMATO DE RESPOSTA OBRIGATÓRIO (JSON PURO):
Você deve responder ESTRITAMENTE em formato JSON com o seguinte esquema:

{
  "pensamento": "Passo a passo do raciocínio: 1) o que foi identificado; 2) como as restrições afetam a escolha; 3) por que a estratégia e ferramenta foram (ou não foram) escolhidas.",
  "estrategia_selecionada": "Resumo da estratégia escolhida ou null",
  "chunk_referencia": "CHUNK XX ou null",
  "justificativa": "Explicação concisa e clara da fundamentação da escolha ou motivo para ausência de ação.",
  "ferramenta_solicitada": "nome_da_ferramenta ou null",
  "parametros_ferramenta": {
    "parametro_1": "valor"
  }
}
"""


def montar_prompt_decisao(
    diagnostico: DiagnosticoEntrada,
    chunks_formatados: str,
    esquema_ferramentas: List[Dict[str, Any]]
) -> str:
    """
    Constrói a mensagem do usuário contendo o diagnóstico estruturado,
    as estratégias científicas recuperadas do RAG e o catálogo de ferramentas.
    """
    ferramentas_texto = json.dumps(esquema_ferramentas, indent=2, ensure_ascii=False)

    restricoes_texto = (
        "\n".join(f"- {r}" for r in diagnostico.restricoes)
        if diagnostico.restricoes
        else "Nenhuma restrição específica informada."
    )

    objetivos_texto = (
        "\n".join(f"- {o}" for o in diagnostico.objetivos_usuario)
        if diagnostico.objetivos_usuario
        else "Nenhum objetivo específico informado."
    )

    evento_texto = (
        json.dumps(diagnostico.evento_detectado, indent=2, ensure_ascii=False)
        if diagnostico.evento_detectado
        else "Sem dados detalhados de evento."
    )

    prompt = f"""
        === DADOS DO USUÁRIO ===
        DIAGNÓSTICO ID: {diagnostico.diagnostico_id}
        RELATO/DIAGNÓSTICO: {diagnostico.diagnostico}

        EVENTO DETECTADO:
        {evento_texto}

        OBJETIVOS DO USUÁRIO:
        {objetivos_texto}

        RESTRIÇÕES DO USUÁRIO:
        {restricoes_texto}

        === CONHECIMENTOS CIENTÍFICOS RECUPERADOS (RAG) ===
        {chunks_formatados}

        === FERRAMENTAS DISPONÍVEIS ===
        {ferramentas_texto}

        Com base nas informações acima, analise a situação, avalie as restrições e forneça sua decisão estritamente no formato JSON solicitado."""

    return prompt
