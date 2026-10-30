"""Acompanha arquivos no disco sem precisar de chat ou de conexão com um LLM."""

import argparse
from datetime import datetime
import json
import math
import os
from pathlib import Path
import sys
import time

from agente import (
    ARQUIVO_CONFIGURACAO, ARQUIVO_USO,
    avaliar_foco, instante, ler_configuracao, ler_uso,
)

RESET = "\033[0m"
# Branco de verdade sobre fundo escuro. A paleta do terminal não troca essa letra por preta.
COR_DENTRO = "\033[38;2;255;255;255;48;2;15;122;50m"   # branco sobre verde
COR_FORA = "\033[38;2;255;255;255;48;2;176;32;32m"     # branco sobre vermelho
COR_ERRO = "\033[38;2;255;255;255;48;2;140;80;0m"      # branco sobre âmbar
COR_ROTULO = "\033[38;2;0;0;0;48;2;255;255;255m"       # preto sobre branco


def pintar(texto: str, codigo: str, colorir: bool) -> str:
    if not colorir:
        return texto
    return f"{codigo} {texto} {RESET}"


def formatar_evento(evento: dict, formato: str = "verboso", colorir: bool = False) -> str | None:
    if formato == "verboso":
        return json.dumps(evento, ensure_ascii=False)
    if formato != "conciso":
        raise ValueError(f"Formato desconhecido: {formato}")
    # A leitura já traz o estado. O alerta verboso repetiria a mesma linha.
    if evento.get("tipo") == "alerta":
        return None
    horario = evento["horario"]
    if evento.get("tipo") == "erro_leitura":
        valor = pintar("erro", COR_ERRO, colorir)
    else:
        ultrapassou = bool(evento["ultrapassou"])
        valor = pintar(
            "true" if ultrapassou else "false",
            COR_FORA if ultrapassou else COR_DENTRO,
            colorir,
        )
    rotulo = pintar("ultrapassou", COR_ROTULO, colorir)
    return f"{{ {horario} | {rotulo}: {valor} }}"


def saida_colorida() -> bool:
    # Saída redirecionada não é terminal. NO_COLOR não vazio também desliga a cor.
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def criar_impressora(formato: str = "verboso", colorir: bool | None = None):
    if colorir is None:
        colorir = saida_colorida()

    def imprimir(evento: dict):
        linha = formatar_evento(evento, formato, colorir=colorir)
        if linha is not None:
            print(linha, flush=True)

    return imprimir


def imprimir_evento(evento: dict):
    # Saída inicial: terminal. Pode ser substituída por notificações ou outro agente.
    criar_impressora()(evento)


class MonitorFoco:
    def __init__(self, configuracao=ARQUIVO_CONFIGURACAO, uso=ARQUIVO_USO,
                 emitir=imprimir_evento):
        self.configuracao = Path(configuracao).resolve()
        self.uso = Path(uso).resolve()
        self.emitir = emitir
        self.alertou = False
        self.sessao = None

    def verificar(self):
        # Os DOIS arquivos são relidos em toda consulta, mesmo se não houve conversa.
        configuracao = ler_configuracao(self.configuracao)
        uso = ler_uso(self.uso)
        resultado = avaliar_foco(configuracao, uso)
        sessao = (instante(configuracao["inicio"]), instante(configuracao["fim"]))
        if sessao != self.sessao:
            self.alertou = False
            self.sessao = sessao
        horario = datetime.now().astimezone().isoformat(timespec="seconds")

        self.emitir({
            "tipo": "leitura",
            "horario": horario,
            "arquivo_configuracao": str(self.configuracao),
            "arquivo_uso": str(self.uso),
            "configuracao_lida": configuracao,
            "uso_lido": uso,
            "atualizado_em": resultado["atualizado_em"],
            "duracao_sessao_minutos": resultado["duracao_sessao_minutos"],
            "minutos_excedidos": resultado["minutos_excedidos"],
            "minutos_distraidos": resultado["minutos_distraidos"],
            "ultrapassou": resultado["ultrapassou"],
        })

        if resultado["ultrapassou"] and not self.alertou:
            self.emitir({
                "tipo": "alerta",
                "horario": horario,
                "motivo": "Uso fora do foco maior que o limite salvo",
                **resultado,
            })
            self.alertou = True
        elif not resultado["ultrapassou"]:
            # Uma nova ultrapassagem poderá alertar depois que voltar ao limite.
            self.alertou = False
        return resultado


def main():
    parser = argparse.ArgumentParser(description="Monitor de arquivos de foco")
    parser.add_argument("--intervalo", type=float, default=5, help="Segundos entre leituras")
    parser.add_argument("--formato", choices=("verboso", "conciso"), default="verboso",
                        help="verboso: JSON completo; conciso: horário e se ultrapassou")
    parser.add_argument("--configuracao", type=Path, default=ARQUIVO_CONFIGURACAO)
    parser.add_argument("--uso", type=Path, default=ARQUIVO_USO)
    parser.add_argument("--notificar", action="store_true", help="Envia alerta como notificação do macOS")
    parser.add_argument("--sem-ia", action="store_true", help="Usa mensagem fixa na notificação, sem Ollama")
    args = parser.parse_args()
    if args.notificar and sys.platform != "darwin":
        parser.error("As notificações nativas desta etapa exigem macOS.")
    if not math.isfinite(args.intervalo) or args.intervalo <= 0:
        parser.error("O intervalo deve ser um número positivo e finito.")

    imprimir = criar_impressora(args.formato)
    saida = None
    if args.notificar:
        from notificacoes import SaidaNotificacoes
        saida = SaidaNotificacoes(imprimir, usar_ia=not args.sem_ia)
    monitor = MonitorFoco(args.configuracao, args.uso, emitir=saida or imprimir)
    print("Monitor ativo. Edite e salve os arquivos. Ctrl+C encerra.", flush=True)
    try:
        while True:
            try:
                monitor.verificar()
            except (OSError, ValueError) as erro:
                # Um editor pode deixar um JSON incompleto durante o salvamento.
                # Não interpreta a falha como zero uso nem apaga os arquivos.
                (saida or imprimir)({
                    "tipo": "erro_leitura",
                    "horario": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "mensagem": str(erro),
                    "acao": "Sem avaliação neste ciclo; tentará novamente na próxima leitura.",
                })
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nMonitor encerrado.", flush=True)
    finally:
        if saida is not None:
            saida.fechar()


if __name__ == "__main__":
    main()
