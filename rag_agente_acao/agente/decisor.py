"""
Módulo do Motor de Decisão (Decision Engine) do Agente de Ação.
Responsável por enviar o contexto (diagnóstico + chunks + ferramentas)
para a LLM (Qwen 2.5 via Ollama) e converter a resposta em uma DecisaoAgente estruturada.
"""

import json
from typing import List, Dict, Any, Optional
import ollama
from .modelos import DiagnosticoEntrada, ChunkRecuperado, DefinicaoFerramenta, DecisaoAgente
from .prompts import SYSTEM_PROMPT_DECISAO, montar_prompt_decisao
from .ferramentas import obter_esquema_ferramentas_para_prompt


class MotorDecisao:
    """
    Motor que implementa o raciocínio ReAct simplificado utilizando
    geração estruturada em JSON via Ollama.
    """

    def __init__(self, modelo_llm: str = "qwen2.5:3b", temperatura: float = 0.2):
        self.modelo_llm = modelo_llm
        self.temperatura = temperatura

    def decidir(
        self,
        diagnostico: DiagnosticoEntrada,
        chunks: List[ChunkRecuperado],
        ferramentas: Optional[List[DefinicaoFerramenta]] = None,
        chunks_formatados_texto: Optional[str] = None
    ) -> DecisaoAgente:
        """
        Executa a análise do diagnóstico com base nos chunks e ferramentas disponíveis.
        Retorna um objeto DecisaoAgente.
        """
        # 1. Obter esquemas das ferramentas
        if ferramentas:
            esquema_ferramentas = [f.to_dict() for f in ferramentas]
        else:
            esquema_ferramentas = obter_esquema_ferramentas_para_prompt()

        # 2. Formatar texto dos chunks se não tiver sido fornecido
        if chunks_formatados_texto is None:
            if not chunks:
                chunks_formatados_texto = "Nenhum conhecimento relevante recuperado da base."
            else:
                chunks_formatados_texto = "\n\n".join(
                    f"--- {c.id} ---\n{c.texto.strip()}" for c in chunks
                )

        # 3. Montar o prompt do usuário
        prompt_usuario = montar_prompt_decisao(
            diagnostico=diagnostico,
            chunks_formatados=chunks_formatados_texto,
            esquema_ferramentas=esquema_ferramentas
        )

        # 4. Chamar a LLM no Ollama com saída estrita em JSON
        try:
            resposta = ollama.chat(
                model=self.modelo_llm,
                format="json",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_DECISAO},
                    {"role": "user", "content": prompt_usuario}
                ],
                options={"temperature": self.temperatura}
            )

            conteudo_resposta = resposta.get("message", {}).get("content", "").strip()
            dados_decisao = json.loads(conteudo_resposta)

            return DecisaoAgente.from_dict(dados_decisao)

        except ConnectionError as erro_conexao:
            raise ConnectionError(
                f"Não foi possível conectar ao serviço do Ollama na porta 11434. "
                f"Verifique se o Ollama está instalado e em execução ('ollama serve'). Detalhes: {erro_conexao}"
            )
        except json.JSONDecodeError as erro_json:
            # Caso a LLM retorne um texto com formatação imperfeita
            return DecisaoAgente(
                pensamento=f"Falha ao decodificar JSON retornado pelo modelo: {conteudo_resposta}",
                estrategia_selecionada=None,
                chunk_referencia=None,
                justificativa="A resposta do modelo não pôde ser interpretada como um JSON válido.",
                ferramenta_solicitada=None,
                parametros_ferramenta={}
            )
        except Exception as erro_geral:
            raise RuntimeError(f"Erro inesperado durante a inferência da LLM: {erro_geral}")


# ============================================================================
# TESTES E SIMULAÇÃO DO MOTOR DE DECISÃO
# ============================================================================

