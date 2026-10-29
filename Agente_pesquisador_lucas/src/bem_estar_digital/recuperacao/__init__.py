"""Embeddings E5 e coleção Chroma persistente, com atualização por snapshot."""
import hashlib
import json
import os
import uuid
from pathlib import Path

from ..config import RAIZ, CONFIG, MODELO_E5, REVISAO_E5, TOP_K, caminhos
from ..ingestao import criar_chunks, ler_documentos


class E5:
    def __init__(self):
        os.environ.setdefault("HF_HOME",str(RAIZ / ".cache/huggingface"))
        from sentence_transformers import SentenceTransformer
        snapshot=RAIZ / ".cache/huggingface/models--intfloat--multilingual-e5-small/snapshots" / REVISAO_E5
        origem=str(snapshot) if (snapshot/"model.safetensors").exists() and (snapshot/"tokenizer.json").exists() else MODELO_E5
        self.model = SentenceTransformer(origem, revision=REVISAO_E5, cache_folder=str(RAIZ / ".cache/huggingface"), device="cpu")
        self.tokenizer = self.model.tokenizer

    def documentos(self,textos):
        return self.model.encode(["passage: "+t for t in textos], normalize_embeddings=True,
                                 batch_size=16, show_progress_bar=False).tolist()

    def pergunta(self,texto):
        if len(self.tokenizer.encode(texto,add_special_tokens=False))>450:
            raise ValueError("A pergunta ultrapassa 450 tokens E5. Reformule-a de forma mais curta.")
        return self.model.encode(["query: "+texto],normalize_embeddings=True,
                                 show_progress_bar=False).tolist()[0]


def gravar_json(path,dados):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(path)


def assinatura(pasta,fontes):
    digest=hashlib.sha256()
    for p in sorted(Path(pasta).rglob("*")):
        if p.is_file() and p.suffix.lower() in {".pdf",".txt",".md"}:
            digest.update(p.relative_to(pasta).as_posix().encode())
            digest.update(hashlib.sha256(p.read_bytes()).digest())
    if fontes and Path(fontes).exists():
        digest.update(Path(fontes).read_bytes())
    return digest.hexdigest()


def preparar(pasta,embedder,base=RAIZ/"data",fontes=None):
    paths=caminhos(base)
    fontes=Path(fontes) if fontes else paths["sources"]
    docs=ler_documentos(Path(pasta),fontes)
    chunks=criar_chunks(docs,embedder.tokenizer)
    paths["processed"].mkdir(parents=True,exist_ok=True)
    for nome,registros in [("documents.jsonl",docs),("chunks.jsonl",chunks)]:
        (paths["processed"]/nome).write_text("".join(json.dumps(c,ensure_ascii=False)+"\n" for c in registros),encoding="utf-8")
    return docs,chunks


def cliente_chroma(base):
    import chromadb
    from chromadb.config import Settings
    return chromadb.PersistentClient(path=str(caminhos(base)["chroma"]),settings=Settings(anonymized_telemetry=False))


def indexar(pasta,embedder,base=RAIZ/"data",fontes=None):
    pasta=Path(pasta).resolve()
    paths=caminhos(base)
    fontes=Path(fontes or paths["sources"]).resolve()
    docs,chunks=preparar(pasta,embedder,base,fontes)
    if not chunks:
        raise ValueError("Nenhum chunk foi gerado.")
    fingerprint=assinatura(pasta,fontes)
    client=cliente_chroma(base)
    # A coleção ativa anterior permanece disponível se a geração de embeddings falhar.
    nome="fluia_"+uuid.uuid4().hex
    collection=client.create_collection(nome,embedding_function=None,configuration={"hnsw":{"space":"cosine"}})
    try:
        for inicio in range(0,len(chunks),16):
            lote=chunks[inicio:inicio+16]
            collection.upsert(ids=[c["id"] for c in lote],documents=[c["texto"] for c in lote],
                embeddings=embedder.documentos([c["texto"] for c in lote]),
                metadatas=[{k:v for k,v in c.items() if k not in {"id","texto"}} for c in lote])
        if collection.count()!=len(chunks):
            raise ValueError("Coleção incompleta; o índice anterior foi preservado.")
        if assinatura(pasta,fontes)!=fingerprint:
            raise ValueError("Os documentos mudaram durante a indexação. Tente novamente.")
        anterior=json.loads(paths["manifest"].read_text()) if paths["manifest"].exists() else {}
        gravar_json(paths["manifest"],{"config":CONFIG,"colecao":nome,"assinatura":fingerprint,
            "documentos":str(pasta),"sources":str(fontes),"chunks":len(chunks)})
    except Exception:
        client.delete_collection(nome)
        raise
    if anterior.get("colecao") and anterior["colecao"]!=nome:
        # Limpeza ocorre apenas após a troca bem-sucedida do manifesto.
        client.delete_collection(anterior["colecao"])
    return len({d["arquivo"] for d in docs}),len(chunks)


def recuperar(pergunta,embedder,base=RAIZ/"data",top_k=TOP_K,max_distancia=None):
    if not pergunta.strip():
        raise ValueError("Digite uma pergunta com texto.")
    if not 1<=top_k<=20 or (max_distancia is not None and not 0<=max_distancia<=2):
        raise ValueError("Use top-k entre 1 e 20; distância máxima opcional entre 0 e 2.")
    paths=caminhos(base)
    if not paths["manifest"].exists():
        raise ValueError("Base ainda não indexada. Execute 'python app.py indexar'.")
    manifest=json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if manifest["config"]!=CONFIG:
        raise ValueError("Modelo ou chunking mudou; execute 'indexar' novamente.")
    if assinatura(Path(manifest["documentos"]),Path(manifest["sources"]))!=manifest["assinatura"]:
        raise ValueError("Documentos ou fontes mudaram; execute 'indexar' novamente.")
    collection=cliente_chroma(base).get_collection(manifest["colecao"],embedding_function=None)
    if not collection.count():
        return []
    resposta=collection.query(query_embeddings=[embedder.pergunta(pergunta)],
        n_results=min(top_k,collection.count()),include=["documents","metadatas","distances"])
    resultados=[]
    vistos=set()
    for id_,texto,meta,distancia in zip(resposta["ids"][0],resposta["documents"][0],resposta["metadatas"][0],resposta["distances"][0]):
        if texto in vistos or (max_distancia is not None and distancia>max_distancia):
            continue
        vistos.add(texto)
        resultados.append({"id":id_,"texto":texto,**meta,"distancia":float(distancia)})
    return resultados
