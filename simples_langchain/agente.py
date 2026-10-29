"""Passo 3: configuração salva em JSON, ferramentas LangChain e modelo local."""

import json
import math
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel, ConfigDict, Field, field_validator
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import ToolMessage
from langchain_ollama import ChatOllama


# Caminhos relativos ao script, não à pasta do terminal.
ARQUIVO_CONFIGURACAO = Path(__file__).resolve().with_name("configuracao.json")
ARQUIVO_USO = Path(__file__).resolve().with_name("uso.json")


class Configuracao(BaseModel):
    """Valida os dados antes de ler ou salvar a configuração."""
    model_config = ConfigDict(extra="forbid", strict=True)
    objetivo: str = Field(min_length=1)
    limite_distracao: int = Field(ge=0, le=60)
    apps_de_foco: list[str]

    @field_validator("objetivo")
    @classmethod
    def objetivo_preenchido(cls, valor):
        if not valor.strip():
            raise ValueError("Informe um objetivo.")
        return valor.strip()

    @field_validator("apps_de_foco")
    @classmethod
    def nomes_preenchidos(cls, valores):
        if any(not nome.strip() for nome in valores):
            raise ValueError("Os nomes dos apps não podem estar vazios.")
        return list(dict.fromkeys(nome.strip() for nome in valores))


def ler_configuracao(caminho: Path | None = None) -> dict:
    dados = json.loads((caminho or ARQUIVO_CONFIGURACAO).read_text(encoding="utf-8"))
    return Configuracao.model_validate(dados).model_dump()


def salvar_configuracao(dados: dict) -> dict:
    dados = Configuracao.model_validate(dados).model_dump()
    # Escreve primeiro num temporário: uma escrita incompleta não apaga o JSON atual.
    temporario = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=ARQUIVO_CONFIGURACAO.parent,
                                suffix=".tmp", delete=False) as arquivo:
            temporario = Path(arquivo.name)
            json.dump(dados, arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
        temporario.replace(ARQUIVO_CONFIGURACAO)
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)
    return dados


@tool
def consultar_configuracao() -> dict:
    """Lê do arquivo o objetivo, a tolerância e os aplicativos relacionados atuais."""
    return ler_configuracao()


@tool
def atualizar_configuracao(
    objetivo: str | None = None,
    limite_distracao: int | None = None,
    apps_de_foco: list[str] | None = None,
) -> dict:
    """Salva apenas os campos que o usuário pediu para mudar no arquivo JSON.

    Campos omitidos ou nulos são preservados. Uma lista vazia de apps significa
    que nenhum app é relacionado. A tolerância é em minutos, entre 0 e 60.

    Args:
        objetivo: Novo objetivo, apenas se solicitado; caso contrário omita ou use null.
        limite_distracao: Novo limite em minutos; caso contrário omita ou use null.
        apps_de_foco: Nova lista, APENAS se o usuário pediu para mudar os apps.
            Use null ou omita para preservar. [] APAGA a lista, não é valor padrão.
    """
    alteracoes = {
        nome: valor
        for nome, valor in {
            "objetivo": objetivo,
            "limite_distracao": limite_distracao,
            "apps_de_foco": apps_de_foco,
        }.items()
        if valor is not None
    }
    return salvar_configuracao(ler_configuracao() | alteracoes)


def ler_uso(caminho: Path | None = None) -> dict:
    """Lê totais acumulados por app. Não escreve nem incrementa esses valores."""
    dados = json.loads((caminho or ARQUIVO_USO).read_text(encoding="utf-8"))
    if not isinstance(dados, dict):
        raise ValueError("uso.json deve conter um objeto com app e minutos acumulados.")
    for app, minutos in dados.items():
        if not app.strip() or type(minutos) not in (int, float):
            raise ValueError("Cada app precisa de nome e um número de minutos.")
        if not math.isfinite(minutos) or not 0 <= minutos <= 60:
            raise ValueError("Cada total deve estar entre 0 e 60 minutos.")
    return dados


