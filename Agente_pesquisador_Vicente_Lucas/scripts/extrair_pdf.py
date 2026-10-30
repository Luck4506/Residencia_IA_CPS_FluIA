"""Base Vicente: extração PDF por página; complementada com vários PDFs e assinatura."""
import hashlib
import json
from config import RAW, PROCESSED


def assinatura():
    # Detecta alterações no PDF.
    h = hashlib.sha256()

    for p in sorted(RAW.glob('*.pdf')):
        h.update(p.name.encode())
        h.update(hashlib.sha256(p.read_bytes()).digest())

    return h.hexdigest()


def extrair_texto_pdf(caminho_pdf):
    # A biblioteca de PDF só é necessária para preparar a base.
    from pypdf import PdfReader

    # Guarda o texto junto com a página de origem.
    paginas = []

    for n, p in enumerate(PdfReader(caminho_pdf).pages, 1):
        texto = p.extract_text() or ''

        if not texto.strip():
            raise ValueError(f'{caminho_pdf.name}, página {n}: sem texto; pode precisar de OCR.')

        paginas.append({'arquivo': caminho_pdf.name, 'pagina': n, 'texto': texto})

    return paginas


def main():
    arquivos = sorted(RAW.glob('*.pdf'))

    if not arquivos:
        raise ValueError('Nenhum PDF em data/raw.')

    paginas = [p for arq in arquivos for p in extrair_texto_pdf(arq)]
    PROCESSED.mkdir(parents=True, exist_ok=True)
    (PROCESSED / 'paginas.json').write_text(
        json.dumps(paginas, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    (PROCESSED / 'base_conhecimento_extraido.txt').write_text(
        '\n\n'.join(
            f"--- {p['arquivo']} | PÁGINA {p['pagina']} ---\n{p['texto']}"
            for p in paginas
        ),
        encoding='utf-8'
    )

    return paginas

if __name__ == '__main__':
    print(f'{len(main())} páginas extraídas.')
