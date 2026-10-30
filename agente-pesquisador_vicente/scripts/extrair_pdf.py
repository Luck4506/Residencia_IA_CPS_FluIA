from pathlib import Path
from pypdf import PdfReader

# Caminhos dos arquivos
PDF_PATH = Path("agente-pesquisador/data/raw/base_conhecimento.pdf")
OUTPUT_PATH = Path("agente-pesquisador/data/processed/base_conhecimento_extraido.txt")


def extrair_texto_pdf(caminho_pdf: Path) -> list[dict]:
    """Extrai o texto de cada página do PDF."""

    if not caminho_pdf.exists():
        raise FileNotFoundError(
            f"PDF não encontrado: {caminho_pdf.resolve()}"
        )

    leitor = PdfReader(caminho_pdf)
    paginas = []

    for numero, pagina in enumerate(leitor.pages, start=1):
        texto = pagina.extract_text() or ""

        paginas.append({
            "pagina": numero,
            "texto": texto.strip()
        })

    return paginas


def salvar_texto(paginas: list[dict], destino: Path) -> None:
    """Salva o texto extraído, mantendo a separação por página."""

    destino.parent.mkdir(parents=True, exist_ok=True)

    with destino.open("w", encoding="utf-8") as arquivo:
        for pagina in paginas:
            arquivo.write(f"--- PÁGINA {pagina['pagina']} ---\n\n")
            arquivo.write(pagina["texto"])
            arquivo.write("\n\n")

    print(f"Texto salvo em: {destino.resolve()}")


def main():
    paginas = extrair_texto_pdf(PDF_PATH)
    salvar_texto(paginas, OUTPUT_PATH)

    total_caracteres = sum(
        len(pagina["texto"]) for pagina in paginas
    )

    print(f"Páginas encontradas: {len(paginas)}")
    print(f"Caracteres extraídos: {total_caracteres}")

    for pagina in paginas:
        if not pagina["texto"]:
            print(
                f"Aviso: a página {pagina['pagina']} "
                "não contém texto extraído."
            )


if __name__ == "__main__":
    main()
