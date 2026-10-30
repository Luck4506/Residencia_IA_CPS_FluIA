import json
from pathlib import Path
import sys
from threading import Event

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import notificacoes
from notificacoes import SaidaNotificacoes
from monitor import MonitorFoco


def arquivos(tmp_path):
    config, uso = tmp_path/'config.json', tmp_path/'uso.json'
    config.write_text(json.dumps({'objetivo':'Estudar Python', 'inicio':'2026-10-29T14:00:00-03:00',
                                 'fim':'2026-10-29T15:00:00-03:00', 'limite_distracao':10, 'apps_de_foco':['Docs']}))
    uso.write_text(json.dumps({'inicio':'2026-10-29T14:00:00-03:00', 'atualizado_em':'2026-10-29T14:35:00-03:00',
                              'minutos_por_app':{'Instagram':12}}))
    return config, uso


def test_monitor_notifica_uma_vez_sem_chat_e_sem_mudar_arquivos(tmp_path):
    config, uso = arquivos(tmp_path)
    antes = config.read_bytes(), uso.read_bytes()
    recebidas, logs = [], []
    pronto = Event()
    def registrar(evento):
        logs.append(evento)
        pronto.set()
    saida = SaidaNotificacoes(lambda e: None, usar_ia=False,
                             enviar=lambda *args: recebidas.append(args), registrar=registrar)
    try:
        monitor = MonitorFoco(config, uso, saida)
        monitor.verificar()
        assert pronto.wait(3)
        for _ in range(3):
            monitor.verificar()
        assert len(recebidas) == 1
        assert '12 min' in recebidas[0][1] and '10 min' in recebidas[0][1]
        assert logs[-1]['tipo'] == 'notificacao_solicitada'
        assert (config.read_bytes(), uso.read_bytes()) == antes
    finally:
        saida.fechar()


def test_modelo_indisponivel_usa_mensagem_padrao(tmp_path):
    config, uso = arquivos(tmp_path)
    pronto = Event()
    recebidas, logs = [], []
    def indisponivel(evento):
        raise ConnectionError('Ollama indisponível')
    def enviar(*args):
        recebidas.append(args)
        pronto.set()
    saida = SaidaNotificacoes(lambda e: None, enviar=enviar, redigir=indisponivel, registrar=logs.append)
    try:
        MonitorFoco(config, uso, saida).verificar()
        assert pronto.wait(3)
        assert 'retomar?' in recebidas[0][1]
        assert logs[0]['tipo'] == 'fallback_mensagem'
    finally:
        saida.fechar()


def test_leituras_continuam_e_alerta_antigo_e_descartado(tmp_path):
    config, uso = arquivos(tmp_path)
    gerando, liberar, terminou = Event(), Event(), Event()
    recebidas, logs = [], []
    def lento(evento):
        gerando.set()
        assert liberar.wait(3)
        return 'Abra seu exercício de Python.'
    def registrar(evento):
        logs.append(evento)
        terminou.set()
    saida = SaidaNotificacoes(lambda e: None, enviar=lambda *a: recebidas.append(a), redigir=lento, registrar=registrar)
    try:
        monitor = MonitorFoco(config, uso, saida)
        monitor.verificar()
        assert gerando.wait(3)
        dados = json.loads(config.read_text())
        dados['limite_distracao'] = 20
        config.write_text(json.dumps(dados))
        assert not monitor.verificar()['ultrapassou']
        liberar.set()
        assert terminou.wait(3)
        assert not recebidas
        assert logs[-1]['tipo'] == 'notificacao_descartada'
    finally:
        liberar.set()
        saida.fechar()


def test_falha_nativa_e_registrada(tmp_path):
    config, uso = arquivos(tmp_path)
    pronto = Event()
    logs = []
    def falha(*args):
        raise OSError('Não foi possível enviar')
    def registrar(e):
        logs.append(e)
        pronto.set()
    saida = SaidaNotificacoes(lambda e: None, usar_ia=False, enviar=falha, registrar=registrar)
    try:
        MonitorFoco(config, uso, saida).verificar()
        assert pronto.wait(3)
        assert logs[-1]['tipo'] == 'erro_notificacao'
    finally:
        saida.fechar()


def test_texto_e_argumento_nunca_codigo_applescript(monkeypatch):
    chamadas = []
    monkeypatch.setattr(notificacoes.sys, 'platform', 'darwin')
    monkeypatch.setattr(notificacoes.subprocess, 'run', lambda *a, **k: chamadas.append((a,k)))
    texto = 'Estudar "Python"; $(echo teste)\nNova linha'
    notificacoes.notificar_macos('Foco', texto)
    argumentos = chamadas[0][0][0]
    assert argumentos[-1] == texto
    assert texto not in argumentos[2]
    assert chamadas[0][1].get('shell', False) is False
