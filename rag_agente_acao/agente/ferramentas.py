"""
Módulo de ferramentas (tools) mockadas do Agente de Ação.
Define as funções disponíveis, seus esquemas e o executor controlado em Python.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from .modelos import DefinicaoFerramenta, ResultadoExecucao


# ============================================================================
# 1. IMPLEMENTAÇÃO DAS FUNÇÕES MOCKADAS
# ============================================================================

def mock_enviar_notificacao(
    mensagem: str,
    prioridade: str = "media",
    aplicativo: Optional[str] = None
) -> Dict[str, Any]:
    """
    Simula o envio de uma notificação personalizada para o dispositivo do usuário.
    """
    if not mensagem or not mensagem.strip():
        raise ValueError("O parâmetro 'mensagem' não pode ser vazio.")

    prioridades_validas = ["baixa", "media", "alta"]
    if prioridade.lower() not in prioridades_validas:
        prioridade = "media"

    return {
        "status": "enviada",
        "mensagem": mensagem.strip(),
        "prioridade": prioridade.lower(),
        "aplicativo_alvo": aplicativo,
        "horario_envio": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def mock_consultar_tarefas(
    categoria: str = "todas"
) -> Dict[str, Any]:
    """
    Simula a consulta ao gerenciador de tarefas do usuário, retornando atividades
    pendentes que podem substituir o tempo improdutivo de tela.
    """
    tarefas_mock = [
        {
            "id": "T01",
            "titulo": "Revisar relatório da Residência em IA",
            "categoria": "estudo",
            "tempo_estimado_minutos": 45
        },
        {
            "id": "T02",
            "titulo": "Caminhada de 20 minutos ao ar livre",
            "categoria": "saude",
            "tempo_estimado_minutos": 20
        },
        {
            "id": "T03",
            "titulo": "Organizar caixa de entrada de e-mails",
            "categoria": "trabalho",
            "tempo_estimado_minutos": 15
        },
        {
            "id": "T04",
            "titulo": "Leitura de 1 capítulo do livro técnico",
            "categoria": "estudo",
            "tempo_estimado_minutos": 30
        }
    ]

    cat_filtro = categoria.lower().strip()
    if cat_filtro in ["", "todas"]:
        filtradas = tarefas_mock
    else:
        filtradas = [t for t in tarefas_mock if t["categoria"] == cat_filtro]

    return {
        "total_encontradas": len(filtradas),
        "categoria_filtrada": cat_filtro,
        "tarefas": filtradas
    }


def mock_consultar_historico(
    aplicativo: str,
    dias: int = 7
) -> Dict[str, Any]:
    """
    Simula a consulta ao histórico detalhado de uso de um aplicativo específico.
    """
    if not aplicativo or not aplicativo.strip():
        raise ValueError("O parâmetro 'aplicativo' é obrigatório.")

    dias = max(1, min(int(dias), 30))

    return {
        "aplicativo": aplicativo.strip(),
        "periodo_analisado_dias": dias,
        "media_diaria_minutos": 68,
        "limite_atual_meta_minutos": 30,
        "dias_acima_da_meta": 5,
        "detalhes_ultimos_dias": [
            {"dia": "D-1", "minutos": 75, "meta_atingida": False},
            {"dia": "D-2", "minutos": 82, "meta_atingida": False},
            {"dia": "D-3", "minutos": 25, "meta_atingida": True},
            {"dia": "D-4", "minutos": 90, "meta_atingida": False},
            {"dia": "D-5", "minutos": 70, "meta_atingida": False}
        ]
    }


# ============================================================================
# 2. CATÁLOGO DE FERRAMENTAS E SEUS ESQUEMAS
# ============================================================================

# Mapeamento interno das funções executáveis em Python
_FUNCOES_REGISTRADAS = {
    "enviar_notificacao": mock_enviar_notificacao,
    "consultar_tarefas": mock_consultar_tarefas,
    "consultar_historico": mock_consultar_historico
}

# Definições que serão passadas no prompt para a LLM entender o que cada ferramenta faz
CATALOGO_FERRAMENTAS: List[DefinicaoFerramenta] = [
    DefinicaoFerramenta(
        nome="enviar_notificacao",
        descricao=(
            "Envia uma notificação ou lembrete sutil e personalizado ao smartphone do usuário. "
            "Útil para lembretes de pausa, alertas de tempo limite ou mensagens de conscientização."
        ),
        parametros={
            "mensagem": {
                "tipo": "string",
                "obrigatorio": True,
                "descricao": "Texto claro, empático e prático da notificação a ser exibida."
            },
            "prioridade": {
                "tipo": "string",
                "obrigatorio": False,
                "opcoes": ["baixa", "media", "alta"],
                "padrao": "media",
                "descricao": "Nível de urgência da notificação."
            },
            "aplicativo": {
                "tipo": "string",
                "obrigatorio": False,
                "descricao": "Nome do aplicativo associado ao evento (ex: 'Instagram', 'TikTok')."
            }
        }
    ),
    DefinicaoFerramenta(
        nome="consultar_tarefas",
        descricao=(
            "Consulta a lista de tarefas e atividades pendentes do usuário. "
            "Útil quando a estratégia sugere substituir o tempo excessivo de tela por uma atividade produtiva ou pausa saudável."
        ),
        parametros={
            "categoria": {
                "tipo": "string",
                "obrigatorio": False,
                "opcoes": ["estudo", "trabalho", "saude", "todas"],
                "padrao": "todas",
                "descricao": "Categoria específica de tarefas para filtrar."
            }
        }
    ),
    DefinicaoFerramenta(
        nome="consultar_historico",
        descricao=(
            "Consulta dados históricos de uso de um aplicativo nos últimos dias. "
            "Útil para obter métricas de comparação antes de emitir um diagnóstico ou intervenção personalizada."
        ),
        parametros={
            "aplicativo": {
                "tipo": "string",
                "obrigatorio": True,
                "descricao": "Nome do aplicativo a ser consultado (ex: 'Instagram')."
            },
            "dias": {
                "tipo": "integer",
                "obrigatorio": False,
                "padrao": 7,
                "descricao": "Quantidade de dias de histórico a analisar."
            }
        }
    )
]


# ============================================================================
# 3. VALIDADOR E EXECUTOR CONTROLADO
# ============================================================================

def obter_esquema_ferramentas_para_prompt() -> List[Dict[str, Any]]:
    """
    Retorna o catálogo formatado para ser injetado nas instruções da LLM.
    """
    return [ferramenta.to_dict() for ferramenta in CATALOGO_FERRAMENTAS]


def executar_ferramenta(nome: str, parametros: Dict[str, Any]) -> ResultadoExecucao:
    """
    Valida a solicitação da LLM e executa a função Python correspondente com segurança.
    Garante que a LLM não execute funções arbitrárias.
    """
    if not nome:
        return ResultadoExecucao(
            sucesso=False,
            erro="Nenhuma ferramenta foi especificada para execução."
        )

    funcao = _FUNCOES_REGISTRADAS.get(nome)
    if not funcao:
        ferramentas_validas = list(_FUNCOES_REGISTRADAS.keys())
        return ResultadoExecucao(
            sucesso=False,
            erro=f"Ferramenta '{nome}' não existe no catálogo. Disponíveis: {ferramentas_validas}"
        )

    # Validar parâmetros obrigatórios conforme catálogo
    definicao = next((f for f in CATALOGO_FERRAMENTAS if f.nome == nome), None)
    if definicao:
        for param_nome, param_info in definicao.parametros.items():
            if param_info.get("obrigatorio") and param_nome not in parametros:
                return ResultadoExecucao(
                    sucesso=False,
                    erro=f"Parâmetro obrigatório '{param_nome}' ausente para a ferramenta '{nome}'."
                )

    # Executar a função capturando possíveis exceções
    try:
        resultado = funcao(**parametros)
        return ResultadoExecucao(
            sucesso=True,
            resultado=resultado
        )
    except TypeError as erro_tipo:
        return ResultadoExecucao(
            sucesso=False,
            erro=f"Parâmetros incompatíveis com a ferramenta '{nome}': {erro_tipo}"
        )
    except Exception as erro_geral:
        return ResultadoExecucao(
            sucesso=False,
            erro=f"Falha na execução da ferramenta '{nome}': {erro_geral}"
        )


# ============================================================================
# 4. TESTES INDIVIDUAIS
# ============================================================================

if __name__ == "__main__":
    import json

    print("=== TESTE INDIVIDUAL DAS FERRAMENTAS MOCKADAS ===\n")

    # Teste 1: Enviar Notificação
    print("1. Testando 'enviar_notificacao':")
    res1 = executar_ferramenta(
        "enviar_notificacao",
        {
            "mensagem": "Você atingiu 75 minutos no Instagram. Que tal fazer uma pausa de 10 minutos?",
            "prioridade": "alta",
            "aplicativo": "Instagram"
        }
    )
    print(f"Sucesso: {res1.sucesso}")
    print(f"Resultado:\n{json.dumps(res1.resultado, indent=2, ensure_ascii=False)}\n")

    # Teste 2: Consultar Tarefas
    print("2. Testando 'consultar_tarefas':")
    res2 = executar_ferramenta("consultar_tarefas", {"categoria": "estudo"})
    print(f"Sucesso: {res2.sucesso}")
    print(f"Resultado:\n{json.dumps(res2.resultado, indent=2, ensure_ascii=False)}\n")

    # Teste 3: Consultar Histórico
    print("3. Testando 'consultar_historico':")
    res3 = executar_ferramenta("consultar_historico", {"aplicativo": "Instagram", "dias": 7})
    print(f"Sucesso: {res3.sucesso}")
    print(f"Resultado:\n{json.dumps(res3.resultado, indent=2, ensure_ascii=False)}\n")

    # Teste 4: Cenário de Erro - Ferramenta Inexistente
    print("4. Testando chamada de ferramenta inexistente:")
    res4 = executar_ferramenta("bloquear_celular", {})
    print(f"Sucesso: {res4.sucesso}")
    print(f"Erro capturado: {res4.erro}\n")

    # Teste 5: Cenário de Erro - Parâmetro Obrigatório Ausente
    print("5. Testando parâmetro obrigatório ausente:")
    res5 = executar_ferramenta("consultar_historico", {})
    print(f"Sucesso: {res5.sucesso}")
    print(f"Erro capturado: {res5.erro}\n")
