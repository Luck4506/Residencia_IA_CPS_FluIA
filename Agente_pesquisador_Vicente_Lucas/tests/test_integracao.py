import io
import json
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import indexar_base as indice
import buscar_relevancia_embeddings as busca
from segmentar_chunks import main as segmentar, segmentar_paginas


class ModeloTeste:

    class Tokenizer:

        def encode(self, text, **kwargs):
            return text.split()
    tokenizer = Tokenizer()

    def encode(self, textos, **kwargs):
        return np.array([[1.0, 0.0] if 'windows' in t.lower() else [0.0, 1.0] for t in textos])


class TestIntegracao(unittest.TestCase):

    def test_base_completa_e_ids_unicos(self):
        chunks = segmentar()
        self.assertEqual(len(chunks), 8)
        self.assertEqual(len({c['id'] for c in chunks}), 8)
        self.assertEqual(sum((c['origem'] == 'Vicente' for c in chunks)), 8)
        self.assertTrue(all((c['resposta'] and c['referencia_bibliografica'] for c in chunks)))

    def test_paginacao_e_sem_cabecalho_na_pergunta(self):
        chunks = segmentar()
        vicente = next((c for c in chunks if c['faq_id'] == 'FAQ-004'))
        self.assertEqual((vicente['pagina_inicio'], vicente['pagina_fim']), (1, 2))
        self.assertTrue(all(('Página' not in c['pergunta'] and 'PÁGINA' not in c['pergunta'] for c in chunks)))

    def test_referencias_ficticias_preservadas(self):
        chunks = segmentar()
        self.assertTrue(all((c['referencia_ficticia'] for c in chunks if c['origem'] == 'Vicente')))
        self.assertTrue(all((c['origem'] == 'Vicente' for c in chunks)))

    def test_registro_incompleto_rejeitado(self):
        with self.assertRaisesRegex(ValueError, 'ausente|incompleto'):
            segmentar_paginas([{'arquivo': 'teste.pdf', 'pagina': 1, 'texto': 'ID: FAQ-001\nPERGUNTA: P?\nRESPOSTA: R.'}])

    def test_identificacao_e_um_unico_chunk_para_ollama(self):
        chunks = segmentar()[:2]
        resultados = [{'chunk': c, 'similaridade': 1} for c in chunks]
        saida = io.StringIO()

        with (
            patch.object(busca, 'responder', return_value='Resposta [T1]') as gerar,
            redirect_stdout(saida),
        ):
            busca.exibir_resultado(resultados, 'Pergunta')

        self.assertEqual(gerar.call_args.args[1]['id'], chunks[0]['id'])
        self.assertIn(chunks[0]['id'], saida.getvalue())
        self.assertIn('páginas', saida.getvalue())

    def test_sem_evidencia_nao_chama_ollama(self):
        chunk = segmentar()[0]

        with patch.object(busca, 'responder') as gerar, redirect_stdout(io.StringIO()):
            busca.exibir_resultado([{'chunk': chunk, 'similaridade': 0.1}], 'Fora da base', minimo=0.5)

        gerar.assert_not_called()

    def test_loop_continua_apos_erro_e_ignora_vazio(self):
        with (
            patch.object(sys, 'argv', ['app.py']),
            patch.object(busca, 'carregar_modelo') as carregar,
            patch('builtins.input', side_effect=['', 'primeira', 'segunda', 'sair']),
            patch.object(busca, 'buscar_relevancia', side_effect=[RuntimeError('falha temporária'), []]) as recuperar,
            patch.object(busca, 'exibir_resultado') as exibir,
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(busca.main(), 0)

        self.assertEqual(carregar.call_count, 1)
        self.assertEqual(recuperar.call_count, 2)
        self.assertEqual(exibir.call_count, 1)

    def test_pergunta_inicial_tambem_entra_no_loop(self):
        with (
            patch.object(sys, 'argv', ['app.py', 'inicial']),
            patch.object(busca, 'carregar_modelo'),
            patch('builtins.input', side_effect=['proxima', 'sair']),
            patch.object(busca, 'buscar_relevancia', return_value=[]) as recuperar,
            patch.object(busca, 'exibir_resultado'),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(busca.main(), 0)

        self.assertEqual([c.args[0] for c in recuperar.call_args_list], ['inicial', 'proxima'])

    def test_uma_vez_nao_pede_outra_pergunta(self):
        with (
            patch.object(sys, 'argv', ['app.py', 'inicial', '--uma-vez']),
            patch.object(busca, 'carregar_modelo'),
            patch('builtins.input', side_effect=AssertionError('Não perguntar novamente')),
            patch.object(busca, 'buscar_relevancia', return_value=[]),
            patch.object(busca, 'exibir_resultado'),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(busca.main(), 0)

    def test_ollama_recebe_apenas_o_chunk_escolhido(self):
        from ollama import responder
        chunk = segmentar()[0]

        with patch('ollama.urlopen') as abrir:
            abrir.return_value.__enter__.return_value.read.return_value = b'{"message":{"content":"Resposta do chunk"}}'
            self.assertEqual(responder('Pergunta', chunk), 'Resposta do chunk')
            pedido = abrir.call_args.args[0]
            dados = json.loads(pedido.data)
            contexto = json.loads(dados['messages'][1]['content'])
            self.assertEqual(contexto['resposta_do_faq'], chunk['resposta'])
            self.assertEqual(contexto['referencia'], chunk['referencia_bibliografica'])
            self.assertFalse(dados['stream'])

    def test_ollama_rejeita_resposta_vazia(self):
        from ollama import responder

        with patch('ollama.urlopen') as abrir:
            abrir.return_value.__enter__.return_value.read.return_value = b'{"message":{"content":""}}'

            with self.assertRaises(ValueError):
                responder('Pergunta', segmentar()[0])

    def test_persistencia_filtro_e_reindexacao(self):
        chunks = segmentar()
        # Dados fictícios usados somente para testar o filtro.
        amostra = [{**chunks[0], 'preferencia': 'windows', 'pergunta': 'Windows'}, {**chunks[1], 'preferencia': 'android', 'pergunta': 'Android'}]

        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            processed = Path(tmp) / 'processed'
            processed.mkdir()
            stack.enter_context(patch.object(indice, 'DB_PATH', Path(tmp) / 'chroma'))
            stack.enter_context(patch.object(indice, 'PROCESSED', processed))
            stack.enter_context(patch.object(busca, 'PROCESSED', processed))
            stack.enter_context(patch.object(indice, 'segmentar', return_value=amostra))
            modelo = ModeloTeste()
            indice.indexar(modelo)
            resultado = busca.buscar_relevancia('Windows', modelo, preferencia='android')
            self.assertEqual(len(resultado), 1)
            self.assertEqual(resultado[0]['chunk']['preferencia'], 'android')
            indice.indexar(modelo)
            r = busca.buscar_relevancia('Windows', modelo)
            self.assertEqual(r[0]['chunk']['id'], amostra[0]['id'])
            self.assertEqual(len(indice.cliente().list_collections()), 1)
            manifest = processed / 'indice.json'
            d = json.loads(manifest.read_text())
            d['assinatura'] = 'alterada'
            manifest.write_text(json.dumps(d))

            with self.assertRaises(ValueError):
                busca.buscar_relevancia('Windows', modelo)

if __name__ == '__main__':
    unittest.main()
