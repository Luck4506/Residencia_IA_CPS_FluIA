"""Baseline de palavras: preserva o mesmo filtro usado pela busca semântica."""
import argparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from segmentar_chunks import carregar,PREFERENCIAS


def buscar(pergunta,preferencia='todos',top_k=3):
    itens=carregar(preferencia)
    if not itens or not pergunta.strip():
        return []
    vetorizador=TfidfVectorizer(strip_accents='unicode',ngram_range=(1,2))
    matriz=vetorizador.fit_transform([r['pergunta'] for r in itens])
    scores=cosine_similarity(vetorizador.transform([pergunta]),matriz)[0]
    return [{**itens[i],'similaridade':float(scores[i])} for i in scores.argsort()[::-1][:top_k] if scores[i]>0]


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('pergunta');parser.add_argument('--preferencia',choices=PREFERENCIAS,default='todos')
    a=parser.parse_args()
    for r in buscar(a.pergunta,a.preferencia):
        print(f"{r['id']} | {r['similaridade']:.3f} | {r['pergunta']}\n{r['resposta']}\nFonte: {r['fonte']}\n")
