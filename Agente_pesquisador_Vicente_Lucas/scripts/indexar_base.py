"""Cria os vetores das perguntas e salva no ChromaDB."""
import json
import os
import uuid
from config import BASE, PROCESSED, DB_PATH, MODEL_NAME
from extrair_pdf import assinatura
from segmentar_chunks import main as segmentar


def carregar_modelo():
    # Reutiliza o modelo já baixado para não depender da internet.
    cache = BASE / '.cache/huggingface'
    os.environ.setdefault('HF_HOME', str(cache))
    from sentence_transformers import SentenceTransformer
    pasta = cache / ('models--' + MODEL_NAME.replace('/', '--'))
    origem = MODEL_NAME

    if (pasta / 'refs/main').exists():
        revisao = (pasta / 'refs/main').read_text().strip()
        local = pasta / 'snapshots' / revisao

        if (local / 'model.safetensors').exists() and (local / 'tokenizer.json').exists():
            origem = str(local)

    return SentenceTransformer(origem, cache_folder=str(cache), device='cpu')


def cliente():
    import chromadb
    from chromadb.config import Settings

    return chromadb.PersistentClient(
        path=str(DB_PATH), settings=Settings(anonymized_telemetry=False))


def indexar(modelo=None):
    chunks = segmentar()
    marca = assinatura()

    if modelo is None:
        modelo = carregar_modelo()

    # A comparação é entre perguntas; cada chunk guarda também a resposta.
    perguntas = [chunk['pergunta'] for chunk in chunks]
    vetores = modelo.encode(perguntas, normalize_embeddings=True).tolist()
    metadados = [{k: v for k, v in c.items() if k != 'texto'} for c in chunks]
    db = cliente()
    nome = 'bem_estar_digital_' + uuid.uuid4().hex
    colecao = db.create_collection(
        nome, embedding_function=None, configuration={'hnsw': {'space': 'cosine'}})
    manifesto = PROCESSED / 'indice.json'
    anterior = json.loads(manifesto.read_text()) if manifesto.exists() else {}

    # Só troca o índice antigo quando o novo estiver pronto.
    try:
        colecao.upsert(ids=[c['id'] for c in chunks], documents=[c['texto'] for c in chunks],
                       embeddings=vetores, metadatas=metadados)

        if marca != assinatura():
            raise ValueError('O PDF mudou durante a indexação. Tente novamente.')

        dados = {'colecao': nome, 'modelo': MODEL_NAME, 'assinatura': marca,
                 'estrategia': 'perguntas_v1', 'chunks': len(chunks)}
        temporario = manifesto.with_suffix('.tmp')
        temporario.write_text(json.dumps(dados, indent=2), encoding='utf-8')
        temporario.replace(manifesto)
    except Exception:
        db.delete_collection(nome)
        raise

    if anterior.get('colecao'):
        db.delete_collection(anterior['colecao'])

    return len(chunks)


if __name__ == '__main__':
    print(f'{indexar()} chunks indexados.')
