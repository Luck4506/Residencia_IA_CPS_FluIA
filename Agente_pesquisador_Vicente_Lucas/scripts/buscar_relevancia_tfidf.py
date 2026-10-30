"""Baseline de Vicente para comparar com o ranking vetorial."""
import argparse
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config import PROCESSED, PREFERENCIAS


def buscar(pergunta, preferencia='todos'):
    chunks = json.loads((PROCESSED / 'chunks.json').read_text(encoding='utf-8'))
    chunks = [c for c in chunks if preferencia == 'todos' or c['preferencia'] == preferencia]

    if not chunks:
        return []

    # Compara as palavras das perguntas.
    vectorizer = TfidfVectorizer(strip_accents='unicode', ngram_range=(1, 2))
    matriz = vectorizer.fit_transform([c['pergunta'] for c in chunks])
    scores = cosine_similarity(vectorizer.transform([pergunta]), matriz)[0]

    return [{'chunk': chunks[i], 'similaridade': float(scores[i])} for i in scores.argsort()[::-1][:3]]

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('pergunta')
    p.add_argument('--preferencia', choices=PREFERENCIAS, default='todos')
    a = p.parse_args()

    for r in buscar(a.pergunta, a.preferencia):
        print(r['chunk']['id'], round(r['similaridade'], 3), r['chunk']['pergunta'])