def simular_decisao_para_teste(diagnostico: DiagnosticoEntrada, chunks: List[ChunkRecuperado]) -> DecisaoAgente:
    """
    Função auxiliar para testes unitários da arquitetura sem necessidade
    do daemon do Ollama ativo no momento da execução local.
    Espelha a decisão esperada para validação do pipeline.
    """
    # Cenário de Restrição bloqueante: se usuário não quer nenhuma ação
    if any("não quero" in r.lower() for r in diagnostico.restricoes):
        return DecisaoAgente(
            pensamento="O usuário informou restrição explícita contra intervenções.",
            estrategia_selecionada=None,
            chunk_referencia=None,
            justificativa="Intervenção cancelada em respeito à restrição declarada pelo usuário.",
            ferramenta_solicitada=None,
            parametros_ferramenta={}
        )

    # Cenário normal
    if chunks:
        primeiro = chunks[0]
        app = diagnostico.evento_detectado.get("aplicativo", "dispositivo")
        return DecisaoAgente(
            pensamento=(
                f"Identificado uso excessivo no diagnóstico {diagnostico.diagnostico_id} ({app}). "
                f"O {primeiro.id} sugere notificação de limite e pausa, respeitando o uso profissional sem bloquear o app."
            ),
            estrategia_selecionada="Lembrete reflexivo para incentivar pausa consciente após limite de sessão.",
            chunk_referencia=primeiro.id,
            justificativa=(
                f"Estratégia baseada no {primeiro.id}, que reduz tempo de tela sem impedir "
                "o acesso a aplicativos essenciais ou profissionais."
            ),
            ferramenta_solicitada="enviar_notificacao",
            parametros_ferramenta={
                "mensagem": f"Você ultrapassou seu limite planejado no {app}. Que tal fazer uma pausa de 10 minutos?",
                "prioridade": "media",
                "aplicativo": app
            }
        )

    return DecisaoAgente(
        pensamento="Nenhum chunk relevante foi fornecido para embasar uma ação.",
        estrategia_selecionada=None,
        chunk_referencia=None,
        justificativa="Sem conhecimento suficiente na base para intervir.",
        ferramenta_solicitada=None,
        parametros_ferramenta={}
    )


if __name__ == "__main__":
    print("=== TESTE DO MOTOR DE DECISÃO ===")

    # Teste 1: Validação do Prompt Montado
    diagnostico_exemplo = DiagnosticoEntrada(
        diagnostico_id="D001",
        diagnostico="Uso do Instagram acima da meta estabelecida.",
        evento_detectado={"aplicativo": "Instagram", "tempo_minutos": 75, "meta_minutos": 30},
        objetivos_usuario=["Reduzir tempo de uso do Instagram"],
        restricoes=["O Instagram também é utilizado para trabalho"]
    )

    chunks_exemplo = [
        ChunkRecuperado(
            id="CHUNK 14",
            texto="ESTRATÉGIA: Enviar notificação reflexiva ao exceder limite de tempo.\nRESTRIÇÕES: Não bloquear.",
            score_hibrido=0.0328
        )
    ]

    prompt_gerado = montar_prompt_decisao(
        diagnostico=diagnostico_exemplo,
        chunks_formatados="--- CHUNK 14 ---\nESTRATÉGIA: Enviar notificação reflexiva ao exceder limite.",
        esquema_ferramentas=obter_esquema_ferramentas_para_prompt()
    )

    print("\n[Prompt Gerado (Prévia)]:\n")
    print(prompt_gerado[:350] + "\n... [truncado] ...")

    # Teste 2: Teste de Decisão Estruturada com Simulação de Cenário
    decisao = simular_decisao_para_teste(diagnostico_exemplo, chunks_exemplo)
    print("\n[Decisão Estruturada Produzida]:")
    print(json.dumps(decisao.to_dict(), indent=2, ensure_ascii=False))

    # Teste 3: Cenário com Restrição Rígida (sem_acao)
    diag_bloqueado = DiagnosticoEntrada(
        diagnostico_id="D999",
        diagnostico="Tempo de tela alto",
        restricoes=["Não quero receber notificações neste momento"]
    )
    decisao_sem_acao = simular_decisao_para_teste(diag_bloqueado, chunks_exemplo)
    print("\n[Decisão em Caso de Restrição Rígida]:")
    print(json.dumps(decisao_sem_acao.to_dict(), indent=2, ensure_ascii=False))
