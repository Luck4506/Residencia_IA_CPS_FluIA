import json
from pathlib import Path
from queue import Queue, Empty
import signal
import subprocess
import sys
from threading import Thread
from time import monotonic

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agente import ler_uso
from monitor import MonitorFoco


def escrever(caminho, dados):
    caminho.write_text(json.dumps(dados), encoding='utf-8')


@pytest.fixture
def arquivos(tmp_path):
    config = tmp_path / 'configuracao.json'
    uso = tmp_path / 'uso.json'
    escrever(config, {'objetivo': 'Estudar Python', 'limite_distracao': 15, 'apps_de_foco': ['Docs']})
    escrever(uso, {'Docs': 20, 'Instagram': 10, 'YouTube': 3})
    return config, uso


def test_edicao_no_disco_dispara_sem_acumular_ou_escrever(arquivos):
    config, uso = arquivos
    eventos = []
    monitor = MonitorFoco(config, uso, eventos.append)
    assert monitor.verificar()['minutos_distraidos'] == 13
    assert monitor.verificar()['minutos_distraidos'] == 13
    escrever(uso, {'Docs': 20, 'Instagram': 10, 'YouTube': 8})
    antes = (config.read_bytes(), uso.read_bytes())
    assert monitor.verificar()['minutos_distraidos'] == 18
    monitor.verificar()
    alertas = [e for e in eventos if e['tipo'] == 'alerta']
    assert len(alertas) == 1
    assert alertas[0]['minutos_distraidos'] == 18
    assert eventos[-1]['uso_lido']['YouTube'] == 8
    assert (config.read_bytes(), uso.read_bytes()) == antes


def test_configuracao_editada_tambem_e_relida(arquivos):
    config, uso = arquivos
    eventos = []
    monitor = MonitorFoco(config, uso, eventos.append)
    monitor.verificar()
    dados = json.loads(config.read_text())
    dados['limite_distracao'] = 10
    escrever(config, dados)
    assert monitor.verificar()['ultrapassou']
    assert len([e for e in eventos if e['tipo'] == 'alerta']) == 1
    dados['limite_distracao'] = 13  # Igualdade não é excesso e rearma o monitor.
    escrever(config, dados)
    assert not monitor.verificar()['ultrapassou']
    dados['apps_de_foco'] = []
    escrever(config, dados)
    assert monitor.verificar()['minutos_distraidos'] == 33
    assert len([e for e in eventos if e['tipo'] == 'alerta']) == 2


@pytest.mark.parametrize('conteudo', ['{', 'null', '[]', '{"X": -1}', '{"X": true}', '{"X": "10"}', '{"X": NaN}'])
def test_uso_invalido_nao_emite_alerta(arquivos, conteudo):
    config, uso = arquivos
    uso.write_text(conteudo)
    eventos = []
    with pytest.raises(ValueError):
        MonitorFoco(config, uso, eventos.append).verificar()
    assert not eventos
    assert uso.read_text() == conteudo


def test_falha_temporaria_nao_rearma_alerta(arquivos):
    config, uso = arquivos
    eventos = []
    monitor = MonitorFoco(config, uso, eventos.append)
    escrever(uso, {'Instagram': 18})
    monitor.verificar()
    uso.write_text('{')
    with pytest.raises(ValueError):
        monitor.verificar()
    escrever(uso, {'Instagram': 19})
    monitor.verificar()
    assert len([e for e in eventos if e['tipo'] == 'alerta']) == 1


def test_processo_rodando_observa_edicoes_e_se_recupera(arquivos):
    config, uso = arquivos
    processo = subprocess.Popen(
        [sys.executable, str(ROOT / 'monitor.py'), '--intervalo', '0.1',
         '--configuracao', str(config), '--uso', str(uso)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    linhas = Queue()
    def ler_saida():
        for linha in processo.stdout:
            linhas.put(linha)
    Thread(target=ler_saida, daemon=True).start()

    def aguardar(tipo, **campos):
        limite = monotonic() + 15
        while monotonic() < limite:
            try:
                linha = linhas.get(timeout=max(0.01, limite - monotonic()))
            except Empty:
                break
            try:
                evento = json.loads(linha)
            except ValueError:
                continue
            if evento.get('tipo') == tipo and all(evento.get(k) == v for k, v in campos.items()):
                return evento
        raise AssertionError(f'Não recebeu {tipo}: {campos}')

    try:
        aguardar('leitura', minutos_distraidos=13, ultrapassou=False)
        uso.write_text('{incompleto')
        aguardar('erro_leitura')
        escrever(uso, {'Docs': 20, 'Instagram': 10, 'YouTube': 8})
        evento = aguardar('alerta', minutos_distraidos=18)
        assert evento['limite_distracao'] == 15
        dados = json.loads(config.read_text())
        dados['limite_distracao'] = 30
        escrever(config, dados)
        aguardar('leitura', minutos_distraidos=18, ultrapassou=False)
        assert json.loads(uso.read_text())['YouTube'] == 8
    finally:
        processo.send_signal(signal.SIGINT)
        try:
            processo.wait(timeout=5)
        except subprocess.TimeoutExpired:
            processo.kill()
            processo.wait()
        processo.stdout.close()
