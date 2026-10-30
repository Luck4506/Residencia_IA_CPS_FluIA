from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agente import FUNDO_AGENTE, RESET, formatar_fala_agente


def test_fala_sem_cor_permanece_uma_linha():
    assert formatar_fala_agente("Olá.") == "Agente: Olá."


def test_fala_colorida_separa_o_bloco_do_usuario():
    bloco = formatar_fala_agente("Retome o foco.", largura=24, colorir=True)
    assert bloco.startswith("\n")
    assert bloco.endswith("\n")
    assert " Agente" in bloco
    assert " Retome o foco." in bloco
    assert FUNDO_AGENTE in bloco
    assert RESET in bloco
    linhas = bloco.strip("\n").splitlines()
    assert all(len(linha) == 24 + len(FUNDO_AGENTE) + len(RESET) for linha in linhas)
