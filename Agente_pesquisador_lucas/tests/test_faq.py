import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'agente_pesquisador/scripts'))
from segmentar_chunks import segmentar,carregar
from buscar_relevancia_tfidf import buscar

class TestFaq(unittest.TestCase):
    def test_pdf_extrai_oito_pares_com_fontes_e_paginas(self):
        itens=segmentar()['faqs']
        self.assertEqual(len(itens),8)
        self.assertEqual({r['pagina'] for r in itens},{1,2,3,4})
        self.assertTrue(all(r['resposta'] and r['base_teorica'] and r['fonte'].startswith('https://') for r in itens))
    def test_preferencia_estrita(self):
        for pref in ['android','mac','windows','geral']:
            itens=carregar(pref)
            self.assertEqual(len(itens),2)
            self.assertTrue(all(r['preferencia']==pref for r in itens))
    def test_tfidf_pergunta_exata(self):
        item=carregar('mac')[0]
        achados=buscar(item['pergunta'],'mac')
        self.assertEqual(achados[0]['id'],item['id'])
        self.assertAlmostEqual(achados[0]['similaridade'],1)
    def test_preferencia_invalida(self):
        with self.assertRaises(ValueError):carregar('brasil')

if __name__=='__main__':unittest.main()
