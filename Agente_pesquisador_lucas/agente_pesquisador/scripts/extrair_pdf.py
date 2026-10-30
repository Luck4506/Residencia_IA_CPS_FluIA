"""Etapa 1: extração por página, sem perder o PDF de origem."""
import hashlib
import json
from pathlib import Path
from pypdf import PdfReader

BASE=Path(__file__).resolve().parents[1]
RAW=BASE/'data/raw'
PROCESSED=BASE/'data/processed'


def assinatura():
    arquivos=sorted(RAW.glob('*.pdf'))
    if not arquivos:
        raise ValueError('Adicione um PDF FAQ em data/raw.')
    h=hashlib.sha256()
    for p in arquivos:
        h.update(p.name.encode());h.update(p.read_bytes())
    return h.hexdigest()


def extrair():
    paginas=[]
    for arquivo in sorted(RAW.glob('*.pdf')):
        for n,pagina in enumerate(PdfReader(arquivo).pages,1):
            texto=pagina.extract_text() or ''
            if not texto.strip():
                raise ValueError(f'{arquivo.name}, página {n}: sem texto; faça OCR antes.')
            paginas.append({'arquivo':arquivo.name,'pagina':n,'texto':texto})
    if not paginas:
        raise ValueError('Nenhuma página extraída.')
    PROCESSED.mkdir(parents=True,exist_ok=True)
    (PROCESSED/'paginas.json').write_text(json.dumps(paginas,ensure_ascii=False,indent=2),encoding='utf-8')
    return paginas


if __name__=='__main__':
    print(f'{len(extrair())} páginas extraídas.')
