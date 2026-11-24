import json
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

from test_monitor import arquivos, escrever
import analista
import monitor


EXEMPLOS = json.loads(
    Path(__file__).with_name('fixtures').joinpath('alertas_analista.json').read_text(encoding='utf-8')
)


def test_alerta_valido_inicia_analise_com_contexto_do_periodo():
    resposta = analista.receber_alerta(EXEMPLOS['valido'])

    assert resposta == {
        'status': 'analise_iniciada',
        'analise': {'etapa': 'consulta_contexto', **EXEMPLOS['valido']},
    }


@pytest.mark.parametrize(('exemplo', 'esperados'), [
    ('incompleto', {('usuario_id', 'missing'), ('periodo_uso.fim', 'missing')}),
    ('invalido', {
        ('motivo', 'string_too_short'),
        ('horario_alerta', 'timezone_aware'),
        ('periodo_uso.fim', 'periodo_invalido'),
    }),
])
def test_alerta_rejeitado_identifica_campos_e_nao_inicia_analise(exemplo, esperados, monkeypatch):
    iniciar = Mock()
    monkeypatch.setattr(analista, 'iniciar_analise', iniciar)

    resposta = analista.receber_alerta(EXEMPLOS[exemplo])

    assert resposta['status'] == 'rejeitado'
    assert {(e['campo'], e['codigo']) for e in resposta['erros']} == esperados
    assert all(e['mensagem'] for e in resposta['erros'])
    assert 'analise' not in resposta
    iniciar.assert_not_called()


def test_monitor_encaminha_apenas_alertas_e_usa_o_fim_medido(arquivos, monkeypatch, capsys):
    configuracao, uso = arquivos
    monkeypatch.setattr(sys, 'argv', [
        'monitor.py', '--analista', 'usuario-teste-01',
        '--configuracao', str(configuracao), '--uso', str(uso),
    ])
    ciclos = iter([{'Docs': 20, 'Instagram': 18}, {'Docs': 20, 'Instagram': 19}])

    def atualizar_uso(_intervalo):
        dados = next(ciclos, None)
        if dados is None:
            raise KeyboardInterrupt
        escrever(uso, dados)

    monkeypatch.setattr(monitor.time, 'sleep', atualizar_uso)
    monitor.main()

    eventos = [json.loads(linha) for linha in capsys.readouterr().out.splitlines() if linha.startswith('{')]
    assert [e['tipo'] for e in eventos] == ['leitura', 'leitura', 'alerta', 'resultado_analista', 'leitura']
    _, _, alerta, resultado, _ = eventos
    assert resultado['status'] == 'analise_iniciada'
    assert resultado['analise'] == {
        'etapa': 'consulta_contexto',
        'usuario_id': 'usuario-teste-01',
        'script_origem': 'monitor_foco',
        'motivo': alerta['motivo'],
        'horario_alerta': alerta['horario'],
        'periodo_uso': {'inicio': alerta['inicio'], 'fim': alerta['atualizado_em']},
        'indicadores': {'minutos_distraidos': 18, 'limite_distracao': 15, 'minutos_excedidos': 3},
    }
