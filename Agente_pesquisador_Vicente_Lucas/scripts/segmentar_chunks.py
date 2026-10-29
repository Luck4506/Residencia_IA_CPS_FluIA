"""Cada pergunta e resposta do PDF Vicente vira um chunk."""
import json
import re
from pathlib import Path
from config import PROCESSED
from extrair_pdf import main as extrair


def segmentar_paginas(paginas):
    documentos = {}

    for pagina in paginas:
        documentos.setdefault(pagina['arquivo'], []).append(pagina)

    chunks = []

    for arquivo, paginas_pdf in documentos.items():
        texto = ''
        limites = []

        for pagina in paginas_pdf:
            # Remove o número impresso sem perder a página de origem.
            limpo = re.sub(r'(?im)^\s*P[ÁA]GINA\s+\d+\s*$', '', pagina['texto'])
            limites.append((len(texto), pagina['pagina']))
            texto += limpo + '\n'

        # Mantém o FAQ inteiro, mesmo quando atravessa duas páginas.
        padrao = (r'ID:\s*(FAQ-\d+)\s*PERGUNTA:\s*(.*?)'
                  r'\s*RESPOSTA:\s*(.*?)\s*REFER[ÊE]NCIA BIBLIOGR[ÁA]FICA:\s*(.*?)'
                  r'\s*FIM DO REGISTRO')
        registros = list(re.finditer(padrao, texto, re.S | re.I))
        quantidade = len(re.findall(r'ID:\s*FAQ-\d+', texto, re.I))

        if not registros or len(registros) != quantidade:
            raise ValueError(f'{arquivo}: registro ausente ou incompleto; confira os campos do FAQ.')

        for registro in registros:
            id_faq, pergunta, resposta, referencia = registro.groups()
            pergunta = ' '.join(pergunta.split())
            resposta = ' '.join(resposta.split())
            referencia = ' '.join(referencia.split())

            if not pergunta or not resposta or not referencia:
                raise ValueError(f'{id_faq}: campo ausente.')

            inicio = max(n for pos, n in limites if pos <= registro.start())
            fim = max(n for pos, n in limites if pos < registro.end())
            chunks.append({
                'id': f'{Path(arquivo).stem}:{id_faq}', 'faq_id': id_faq,
                'pergunta': pergunta, 'resposta': resposta,
                'referencia_bibliografica': referencia, 'arquivo': arquivo,
                'pagina_inicio': inicio, 'pagina_fim': fim,
                'origem': 'Vicente', 'preferencia': 'geral', 'fonte': '',
                'referencia_ficticia': 'FICTÍCIA' in referencia.upper() or 'FICTICIA' in referencia.upper(),
                'texto': f'Pergunta: {pergunta}\nResposta: {resposta}\nReferência: {referencia}',
            })

    if len({c['id'] for c in chunks}) != len(chunks):
        raise ValueError('Há IDs repetidos no PDF.')

    return chunks


def main():
    chunks = segmentar_paginas(extrair())
    (PROCESSED / 'chunks.json').write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2), encoding='utf-8')

    return chunks


if __name__ == '__main__':
    print(f'{len(main())} chunks preparados.')
