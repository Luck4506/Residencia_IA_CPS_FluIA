"""Conversa no terminal com monitoramento independente da resposta do modelo."""

from queue import Empty, Queue
import shutil
from threading import Event, Thread

from langchain_core.messages import AIMessage, ToolMessage
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from agente import (
    ARQUIVO_CONFIGURACAO, ARQUIVO_USO, criar_agente, formatar_fala_agente,
    imprimir_apoio, ler_configuracao, saida_colorida,
)
from monitor import MonitorFoco


class AlertasChat:
    def __init__(self, mostrar, configuracao=ARQUIVO_CONFIGURACAO,
                 uso=ARQUIVO_USO, intervalo=1):
        self.mostrar = mostrar
        self.intervalo = intervalo
        self.pendentes = Queue()
        self.parar = Event()
        self.monitor = MonitorFoco(configuracao, uso, emitir=self._receber)
        self.thread = Thread(target=self._acompanhar, daemon=True)

    def _receber(self, evento):
        if evento['tipo'] != 'alerta':
            return
        texto = (
            f"Hey, tá passando da hora! Seu foco era: {evento['objetivo']}. "
            f"Até {evento['atualizado_em']}, você acumulou "
            f"{evento['minutos_distraidos']:g} min fora do foco "
            f"(limite: {evento['limite_distracao']:g} min). Quer ajuda para retomar?"
        )
        self.pendentes.put(AIMessage(content=texto))
        self.mostrar(texto)

    def _acompanhar(self):
        ultimo_erro = None
        while not self.parar.is_set():
            try:
                self.monitor.verificar()
                ultimo_erro = None
            except (OSError, ValueError) as erro:
                # Não repete o mesmo erro a cada segundo durante uma edição.
                if str(erro) != ultimo_erro:
                    self.mostrar(f"Não consegui ler os dados de foco: {erro}. Vou tentar novamente.")
                    ultimo_erro = str(erro)
            self.parar.wait(self.intervalo)

    def incorporar(self, mensagens):
        # Só a thread da conversa modifica o histórico, inclusive durante invoke.
        while True:
            try:
                mensagens.append(self.pendentes.get_nowait())
            except Empty:
                return

    def iniciar(self):
        self.thread.start()

    def fechar(self):
        self.parar.set()
        self.thread.join()


def main():
    agente = criar_agente()
    mensagens = []
    colorir = saida_colorida()
    print('Configuração carregada:', ler_configuracao())
    print('Alterações serão salvas em:', ARQUIVO_CONFIGURACAO)
    print('Converse com o agente. Digite /sair para encerrar.')
    print('Monitoramento do chat ativo: os arquivos serão relidos a cada segundo.')

    def mostrar(texto):
        largura = shutil.get_terminal_size(fallback=(80, 24)).columns
        print(formatar_fala_agente(texto, largura, colorir), flush=True)

    sessao = PromptSession()
    alertas = AlertasChat(mostrar)
    # Redesenha o prompt após mensagens espontâneas, preservando o texto digitado.
    with patch_stdout(raw=True):
        alertas.iniciar()
        try:
            while True:
                try:
                    texto = sessao.prompt('Você: ').strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if texto == '/sair':
                    break
                if not texto:
                    continue
                alertas.incorporar(mensagens)
                entrada = mensagens + [{'role': 'user', 'content': texto}]
                imprimir_apoio('Consultando o modelo local...', colorir)
                try:
                    resultado = agente.invoke({'messages': entrada}, config={'recursion_limit': 12})
                except Exception as erro:
                    print(f'Não foi possível responder: {erro}')
                    print('Confira se o Ollama está aberto e se baixou qwen2.5:3b.')
                    continue
                for mensagem in resultado['messages'][len(entrada):]:
                    if isinstance(mensagem, ToolMessage):
                        imprimir_apoio(f'[Ferramenta executada: {mensagem.name}]', colorir)
                mensagens = resultado['messages']
                mostrar(mensagens[-1].content)
                alertas.incorporar(mensagens)
        finally:
            alertas.fechar()


if __name__ == '__main__':
    main()
