import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

# Carrega o arquivo didático diretamente, sem exigir instalação como pacote.
SCRIPT = Path(__file__).resolve().parents[1] / 'agente.py'
spec = importlib.util.spec_from_file_location('agente', SCRIPT)
agente = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agente)


@pytest.fixture
def arquivo(tmp_path, monkeypatch):
    caminho = tmp_path / 'configuracao.json'
    monkeypatch.setattr(agente, 'ARQUIVO_CONFIGURACAO', caminho)
    uso = tmp_path / 'uso.json'
    uso.write_text(json.dumps({'inicio': '2026-10-29T14:00:00-03:00', 'atualizado_em': '2026-10-29T14:40:00-03:00', 'minutos_por_app': {'Docs': 20, 'Instagram': 10, 'YouTube': 10}}))
    monkeypatch.setattr(agente, 'ARQUIVO_USO', uso)
    agente.salvar_configuracao({
        'inicio': '2026-10-29T14:00:00-03:00', 'fim': '2026-10-29T15:00:00-03:00',
        'objetivo': 'Estudar Python', 'limite_distracao': 15, 'apps_de_foco': ['Docs'],
    })
    return caminho


def test_mudanca_parcial_preserva_campos_e_altera_avaliacao(arquivo):
    assert agente.verificar_foco.invoke({})['ultrapassou'] is True
    agente.atualizar_configuracao.invoke({'limite_distracao': 25})
    assert agente.verificar_foco.invoke({})['ultrapassou'] is False
    resultado = agente.atualizar_configuracao.invoke({'apps_de_foco': []})
    assert resultado == {'inicio': '2026-10-29T14:00:00-03:00', 'fim': '2026-10-29T15:00:00-03:00', 'objetivo': 'Estudar Python', 'limite_distracao': 25, 'apps_de_foco': []}
    assert agente.verificar_foco.invoke({})['minutos_distraidos'] == 40


def test_zero_e_null(arquivo):
    agente.atualizar_configuracao.invoke({'limite_distracao': 0, 'objetivo': None})
    assert agente.ler_configuracao()['limite_distracao'] == 0
    assert agente.ler_configuracao()['objetivo'] == 'Estudar Python'


@pytest.mark.parametrize('alteracao', [
    {'limite_distracao': -1}, {'limite_distracao': 61},
    {'objetivo': '   '}, {'apps_de_foco': ['']},
])
def test_invalido_nao_altera_arquivo(arquivo, alteracao):
    antes = arquivo.read_bytes()
    with pytest.raises(ValidationError):
        agente.atualizar_configuracao.invoke(alteracao)
    assert arquivo.read_bytes() == antes


def test_arquivo_corrompido_nao_e_substituido(arquivo):
    arquivo.write_text('{invalido')
    with pytest.raises(ValueError):
        agente.atualizar_configuracao.invoke({'limite_distracao': 25})
    assert arquivo.read_text() == '{invalido'


def test_novo_processo_le_configuracao_salva(arquivo):
    agente.atualizar_configuracao.invoke({'limite_distracao': 30})
    codigo = f'''import sys, json
from pathlib import Path
sys.path.insert(0, {str(SCRIPT.parent)!r})
import agente
agente.ARQUIVO_CONFIGURACAO = Path({str(arquivo)!r})
print(json.dumps(agente.consultar_configuracao.invoke({{}})))
'''
    saida = subprocess.check_output([sys.executable, '-c', codigo], cwd=arquivo.parent, text=True)
    assert json.loads(saida)['limite_distracao'] == 30


def test_atualizacao_e_consulta_na_mesma_rodada(arquivo, monkeypatch):
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import AIMessage, ToolMessage
    from langchain_core.outputs import ChatGeneration, ChatResult

    class ModeloSimulado(BaseChatModel):
        chamadas: int = 0

        @property
        def _llm_type(self):
            return 'teste'

        def bind_tools(self, tools, **kwargs):
            return self

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            self.chamadas += 1
            mensagem = AIMessage(content='Pronto.')
            if self.chamadas == 1:
                mensagem = AIMessage(content='', tool_calls=[
                    {'name': 'atualizar_configuracao', 'args': {'limite_distracao': 30}, 'id': '1'},
                    {'name': 'verificar_foco', 'args': {}, 'id': '2'},
                ])
            return ChatResult(generations=[ChatGeneration(message=mensagem)])

    monkeypatch.setattr(agente, 'ChatOllama', lambda **kwargs: ModeloSimulado())
    resposta = agente.criar_agente().invoke({'messages': [('user', 'Altere e confira')]})
    resultados = [json.loads(m.content) for m in resposta['messages']
                  if isinstance(m, ToolMessage) and m.name == 'verificar_foco']
    assert resultados[0]['limite_distracao'] == 30
    assert resultados[0]['ultrapassou'] is False


def test_adicionar_app_preserva_configuracao_e_nao_duplica(arquivo):
    antes = agente.ler_configuracao()
    assert agente.verificar_foco.invoke({})['minutos_distraidos'] == 20
    resultado = agente.adicionar_app_de_foco.invoke({'app': 'YouTube'})
    assert resultado == antes | {'apps_de_foco': ['Docs', 'YouTube']}
    assert agente.verificar_foco.invoke({})['minutos_distraidos'] == 10
    agente.adicionar_app_de_foco.invoke({'app': ' YouTube '})
    assert agente.ler_configuracao() == resultado


def test_adicionar_app_vazio_nao_altera_configuracao(arquivo):
    antes = arquivo.read_bytes()
    with pytest.raises(ValidationError):
        agente.adicionar_app_de_foco.invoke({'app': '   '})
    assert arquivo.read_bytes() == antes


@pytest.mark.parametrize('nome', ['youtube', 'YOUTUBE', ' YouTube '])
def test_excecao_ignora_maiusculas_no_calculo(arquivo, nome):
    agente.adicionar_app_de_foco.invoke({'app': nome})
    resultado = agente.verificar_foco.invoke({})
    assert resultado['minutos_distraidos'] == 10
    assert resultado['ultrapassou'] is False
    agente.adicionar_app_de_foco.invoke({'app': 'YouTube'})
    assert agente.ler_configuracao()['apps_de_foco'] == ['Docs', nome.strip()]


def test_lista_editada_no_disco_aceita_variantes_sem_reescrever(arquivo):
    dados = json.loads(arquivo.read_text())
    dados['apps_de_foco'] = ['Docs', 'youtube', 'YOUTUBE']
    arquivo.write_text(json.dumps(dados))
    antes = arquivo.read_bytes()
    assert agente.ler_configuracao()['apps_de_foco'] == ['Docs', 'youtube']
    assert agente.verificar_foco.invoke({})['minutos_distraidos'] == 10
    assert arquivo.read_bytes() == antes
