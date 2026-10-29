"""Busca de perguntas semelhantes com E5; resposta original ou redação pelo Ollama."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
import numpy as np
from extrair_pdf import BASE,PROCESSED
from segmentar_chunks import carregar,segmentar,PREFERENCIAS

MODELO='intfloat/multilingual-e5-small'
REVISAO='614241f622f53c4eeff9890bdc4f31cfecc418b3'


def modelo():
    from sentence_transformers import SentenceTransformer
    raiz=BASE.parent
    cache=raiz/'.cache/huggingface'
    os.environ.setdefault('HF_HOME',str(cache))
    local=cache/'models--intfloat--multilingual-e5-small/snapshots'/REVISAO
    origem=str(local) if (local/'model.safetensors').exists() and (local/'tokenizer.json').exists() else MODELO
    return SentenceTransformer(origem,revision=REVISAO,cache_folder=str(cache),device='cpu')


def buscar(pergunta,preferencia='todos',top_k=3,minimo=None):
    if not pergunta.strip():
        raise ValueError('Digite uma pergunta.')
    if not 1<=top_k<=10:
        raise ValueError('top-k deve estar entre 1 e 10.')
    todos=carregar('todos')
    if preferencia not in PREFERENCIAS:
        raise ValueError('Preferência inválida.')
    indices=[i for i,r in enumerate(todos) if preferencia=='todos' or r['preferencia']==preferencia]
    if not indices:
        return []
    m=modelo()
    if len(m.tokenizer.encode(pergunta,add_special_tokens=False))>450:
        raise ValueError('Reduza a pergunta para até 450 tokens.')
    chave=hashlib.sha256(json.dumps([MODELO,REVISAO,[r['pergunta'] for r in todos]],ensure_ascii=False).encode()).hexdigest()
    caminho=PROCESSED/'embeddings.npz'
    vetores=None
    if caminho.exists():
        with np.load(caminho,allow_pickle=False) as z:
            if str(z['assinatura'])==chave:
                vetores=z['vetores']
    if vetores is None:
        vetores=m.encode(['passage: '+r['pergunta'] for r in todos],normalize_embeddings=True,show_progress_bar=False)
        np.savez(caminho,vetores=vetores,assinatura=chave)
    q=m.encode(['query: '+pergunta],normalize_embeddings=True,show_progress_bar=False)[0]
    scores=vetores[indices]@q
    saida=[]
    for j in np.argsort(-scores)[:top_k]:
        if minimo is None or float(scores[j])>=minimo:
            saida.append({**todos[indices[j]],'similaridade':float(scores[j])})
    return saida


def exibir(resultados,pergunta,usar_llm=False,modelo_llm='llama3.2:3b'):
    if not resultados:
        print('Nenhuma pergunta encontrada para a preferência e o filtro informados.');return
    primeiro=resultados[0]
    print(f"\nPergunta semelhante: {primeiro['pergunta']}\nPreferência: {primeiro['preferencia']} | Similaridade: {primeiro['similaridade']:.3f}")
    if usar_llm:
        # Mantém o cliente Ollama já testado do projeto, limitado ao FAQ recuperado.
        sys.path.insert(0,str(BASE.parent/'src'))
        from bem_estar_digital.geracao import Ollama,responder,SEM_EVIDENCIA
        resposta=responder(pergunta,[{'texto':primeiro['pergunta']+'\n'+primeiro['resposta']+'\n'+primeiro['base_teorica'],
                                    'arquivo':primeiro['arquivo'],'pagina':primeiro['pagina']}],Ollama(os.getenv('OLLAMA_BASE_URL','http://localhost:11434')),modelo_llm)
        print('\nResposta do Ollama: '+resposta)
        if resposta==SEM_EVIDENCIA:
            print('O modelo considerou o FAQ insuficiente para a pergunta.')
    else:
        print('\nResposta cadastrada do FAQ candidato: '+primeiro['resposta'])
    fonte_label="Fonte [T1]" if usar_llm else "Fonte"
    print(f"\nBase teórica: {primeiro['base_teorica']}\n{fonte_label}: {primeiro['fonte']}\nPDF: {primeiro['arquivo']} | página {primeiro['pagina']} | {primeiro['id']}")
    if len(resultados)>1:
        print('\nOutras perguntas semelhantes:')
        for r in resultados[1:]:print(f"- {r['id']} | {r['similaridade']:.3f} | {r['pergunta']}")
    print('\nA similaridade ordena candidatos; não garante que a pergunta esteja respondida.')


def main():
    p=argparse.ArgumentParser(description='FAQ RAG por preferência de dispositivo.')
    p.add_argument('pergunta',nargs='?',help='Pergunta entre aspas; sem argumento abre modo interativo.')
    p.add_argument('--preferencia',choices=PREFERENCIAS,default='todos')
    p.add_argument('--top-k',type=int,default=3)
    p.add_argument('--minimo',type=float,help='Limiar experimental de similaridade, de -1 a 1.')
    p.add_argument('--ollama',action='store_true',help='Usar Llama para redigir a resposta recuperada.')
    p.add_argument('--modelo',default=os.getenv('LLAMA_MODEL','llama3.2:3b'))
    p.add_argument('--indexar',action='store_true')
    # Compatibilidade com o comando anterior; agora o par FAQ já é exibido completo.
    p.add_argument('--mostrar-trechos',action='store_true',help=argparse.SUPPRESS)
    a=p.parse_args()
    try:
        if a.minimo is not None and not -1<=a.minimo<=1:raise ValueError('Limiar deve estar entre -1 e 1.')
        if a.indexar:
            itens=segmentar()['faqs'];buscar(itens[0]['pergunta']);print(f'{len(itens)} FAQs indexados.');return 0
        if a.pergunta:
            exibir(buscar(a.pergunta,a.preferencia,a.top_k,a.minimo),a.pergunta,a.ollama,a.modelo)
        else:
            print('Digite sair para encerrar.')
            while True:
                pergunta=input('Sua pergunta: ').strip()
                if pergunta.lower() in {'sair','exit'}:break
                if pergunta:exibir(buscar(pergunta,a.preferencia,a.top_k,a.minimo),pergunta,a.ollama,a.modelo)
        return 0
    except (ValueError,RuntimeError,OSError) as erro:
        print(f'Erro: {erro}',file=sys.stderr);return 1
    except (KeyboardInterrupt,EOFError):
        return 0


if __name__=='__main__':raise SystemExit(main())
