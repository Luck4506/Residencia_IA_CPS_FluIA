from queue import Queue
from threading import Event

from test_monitor import arquivos, escrever
from chat import AlertasChat


def test_avisa_sem_pergunta_e_incorpora_no_historico(arquivos):
    config, uso = arquivos
    exibidos = Queue()
    lido = Event()
    chat = AlertasChat(exibidos.put, config, uso, intervalo=0.02)
    receber = chat.monitor.emitir

    def observar(evento):
        receber(evento)
        if evento['tipo'] == 'leitura':
            lido.set()

    chat.monitor.emitir = observar
    chat.iniciar()
    try:
        assert lido.wait(3)
        assert exibidos.empty()
        escrever(uso, {'Docs': 20, 'Instagram': 18})
        antes = (config.read_bytes(), uso.read_bytes())
        texto = exibidos.get(timeout=3)
        assert '18 min' in texto and '15 min' in texto
        assert 'Estudar Python' in texto
        historico = []
        chat.incorporar(historico)
        assert historico[0].type == 'ai'
        assert historico[0].content == texto
        chat.incorporar(historico)
        assert len(historico) == 1
        lido.clear()
        assert lido.wait(3)
        assert exibidos.empty()
        assert (config.read_bytes(), uso.read_bytes()) == antes
    finally:
        chat.fechar()
    assert not chat.thread.is_alive()


def test_recupera_erro_de_arquivo_sem_encerrar_chat(arquivos):
    config, uso = arquivos
    uso.write_text('{')
    exibidos = Queue()
    chat = AlertasChat(exibidos.put, config, uso, intervalo=0.02)
    chat.iniciar()
    try:
        assert 'Não consegui ler' in exibidos.get(timeout=3)
        escrever(uso, {'Instagram': 18})
        assert '18 min' in exibidos.get(timeout=3)
    finally:
        chat.fechar()
