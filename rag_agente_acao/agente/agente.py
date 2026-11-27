"""
Módulo Principal do Agente de Ação.
Orquestra o fluxo completo do padrão ReAct simplificado e controlado em Python:
Diagnóstico -> Recuperação RAG -> Análise Cognitiva -> Validação de Ferramenta -> Execução -> Resposta Final.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Garante acesso aos módulos util e agente
RAIZ_RAG = Path(__file__).resolve().parent.parent
if str(RAIZ_RAG) not in sys.path:
    sys.path.insert(0, str(RAIZ_RAG))

from .modelos import DiagnosticoEntrada, RespostaFinal, DecisaoAgente, ResultadoExecucao
from .recuperador import RecuperadorAgente
from .ferramentas import executar_ferramenta, CATALOGO_FERRAMENTAS
from .decisor import MotorDecisao, simular_decisao_para_teste


class AgenteAcao:
    """
    Orquestrador responsável pelo ciclo de vida das intervenções de Bem-Estar Digital.
    Garante controle estrito em Python sobre chamadas de ferramentas e formatação de saídas.
    """

    def __init__(
        self,
        top_k: int = 3,
        modelo_llm: str = "qwen2.5:3b",
        temperatura: float = 0.2,
        usar_simulacao: bool = False
    ):
        """
        Inicializa o Agente de Ação.
        :param top_k: quantidade de chunks recuperados pelo RAG (padrão ótimo: 3)
        :param modelo_llm: nome do modelo no Ollama
        :param temperatura: temperatura para geração determinística (0.2)
        :param usar_simulacao: permite rodar testes sem o serviço do Ollama ativo
        """
        self.recuperador = RecuperadorAgente(top_k=top_k)
        self.motor_decisao = MotorDecisao(modelo_llm=modelo_llm, temperatura=temperatura)
        self.usar_simulacao = usar_simulacao

    def executar(self, entrada: Union[Dict[str, Any], DiagnosticoEntrada]) -> RespostaFinal:
        """
        Executa o fluxo completo do Agente de Ação a partir de um diagnóstico.
        """
        print("\n" + "=" * 65)
        print(" INICIANDO EXECUÇÃO DO AGENTE DE AÇÃO")
        print("=" * 65)

        # 1. Validação e estruturação da entrada
        if isinstance(entrada, dict):
            diagnostico = DiagnosticoEntrada.from_dict(entrada)
        else:
            diagnostico = entrada

        print(f"\n[Etapa 1/5] Diagnóstico recebido: {diagnostico.diagnostico_id}")
        print(f" -> Relato: {diagnostico.diagnostico}")
        if diagnostico.restricoes:
            print(f" -> Restrições ativas: {diagnostico.restricoes}")
        if diagnostico.objetivos_usuario:
            print(f" -> Objetivos: {diagnostico.objetivos_usuario}")

        # 2. Recuperação de Conhecimento Científico (RAG Híbrido)
        print("\n[Etapa 2/5] Consultando Base Científica (RAG Híbrido)...")
        chunks = self.recuperador.recuperar(diagnostico)
        chunks_texto = self.recuperador.formatar_para_prompt(chunks)

        print(f" -> Chunks recuperados: {[c.id for c in chunks]}")

        # 3. Análise Cognitiva e Decisão da Ação (LLM - ReAct)
        print("\n[Etapa 3/5] Analisando contexto e restrições com a LLM...")

        if self.usar_simulacao:
            print(" -> [Modo Simulação Ativo: gerando raciocínio controlado]")
            decisao = simular_decisao_para_teste(diagnostico, chunks)
        else:
            try:
                decisao = self.motor_decisao.decidir(
                    diagnostico=diagnostico,
                    chunks=chunks,
                    chunks_formatados_texto=chunks_texto
                )
            except ConnectionError as err_conexao:
                print(f" -> [Aviso: Ollama indisponível ({err_conexao}). Alternando para simulação de teste...]")
                decisao = simular_decisao_para_teste(diagnostico, chunks)

        print(f" -> Raciocínio (Thought): {decisao.pensamento}")
        print(f" -> Estratégia Escolhida: {decisao.estrategia_selecionada or 'Nenhuma'}")
        print(f" -> Chunk Referência: {decisao.chunk_referencia or 'Nenhum'}")
        print(f" -> Ferramenta Solicitada: {decisao.ferramenta_solicitada or 'Nenhuma (sem_acao)'}")

        # 4. Validação e Execução da Ferramenta
        print("\n[Etapa 4/5] Validando e executando ferramenta em Python...")

        acao_dict: Optional[Dict[str, Any]] = None
        execucao_dict: Optional[Dict[str, Any]] = None
        status_final = "executado"

        # Caso A: LLM decidiu conscientemente por não agir
        if not decisao.ferramenta_solicitada:
            status_final = "sem_acao"
            print(" -> Decisão: Nenhuma ação a ser executada (sem_acao).")

        # Caso B: LLM solicitou uma ferramenta
        else:
            acao_dict = {
                "ferramenta": decisao.ferramenta_solicitada,
                "parametros": decisao.parametros_ferramenta
            }

            # O código Python intercepta e executa de forma segura
            resultado_execucao: ResultadoExecucao = executar_ferramenta(
                nome=decisao.ferramenta_solicitada,
                parametros=decisao.parametros_ferramenta
            )

            if resultado_execucao.sucesso:
                print(f" -> Sucesso na execução de '{decisao.ferramenta_solicitada}'!")
                execucao_dict = {
                    "sucesso": True,
                    "resultado": resultado_execucao.resultado
                }
            else:
                status_final = "falha"
                print(f" -> Falha controlada ao executar '{decisao.ferramenta_solicitada}': {resultado_execucao.erro}")
                execucao_dict = {
                    "sucesso": False,
                    "erro": resultado_execucao.erro
                }

        # 5. Montagem do Contrato Final de Saída
        print(f"\n[Etapa 5/5] Consolidando contrato final. Status: [{status_final.upper()}]")

        resposta = RespostaFinal(
            diagnostico_id=diagnostico.diagnostico_id,
            status=status_final,
            decisao={
                "estrategia_selecionada": decisao.estrategia_selecionada,
                "chunk_referencia": decisao.chunk_referencia,
                "justificativa": decisao.justificativa
            },
            acao=acao_dict,
            execucao=execucao_dict
        )

        print("=" * 65)
        print(" EXECUÇÃO CONCLUÍDA")
        print("=" * 65)

        return resposta


# ============================================================================
# INTERFACE DE TESTES EXECUTÁVEL E MENU INTERATIVO
# ============================================================================

def rodar_bateria_de_testes(agente: Optional[AgenteAcao] = None):
    """
    Executa testes práticos com diagnósticos reais e exibe o JSON de saída.
    """
    caminho_dataset = RAIZ_RAG / "avaliacao" / "diagnosticos_teste.json"
    with open(caminho_dataset, "r", encoding="utf-8") as f:
        dataset = json.load(f)["diagnosticos"]

    if agente is None:
        agente = AgenteAcao(top_k=3)

    print("\n" + "#" * 65)
    print(" TESTE 1: CASO D001 - INSTAGRAM ACIMA DA META (USO PROFISSIONAL)")
    print("#" * 65)
    caso_d001 = dict(dataset[0])
    caso_d001["restricoes"] = ["O Instagram também é utilizado para trabalho"]
    resposta_1 = agente.executar(caso_d001)

    print("\n>>> JSON FINAL GERADO (CONTRATO D001):")
    print(json.dumps(resposta_1.to_dict(), indent=2, ensure_ascii=False))

    print("\n\n" + "#" * 65)
    print(" TESTE 2: CASO D002 - TIKTOK COM HORAS ACUMULADAS")
    print("#" * 65)
    caso_d002 = dict(dataset[1])
    resposta_2 = agente.executar(caso_d002)

    print("\n>>> JSON FINAL GERADO (CONTRATO D002):")
    print(json.dumps(resposta_2.to_dict(), indent=2, ensure_ascii=False))

    print("\n\n" + "#" * 65)
    print(" TESTE 3: CENÁRIO EXCEPCIONAL - RESTRIÇÃO QUE IMPEDE AÇÃO (SEM_ACAO)")
    print("#" * 65)
    caso_sem_acao = {
        "diagnostico_id": "D_BLOQUEADO",
        "diagnostico": "Usuário permaneceu 90 minutos em jogos online.",
        "evento_detectado": {"aplicativo": "Games", "tempo_minutos": 90},
        "objetivos_usuario": ["Diminuir tempo"],
        "restricoes": ["Não quero receber nenhuma notificação ou intervenção hoje"]
    }
    resposta_3 = agente.executar(caso_sem_acao)

    print("\n>>> JSON FINAL GERADO (CONTRATO SEM_ACAO):")
    print(json.dumps(resposta_3.to_dict(), indent=2, ensure_ascii=False))


def menu_interativo():
    """
    Menu no terminal para o usuário escolher casos de teste ou digitar um relato.
    """
    caminho_dataset = RAIZ_RAG / "avaliacao" / "diagnosticos_teste.json"
    with open(caminho_dataset, "r", encoding="utf-8") as f:
        dataset_casos = {d["diagnostico_id"]: d for d in json.load(f)["diagnosticos"]}

    agente = AgenteAcao(top_k=3)

    while True:
        print("\n" + "=" * 65)
        print(" PAINEL DE TESTES DO AGENTE DE AÇÃO (BEM-ESTAR DIGITAL)")
        print("=" * 65)
        print("Escolha uma opção de teste:")
        print(" [1] Rodar bateria automática (D001, D002 e Restrição Bloqueante)")
        print(" [2] Testar Caso D003 - YouTube (Autoplay e perda de noção do tempo)")
        print(" [3] Testar Caso D004 - Notificações (Interrupções constantes nos estudos)")
        print(" [4] Testar Caso D006 - Concentração Acadêmica (Multitarefa / checagem constante)")
        print(" [5] Testar Caso D007 - Uso na Cama Antes de Dormir (Impacto no sono)")
        print(" [6] Digitar um relato/diagnóstico personalizado na hora")
        print(" [0] Sair")
        print("=" * 65)

        opcao = input("Opção desejada: ").strip()

        if opcao == "0":
            print("\nEncerrando painel de testes.")
            break
        elif opcao == "1":
            rodar_bateria_de_testes(agente)
        elif opcao == "2":
            caso = dataset_casos.get("D003")
            if caso:
                resp = agente.executar(caso)
                print("\n>>> JSON FINAL GERADO (D003):")
                print(json.dumps(resp.to_dict(), indent=2, ensure_ascii=False))
        elif opcao == "3":
            caso = dataset_casos.get("D004")
            if caso:
                resp = agente.executar(caso)
                print("\n>>> JSON FINAL GERADO (D004):")
                print(json.dumps(resp.to_dict(), indent=2, ensure_ascii=False))
        elif opcao == "4":
            caso = dataset_casos.get("D006")
            if caso:
                resp = agente.executar(caso)
                print("\n>>> JSON FINAL GERADO (D006):")
                print(json.dumps(resp.to_dict(), indent=2, ensure_ascii=False))
        elif opcao == "5":
            caso = dataset_casos.get("D007")
            if caso:
                resp = agente.executar(caso)
                print("\n>>> JSON FINAL GERADO (D007):")
                print(json.dumps(resp.to_dict(), indent=2, ensure_ascii=False))
        elif opcao == "6":
            print("\n--- TESTE COM DIAGNÓSTICO PERSONALIZADO ---")
            relato = input("Descreva o problema/diagnóstico: ").strip()
            if not relato:
                print("Relato vazio, cancelando.")
                continue
            app = input("Nome do aplicativo (opcional, ex: Instagram): ").strip()
            tempo = input("Tempo gasto em minutos (opcional, ex: 60): ").strip()
            meta = input("Meta em minutos (opcional, ex: 20): ").strip()
            restricao = input("Alguma restrição específica? (opcional, ex: 'uso para trabalho'): ").strip()

            caso_custom = {
                "diagnostico_id": "D_CUSTOM",
                "diagnostico": relato,
                "evento_detectado": {
                    "aplicativo": app if app else "Smartphone",
                    "tempo_minutos": int(tempo) if tempo.isdigit() else 0,
                    "meta_minutos": int(meta) if meta.isdigit() else 0
                },
                "objetivos_usuario": ["Melhorar hábitos digitais"],
                "restricoes": [restricao] if restricao else []
            }
            resp = agente.executar(caso_custom)
            print("\n>>> JSON FINAL GERADO (PERSONALIZADO):")
            print(json.dumps(resp.to_dict(), indent=2, ensure_ascii=False))
        else:
            print("Opção inválida, tente novamente.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--testes", "-t", "--auto"]:
        rodar_bateria_de_testes()
    else:
        menu_interativo()
