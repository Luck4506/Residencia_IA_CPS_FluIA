"""Passo 3: configuração salva em JSON, ferramentas LangChain e modelo local."""

import json
from datetime import datetime
import math
import os
import sys
import textwrap
from pathlib import Path
from tempfile import NamedTemporaryFile

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_ollama import ChatOllama


# Caminhos relativos ao script, não à pasta do terminal.
ARQUIVO_CONFIGURACAO = Path(__file__).resolve().with_name("configuracao.json")
ARQUIVO_USO = Path(__file__).resolve().with_name("uso.json")

RESET = "\033[0m"
# Branco sobre cinza escuro: o bloco da resposta se separa do que você digitou.
FUNDO_AGENTE = "\033[38;2;255;255;255;48;2;58;58;58m"
TEXTO_APOIO = "\033[90m"


def saida_colorida() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def formatar_fala_agente(texto: str, largura: int = 80, colorir: bool = False) -> str:
    if not colorir:
        return f"Agente: {texto}"
    largura = max(20, largura)
    linhas = [" Agente"]
    for paragrafo in str(texto).splitlines() or [""]:
        if paragrafo.strip():
            linhas.extend(
                f" {linha}" for linha in textwrap.wrap(paragrafo, width=largura - 2)
            )
        else:
            linhas.append("")
    bloco = "\n".join(f"{FUNDO_AGENTE}{linha.ljust(largura)}{RESET}" for linha in linhas)
    return f"\n{bloco}\n"


def imprimir_apoio(texto: str, colorir: bool):
    if colorir:
        print(f"{TEXTO_APOIO}{texto}{RESET}", flush=True)
    else:
        print(texto, flush=True)


def instante(valor: str) -> datetime:
    """Exige data/hora ISO-8601 com fuso, para comparar instantes sem ambiguidade."""
    if not isinstance(valor, str):
        raise ValueError("O horário deve ser uma string ISO-8601 com fuso.")
    data = datetime.fromisoformat(valor)
    if data.tzinfo is None or data.utcoffset() is None:
        raise ValueError("Informe o fuso no horário, por exemplo -03:00.")
    return data


def minutos_entre(inicio: str, fim: str) -> float:
    return (instante(fim).timestamp() - instante(inicio).timestamp()) / 60


def chave_app(nome: str) -> str:
    """Compara nomes sem distinguir maiúsculas e espaços nas extremidades."""
    return nome.strip().casefold()


