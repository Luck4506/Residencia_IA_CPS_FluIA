"""Acompanha arquivos no disco sem precisar de chat ou de conexão com um LLM."""

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import time

from agente import (
    ARQUIVO_CONFIGURACAO, ARQUIVO_USO,
    avaliar_foco, ler_configuracao, ler_uso,
)


def imprimir_evento(evento: dict):
    # Saída inicial: terminal. Pode ser substituída por notificações ou outro agente.
    print(json.dumps(evento, ensure_ascii=False), flush=True)


class MonitorFoco:
    def __init__(self, configuracao=ARQUIVO_CONFIGURACAO, uso=ARQUIVO_USO,
                 emitir=imprimir_evento):
        self.configuracao = Path(configuracao).resolve()
        self.uso = Path(uso).resolve()
        self.emitir = emitir
        self.alertou = False

    def verificar(self):
        # Os DOIS arquivos são relidos em toda consulta, mesmo se não houve conversa.
        configuracao = ler_configuracao(self.configuracao)
        uso = ler_uso(self.uso)
        resultado = avaliar_foco(configuracao, uso)
        horario = datetime.now().astimezone().isoformat(timespec="seconds")

        self.emitir({
            "tipo": "leitura",
            "horario": horario,
            "arquivo_configuracao": str(self.configuracao),
            "arquivo_uso": str(self.uso),
            "configuracao_lida": configuracao,
            "uso_lido": uso,
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
    parser.add_argument("--configuracao", type=Path, default=ARQUIVO_CONFIGURACAO)
    parser.add_argument("--uso", type=Path, default=ARQUIVO_USO)
    args = parser.parse_args()
    if not math.isfinite(args.intervalo) or args.intervalo <= 0:
        parser.error("O intervalo deve ser um número positivo e finito.")

    monitor = MonitorFoco(args.configuracao, args.uso)
    print("Monitor ativo. Edite e salve os arquivos. Ctrl+C encerra.", flush=True)
    try:
        while True:
            try:
                monitor.verificar()
            except (OSError, ValueError) as erro:
                # Um editor pode deixar um JSON incompleto durante o salvamento.
                # Não interpreta a falha como zero uso nem apaga os arquivos.
                imprimir_evento({
                    "tipo": "erro_leitura",
                    "horario": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "mensagem": str(erro),
                    "acao": "Sem avaliação neste ciclo; tentará novamente na próxima leitura.",
                })
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nMonitor encerrado.", flush=True)


if __name__ == "__main__":
    main()
