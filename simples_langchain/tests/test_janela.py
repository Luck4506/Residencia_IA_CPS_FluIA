import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agente import Configuracao, avaliar_foco, validar_uso
from monitor import MonitorFoco


def plano(**campos):
    return dict(objetivo='Estudar Python', inicio='2026-10-29T14:00:00-03:00',
                fim='2026-10-29T15:00:00-03:00', limite_distracao=10,
                apps_de_foco=['Docs']) | campos


def uso(**campos):
    return dict(inicio='2026-10-29T14:00:00-03:00', atualizado_em='2026-10-29T14:35:00-03:00',
                minutos_por_app={'Docs': 20, 'Instagram': 12}) | campos


def test_exemplo_do_usuario():
    resultado = avaliar_foco(plano(), uso())
    assert resultado['minutos_distraidos'] == 12
    assert resultado['minutos_excedidos'] == 2
    assert resultado['minutos_medidos'] == 35
    assert resultado['duracao_sessao_minutos'] == 60
    assert resultado['ultrapassou'] is True


def test_sessao_longa_aceita_mais_de_60_minutos():
    resultado = avaliar_foco(
        plano(fim='2026-10-29T17:00:00-03:00', limite_distracao=90),
        uso(atualizado_em='2026-10-29T16:30:00-03:00', minutos_por_app={'Docs': 120, 'Instagram': 20}),
    )
    assert resultado['duracao_sessao_minutos'] == 180
    assert not resultado['ultrapassou']


@pytest.mark.parametrize('mudanca', [
    {'inicio': '2026-10-29T14:00:00'},
    {'fim': '2026-10-29T13:00:00-03:00'},
    {'fim': '2026-10-29T14:00:00-03:00'},
    {'limite_distracao': 61},
])
def test_plano_invalido(mudanca):
    with pytest.raises(ValueError):
        Configuracao.model_validate(plano(**mudanca))


@pytest.mark.parametrize('mudanca', [
    {'inicio': '2026-10-29T13:00:00-03:00'},
    {'atualizado_em': '2026-10-29T15:01:00-03:00'},
    {'atualizado_em': '2026-10-29T13:59:00-03:00'},
    {'atualizado_em': '2026-10-29T14:35:00'},
    {'minutos_por_app': {'Docs': 36}},
    {'minutos_por_app': {'X': -1}},
    {'minutos_por_app': {'X': float('nan')}},
    {'minutos_por_app': {'X': True}},
    {'minutos_por_app': {'X': '12'}},
])
def test_uso_invalido_ou_periodo_incompativel(mudanca):
    with pytest.raises(ValueError):
        avaliar_foco(plano(), uso(**mudanca))


def test_fusos_equivalentes_e_limites_inclusivos():
    inicio = uso(inicio='2026-10-29T17:00:00+00:00', atualizado_em='2026-10-29T17:00:00+00:00', minutos_por_app={})
    assert not avaliar_foco(plano(), inicio)['ultrapassou']
    fim = uso(atualizado_em='2026-10-29T15:00:00-03:00', minutos_por_app={'Instagram': 10})
    assert not avaliar_foco(plano(), fim)['ultrapassou']


def test_nova_sessao_rearma_alerta_mas_incompativel_nao_alerta(tmp_path):
    config_path, uso_path = tmp_path/'config.json', tmp_path/'uso.json'
    config_path.write_text(json.dumps(plano()))
    uso_path.write_text(json.dumps(uso()))
    eventos = []
    monitor = MonitorFoco(config_path, uso_path, eventos.append)
    monitor.verificar()
    novo_plano = plano(inicio='2026-10-30T14:00:00-03:00', fim='2026-10-30T15:00:00-03:00')
    config_path.write_text(json.dumps(novo_plano))
    with pytest.raises(ValueError):
        monitor.verificar()
    assert len([e for e in eventos if e['tipo'] == 'alerta']) == 1
    uso_path.write_text(json.dumps(uso(inicio=novo_plano['inicio'], atualizado_em='2026-10-30T14:35:00-03:00')))
    monitor.verificar()
    assert len([e for e in eventos if e['tipo'] == 'alerta']) == 2
