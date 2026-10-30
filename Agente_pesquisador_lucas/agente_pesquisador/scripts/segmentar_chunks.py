"""Etapa 2: um registro completo por pergunta/resposta, sem quebrar o par."""
import json
import re
from extrair_pdf import extrair,assinatura,PROCESSED

PREFERENCIAS=('todos','geral','android','mac','windows')


def segmentar():
    registros=[]
    for pagina in extrair():
        partes=re.split(r'(?=ID:\s*FAQ\d+)',pagina['texto'])
        for parte in partes:
            if not parte.startswith('ID:'):
                continue
            padrao=r'ID:\s*(FAQ\d+)\s+Preferencia:\s*(\w+)\s+Pergunta:\s*(.*?)\s+Resposta:\s*(.*?)\s+Base teorica:\s*(.*?)\s+Fonte:\s*(https?://\S+)'
            m=re.search(padrao,parte,re.S)
            if not m:
                raise ValueError(f'FAQ inválido em {pagina["arquivo"]}, página {pagina["pagina"]}. Confira os campos e se o par cabe na página.')
            id_,pref,q,a,b,url=m.groups()
            if pref not in PREFERENCIAS[1:]:
                raise ValueError(f'Preferência desconhecida: {pref}')
            registros.append({'id':id_,'preferencia':pref,'pergunta':' '.join(q.split()),
                'resposta':' '.join(a.split()),'base_teorica':' '.join(b.split()),
                'fonte':url,'arquivo':pagina['arquivo'],'pagina':pagina['pagina']})
    if not registros or len({r['id'] for r in registros})!=len(registros):
        raise ValueError('FAQ vazio ou IDs repetidos; use IDs únicos em todos os PDFs.')
    dados={'assinatura':assinatura(),'faqs':registros}
    (PROCESSED/'faq.json').write_text(json.dumps(dados,ensure_ascii=False,indent=2),encoding='utf-8')
    return dados


def carregar(preferencia='todos'):
    if preferencia not in PREFERENCIAS:
        raise ValueError('Preferência inválida.')
    p=PROCESSED/'faq.json'
    dados=json.loads(p.read_text(encoding='utf-8')) if p.exists() else segmentar()
    if dados['assinatura']!=assinatura():
        dados=segmentar()
    return [r for r in dados['faqs'] if preferencia=='todos' or r['preferencia']==preferencia]


if __name__=='__main__':
    print(f'{len(segmentar()["faqs"])} pares de perguntas e respostas preparados.')