class Configuracao(BaseModel):
    """Valida os dados antes de ler ou salvar a configuração."""
    model_config = ConfigDict(extra="forbid", strict=True)
    objetivo: str = Field(min_length=1)
    inicio: str
    fim: str
    limite_distracao: int = Field(ge=0)
    apps_de_foco: list[str]

    @model_validator(mode="after")
    def janela_valida(self):
        duracao = minutos_entre(self.inicio, self.fim)
        if duracao <= 0:
            raise ValueError("O fim da sessão deve ser posterior ao início.")
        if self.limite_distracao > duracao:
            raise ValueError("O limite de distração não pode superar a duração da sessão.")
        return self

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
        unicos = {}
        for nome in valores:
            # Preserva a grafia da primeira ocorrência para exibição.
            unicos.setdefault(chave_app(nome), nome.strip())
        return list(unicos.values())


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
    inicio: str | None = None,
    fim: str | None = None,
) -> dict:
    """Salva apenas os campos que o usuário pediu para mudar no arquivo JSON.

    Campos omitidos ou nulos são preservados. Uma lista vazia de apps significa
    que nenhum app é relacionado. A tolerância é em minutos e deve caber na duração da sessão.

    Args:
        inicio: Novo início ISO-8601 com data e fuso; omita para preservar.
        fim: Novo fim ISO-8601 com data e fuso; omita para preservar.
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
            "inicio": inicio,
            "fim": fim,
        }.items()
        if valor is not None
    }
    return salvar_configuracao(ler_configuracao() | alteracoes)


@tool
def adicionar_app_de_foco(app: str) -> dict:
    """Adiciona um app permitido/uma exceção sem remover os apps de foco existentes.

    Args:
        app: Nome do aplicativo a adicionar, por exemplo YouTube.
    """
    dados = ler_configuracao()
    dados["apps_de_foco"] = dados["apps_de_foco"] + [app]
    return salvar_configuracao(dados)


def ler_uso(caminho: Path | None = None) -> dict:
    """Lê totais acumulados por app. Não escreve nem incrementa esses valores."""
    dados = json.loads((caminho or ARQUIVO_USO).read_text(encoding="utf-8"))
    validar_uso(dados)
    return dados


def validar_uso(dados: dict):
    campos = {"inicio", "atualizado_em", "minutos_por_app"}
    if not isinstance(dados, dict) or set(dados) != campos:
        raise ValueError("uso.json exige inicio, atualizado_em e minutos_por_app.")
    decorrido = minutos_entre(dados["inicio"], dados["atualizado_em"])
    if decorrido < 0:
        raise ValueError("atualizado_em não pode ser anterior ao início da coleta.")
    if not isinstance(dados["minutos_por_app"], dict):
        raise ValueError("minutos_por_app deve ser um objeto com app e minutos.")
    for app, minutos in dados["minutos_por_app"].items():
        if not isinstance(app, str) or not app.strip() or type(minutos) not in (int, float):
            raise ValueError("Cada app precisa de nome e um número de minutos.")
        if not math.isfinite(minutos) or minutos < 0:
            raise ValueError("Os totais devem ser números finitos e não negativos.")
        if minutos > decorrido + 1e-9:
            raise ValueError(f"O uso de {app} supera os {decorrido:g} minutos medidos.")


def avaliar_foco(configuracao: dict, uso: dict) -> dict:
    """Calcula a partir de uma leitura; não soma snapshots repetidos."""
    configuracao = Configuracao.model_validate(configuracao).model_dump()
    validar_uso(uso)
    if instante(uso["inicio"]) != instante(configuracao["inicio"]):
        raise ValueError("O início da coleta não corresponde ao início da sessão configurada.")
    if instante(uso["atualizado_em"]) > instante(configuracao["fim"]):
        raise ValueError("A coleta ultrapassa o fim da sessão; totais não podem ser recortados por horário.")
    objetivo = configuracao["objetivo"]
    limite_distracao = configuracao["limite_distracao"]
    apps_de_foco = {chave_app(app) for app in configuracao["apps_de_foco"]}

    minutos_distraidos = sum(
        minutos
        for app, minutos in uso["minutos_por_app"].items()
        if chave_app(app) not in apps_de_foco
    )
    ultrapassou = minutos_distraidos > limite_distracao

    return {
        "objetivo": objetivo,
        "inicio": configuracao["inicio"],
        "fim": configuracao["fim"],
        "atualizado_em": uso["atualizado_em"],
        "duracao_sessao_minutos": minutos_entre(configuracao["inicio"], configuracao["fim"]),
        "minutos_medidos": minutos_entre(uso["inicio"], uso["atualizado_em"]),
        "minutos_excedidos": max(0, minutos_distraidos - limite_distracao),
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
        tools=[consultar_configuracao, atualizar_configuracao, adicionar_app_de_foco, verificar_foco],
        system_prompt=(
            "Você ajuda o usuário a retomar seu foco. Responda em português em até três frases. "
            "A configuração está salva em arquivo; nunca use o histórico como fonte dos valores atuais. "
            "Para saber objetivo, tolerância ou apps relacionados, use consultar_configuracao. "
            "Apps permitidos e exceções significam apps_de_foco. "
            "Para adicionar um app, use adicionar_app_de_foco com apenas o nome em app. "
            "Exemplo: 'Adicione YouTube aos apps permitidos' chama adicionar_app_de_foco "
            "com {\"app\": \"YouTube\"}. Essa ferramenta preserva os outros apps automaticamente. "
            "Para adicionar vários, chame essa ferramenta uma vez por app. "
            "Para substituir toda a lista ou mudar outros campos, use atualizar_configuracao passando SOMENTE "
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
            "Os dados são mockados: inicio/fim definem a sessão e atualizado_em é o instante medido. "
            "Relate a avaliação até atualizado_em, nunca afirme que a sessão está ativa no relógio real. "
            "Para alterar horários, obtenha data e fuso; se faltarem, pergunte. "
            "Não altere uso.json: outra coleta pode ser necessária quando a janela mudar. "
            "Sugira um pequeno passo para retomar o objetivo quando houver excesso. "
            "O chat tem um monitor que relê os arquivos a cada segundo e mostra avisos de excesso automaticamente. "
            "Esses avisos usam dados mockados, não coleta real do dispositivo. "
            "Você não pode agendar lembretes nem bloquear apps. Não ofereça essas ações."
        ),
    ).with_config(max_concurrency=1)  # Evita ler enquanto a atualização ainda está gravando.


if __name__ == "__main__":
    from chat import main
    main()
