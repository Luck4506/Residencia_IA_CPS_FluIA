"""PDF/TXT, limpeza e chunks por parágrafos com contagem pelo tokenizer E5."""
import csv
import hashlib
import re
import unicodedata
import warnings
from collections import Counter
from pathlib import Path

from ..config import TAMANHO, SOBREPOSICAO


def limpar(texto):
    texto = unicodedata.normalize("NFC", texto).replace("\x00", "").replace("\u00ad", "")
    texto = re.sub(r"(\w)-\n(?=[a-záéíóúâêôãõç])", r"\1", texto)
    linhas = [re.sub(r"[ \t]+", " ", l).strip() for l in texto.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip()


def ler_documentos(pasta, fontes=None):
    pasta = Path(pasta)
    if not pasta.is_dir():
        raise ValueError(f"Pasta não encontrada: {pasta}")
    cadastro = {}
    if fontes and Path(fontes).exists():
        with Path(fontes).open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row["arquivo"] in cadastro:
                    raise ValueError(f"Fonte duplicada: {row['arquivo']}")
                cadastro[row["arquivo"]] = row
    documentos = []
    for arquivo in sorted(pasta.rglob("*")):
        if not arquivo.is_file() or arquivo.suffix.lower() not in {".pdf", ".txt", ".md"}:
            continue
        relativo = arquivo.relative_to(pasta).as_posix()
        meta = cadastro.get(relativo, {})
        titulo_pdf = ""
        if arquivo.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            pdf = PdfReader(arquivo)
            titulo_pdf = str((pdf.metadata or {}).get("/Title", ""))
            paginas = [p.extract_text(extraction_mode="layout") or "" for p in pdf.pages]
            bordas = Counter()
            for texto in paginas:
                linhas = [l.strip() for l in texto.splitlines() if l.strip()]
                bordas.update(set(linhas[:2] + linhas[-2:]))
            repetidas = {l for l, n in bordas.items() if n >= max(2, len(paginas) * .6)}
            paginas = ["\n".join(l for l in t.splitlines()
                       if l.strip() not in repetidas and not re.fullmatch(r"\s*\d+\s*(/\s*\d+)?\s*", l))
                       for t in paginas]
        else:
            paginas = [arquivo.read_text(encoding="utf-8-sig")]
        for numero, texto in enumerate(paginas, 1):
            texto = limpar(texto)
            if not texto:
                warnings.warn(f"{relativo}, página {numero}: sem texto extraível; pode precisar de OCR.")
                continue
            documentos.append({"arquivo": relativo, "pagina": numero if arquivo.suffix.lower()==".pdf" else 0,
                "titulo": meta.get("titulo") or titulo_pdf or texto.splitlines()[0].lstrip("# "),
                "fonte_id": meta.get("id") or hashlib.sha256(relativo.encode()).hexdigest()[:12],
                "url": meta.get("url", ""), "autor": meta.get("autor", ""),
                "data": meta.get("data", ""), "tipo": meta.get("tipo", "não cadastrado"),
                "localizacao_original": meta.get("localizacao_original", ""), "acesso": meta.get("acesso", ""),
                "texto": texto})
    if not documentos:
        raise ValueError("Nenhum texto encontrado em PDF, TXT ou Markdown. PDFs digitalizados precisam de OCR.")
    return documentos


def criar_chunks(documentos, tokenizer, tamanho=TAMANHO, sobreposicao=SOBREPOSICAO):
    if not 0 <= sobreposicao < tamanho <= 450:
        raise ValueError("Use 0 <= sobreposição < tamanho <= 450 tokens.")
    def contar(s):
        return len(tokenizer.encode(s, add_special_tokens=False))
    def cauda(s):
        offsets = tokenizer(s, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
        return s[offsets[-sobreposicao][0]:] if sobreposicao and len(offsets) >= sobreposicao else ""
    chunks = []
    for doc in documentos:
        secao = "Texto principal"
        buffer = ""
        def salvar(texto, titulo_secao):
            if not texto.strip():
                return
            chave = f"{doc['arquivo']}|{doc['pagina']}|{titulo_secao}|{texto}"
            chunks.append({**{k:v for k,v in doc.items() if k!="texto"},
                "id": hashlib.sha256(chave.encode()).hexdigest()[:32],
                "secao": titulo_secao, "texto": texto, "tokens": contar(texto)})
        # Blocos preservam parágrafos; títulos Markdown iniciam novas seções.
        blocos = re.split(r"\n\s*\n|(?=^#{1,6} )", doc["texto"], flags=re.MULTILINE)
        for bloco in blocos:
            bloco = bloco.strip()
            if not bloco:
                continue
            linhas = bloco.splitlines()
            if linhas[0].startswith("#"):
                salvar(buffer, secao)
                buffer = ""
                secao = linhas[0].lstrip("# ")
                bloco = "\n".join(linhas[1:]).strip()
                if not bloco:
                    continue
            elif doc["pagina"] and len(linhas)==1 and len(bloco)<90 and not re.search(r"[.!?]$", bloco):
                salvar(buffer, secao)
                buffer = ""
                secao = bloco
                continue
            unidades = [bloco] if contar(bloco)<=tamanho else re.split(r"(?<=[.!?])\s+", bloco)
            for unidade in unidades:
                # Somente uma frase maior que o limite é dividida por offsets de tokens.
                offsets = tokenizer(unidade, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
                partes = [unidade]
                if len(offsets)>tamanho:
                    partes=[]
                    for pos in range(0,len(offsets),tamanho-sobreposicao):
                        janela=offsets[pos:pos+tamanho]
                        partes.append(unidade[janela[0][0]:janela[-1][1]])
                        if pos+tamanho>=len(offsets):
                            break
                for parte in partes:
                    candidato = (buffer+"\n\n"+parte).strip()
                    if contar(candidato)>tamanho:
                        salvar(buffer,secao)
                        tail=cauda(buffer)
                        buffer=(tail+"\n\n"+parte).strip()
                        if contar(buffer)>tamanho:
                            buffer=parte
                    else:
                        buffer=candidato
        salvar(buffer,secao)
    # IDs por conteúdo evitam repetir um mesmo trecho do mesmo local.
    return list({c["id"]:c for c in chunks}.values())
