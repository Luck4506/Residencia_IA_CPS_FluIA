"""Interface de terminal do FluIA: python app.py --help."""
import argparse
import json
import os
import sys
from pathlib import Path
from time import perf_counter

RAIZ=Path(__file__).resolve().parent
sys.path.insert(0,str(RAIZ/'src'))
from bem_estar_digital.config import caminhos
from bem_estar_digital.rag import E5,Ollama,preparar,indexar,recuperar,responder
from bem_estar_digital.avaliacao import avaliar


def mostrar(trechos,texto=False):
    for i,t in enumerate(trechos,1):
        pagina=f"página {t['pagina']}" if t['pagina'] else 'texto sem paginação'
        print(f"[T{i}] {t['titulo']} | {t['arquivo']} | {pagina} | {t['secao']}")
        print(f"  Distância: {t['distancia']:.4f} | ID: {t['id']}")
        if t.get('url'):
            print(f"  Fonte: {t['url']}")
        if texto:
            print(f"  {t['texto']}")


def main():
    # O fluxo FAQ é a entrada padrão; os comandos anteriores de avaliação documental
    # continuam disponíveis para preservar os experimentos já feitos.
    if len(sys.argv)==1 or sys.argv[1] in {'faq','indexar','perguntar','recuperar','--help','-h'}:
        sys.path.insert(0,str(RAIZ/'agente_pesquisador/scripts'))
        from buscar_relevancia_embeddings import main as main_faq
        if len(sys.argv)>1:
            comando=sys.argv.pop(1)
            if comando in {'--help','-h'}:sys.argv.append('--help')
            elif comando=='indexar':sys.argv.append('--indexar')
            elif comando=='perguntar':sys.argv.append('--ollama')
        return main_faq()
    parser=argparse.ArgumentParser(description='FluIA: PDF/TXT → E5 → ChromaDB → Llama via Ollama.')
    comandos=parser.add_subparsers(dest='comando',required=True)
    for nome,ajuda in [('preparar','Extrair, limpar e inspecionar chunks sem criar o índice.'),
                       ('indexar','Gerar embeddings e persistir a coleção Chroma.'),
                       ('recuperar','Inspecionar somente a busca, sem chamar o Llama.'),
                       ('perguntar','Buscar evidências e gerar uma resposta com fontes.'),
                       ('avaliar','Executar perguntas de avaliação e salvar resultados.')]:
        p=comandos.add_parser(nome,help=ajuda)
        p.add_argument('--base',type=Path,default=RAIZ/'data',help='Diretório de processamento e persistência.')
        if nome in {'preparar','indexar'}:
            p.add_argument('--documentos',type=Path,default=RAIZ/'data/raw')
            p.add_argument('--fontes',type=Path,help='Cadastro CSV; padrão: <base>/sources.csv.')
        else:
            p.add_argument('--top-k',type=int,default=5)
            p.add_argument('--max-distancia',type=float,default=None,help='Filtro opcional; calibrar com os testes.')
        if nome in {'recuperar','perguntar'}:
            p.add_argument('pergunta')
            p.add_argument('--mostrar-trechos',action='store_true')
        if nome in {'perguntar','avaliar'}:
            p.add_argument('--modelo',default=os.getenv('LLAMA_MODEL','llama3.2:3b'))
            p.add_argument('--servidor',default=os.getenv('OLLAMA_BASE_URL','http://localhost:11434'))
        if nome=='avaliar':
            p.add_argument('--sem-geracao',action='store_true',help='Avaliar apenas a recuperação, sem Ollama.')
    args=parser.parse_args()
    try:
        if args.comando not in {'preparar','indexar'} and not caminhos(args.base)['manifest'].exists():
            raise ValueError("Base ainda não indexada. Execute 'python app.py indexar'.")
        print('Carregando embeddings E5 locais (primeira execução baixa o modelo)...',flush=True)
        embedder=E5()
        if args.comando in {'preparar','indexar'}:
            if args.comando=='preparar':
                docs,chunks=preparar(args.documentos,embedder,args.base,args.fontes)
                print(f'{len({d["arquivo"] for d in docs})} documentos; {len(chunks)} chunks.')
                for c in chunks[:5]:
                    print(f"\n{c['arquivo']} | página {c['pagina'] or '-'} | {c['secao']} | {c['tokens']} tokens\n{c['texto']}")
            else:
                n,c=indexar(args.documentos,embedder,args.base,args.fontes)
                print(f'Coleção pronta: {n} documentos; {c} chunks.')
            return 0
        if args.comando=='avaliar':
            pasta,resultados=avaliar(embedder,Ollama(args.servidor),args.modelo,args.base,
                                    args.sem_geracao,args.top_k,args.max_distancia)
            print(f'{len(resultados)} casos registrados em {pasta}')
            erros=sum(bool(r['erro']) for r in resultados)
            print(f'Erros de execução: {erros}. Fidelidade e sustentação das citações aguardam revisão manual.')
            return 1 if erros else 0
        inicio=perf_counter()
        trechos=recuperar(args.pergunta,embedder,args.base,args.top_k,args.max_distancia)
        print(f'\nBusca: {perf_counter()-inicio:.2f}s; {len(trechos)} trechos.')
        if args.comando=='perguntar':
            print('\n'+responder(args.pergunta,trechos,Ollama(args.servidor),args.modelo)+'\n')
        mostrar(trechos,args.mostrar_trechos or args.comando=='recuperar')
        return 0
    except ImportError as erro:
        print(f'Biblioteca ausente: {erro}. Ative o ambiente e execute: python -m pip install -r requirements.txt',file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\nOperação interrompida.',file=sys.stderr)
        return 130
    except Exception as erro:
        print(f'Erro: {erro}',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