def avaliar_foco(configuracao: dict, uso: dict) -> dict:
    """Calcula a partir de uma leitura; não soma snapshots repetidos."""
    objetivo = configuracao["objetivo"]
    limite_distracao = configuracao["limite_distracao"]
    apps_de_foco = configuracao["apps_de_foco"]

    minutos_distraidos = sum(
        minutos
        for app, minutos in uso.items()
        if app not in apps_de_foco
    )
    ultrapassou = minutos_distraidos > limite_distracao

    return {
        "objetivo": objetivo,
        "minutos_distraidos": minutos_distraidos,
        "limite_distracao": limite_distracao,
        "ultrapassou": ultrapassou,
        "mensagem": (
            f"Hey, tá passando da hora! Seu foco era: {objetivo}. Quer ajuda para retomar?"
            if ultrapassou else "Você está dentro do limite de distração."
        ),
    }


@tool
def verificar_foco() -> dict:
    """Relê configuracao.json e uso.json e verifica se o limite foi ultrapassado."""
    return avaliar_foco(ler_configuracao(), ler_uso())


def criar_agente():
    # O Ollama executa o modelo no seu computador, sem chave de API.
    modelo = ChatOllama(
        model="qwen2.5:3b",
        base_url="http://127.0.0.1:11434",
        temperature=0,
        keep_alive="30m",  # Evita recarregar o modelo entre perguntas próximas.
        num_ctx=8192,
        client_kwargs={"timeout": 180},
    )

    return create_agent(
        model=modelo,
        tools=[consultar_configuracao, atualizar_configuracao, verificar_foco],
        system_prompt=(
            "Você ajuda o usuário a retomar seu foco. Responda em português em até três frases. "
            "A configuração está salva em arquivo; nunca use o histórico como fonte dos valores atuais. "
            "Para saber objetivo, tolerância ou apps relacionados, use consultar_configuracao. "
            "Quando o usuário pedir uma mudança, use atualizar_configuracao passando SOMENTE "
            "os campos pedidos. Campos omitidos são preservados automaticamente. "
            "Exemplo: 'mude o limite para 30' chama atualizar_configuracao "
            "com apenas {\"limite_distracao\": 30}. Não envie apps_de_foco nesse caso. "
            "Nunca envie apps_de_foco=[] sem um pedido explícito para remover todos os apps. "
            "Se precisar preencher campos não solicitados, use null, nunca [] ou valores inventados. "
            "Só confirme uma alteração depois que a ferramenta salvar com sucesso. "
            "Se houver erro, explique que a operação não foi concluída, sem inventar resultados. "
            "Se o pedido for ambíguo, pergunte antes de alterar. "
            "Para perguntas como 'Como está meu foco?', use verificar_foco sem argumentos. "
            "Se o usuário pedir para alterar e verificar, primeiro salve, depois verifique. "
            "Use uma ferramenta por vez e aguarde seu resultado antes da próxima. "
            "Responda com o uso e o limite retornados pela ferramenta. "
            "Os dados de uso são mockados de uma janela de 60 minutos, sem monitoramento real. "
            "Sugira um pequeno passo para retomar o objetivo quando houver excesso. "
            "Você não pode agendar lembretes nem bloquear apps. Não ofereça essas ações."
        ),
    ).with_config(max_concurrency=1)  # Evita ler enquanto a atualização ainda está gravando.


if __name__ == "__main__":
    agente = criar_agente()
    mensagens = []  # Histórico apenas desta execução; não é salvo em disco.
    configuracao = ler_configuracao()
    print("Configuração carregada:", configuracao)
    print("Alterações serão salvas em:", ARQUIVO_CONFIGURACAO)
    print("Converse com o agente. Digite /sair para encerrar.")

    while True:
        try:
            texto = input("Você: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if texto == "/sair":
            break
        if not texto:
            continue

        entrada = mensagens + [{"role": "user", "content": texto}]
        print("Consultando o modelo local...", flush=True)
        try:
            resultado = agente.invoke(
                {"messages": entrada},
                config={"recursion_limit": 12},
            )
        except Exception as erro:
            print(f"Não foi possível responder: {erro}")
            print("Confira se o Ollama está aberto e se baixou qwen2.5:3b.")
            continue

        # Mostra quando a ferramenta foi realmente executada, para facilitar o estudo.
        for mensagem in resultado["messages"][len(entrada):]:
            if isinstance(mensagem, ToolMessage):
                print(f"[Ferramenta executada: {mensagem.name}]")

        mensagens = resultado["messages"]
        print("Agente:", mensagens[-1].content)
