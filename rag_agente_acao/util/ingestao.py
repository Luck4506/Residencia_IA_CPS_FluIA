import pymupdf
import re
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb

# Caminhos do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
DB_DIR = BASE_DIR / "data" / "base_conhecimento"
NOME_COLECAO = "bem_estar_digital"

CAMPOS = [
    "CATEGORIA",
    "SITUAÇÃO",
    "ESTRATÉGIA",
    "OBJETIVO",
    "EVIDÊNCIA",
    "ADEQUAÇÃO",
    "RESTRIÇÕES",
    "ALTERNATIVAS",
    "FONTE"
]

MODELO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

def extrair_texto_pdf(caminho_pdf):
    """
    Extrai o texto de todas as páginas de um PDF.
    """

    documento = pymupdf.open(caminho_pdf)

    texto = ""

    for pagina in documento:
        texto += pagina.get_text("text") + "\n"

    documento.close()

    return texto

def separar_chunks(texto):
    """
    Identifica e separa os chunks do texto extraído.
    """

    # Localiza os cabeçalhos: CHUNK 01, CHUNK 02...
    padrao = r"(?im)^\s*CHUNK\s+(\d+)\s*$"

    ocorrencias = list(re.finditer(padrao, texto))

    chunks = []

    for i, ocorrencia in enumerate(ocorrencias):

        numero = int(ocorrencia.group(1))

        inicio = ocorrencia.end()

        # O chunk termina no próximo cabeçalho
        if i + 1 < len(ocorrencias):
            fim = ocorrencias[i + 1].start()
        else:
            fim = len(texto)

        conteudo = texto[inicio:fim].strip()

        chunks.append({
            "id": f"chunk-{numero:03d}",
            "numero": numero,
            "texto": conteudo
        })

    if not chunks:
        raise ValueError("Nenhum chunk foi encontrado no documento.")

    return chunks

def extrair_metadados(texto_chunk):
    """
    Identifica os campos estruturados de um chunk.
    """

    campos = {}

    # Localiza o início de cada campo
    campos_regex = "|".join(map(re.escape, CAMPOS))

    padrao = rf"(?im)^\s*({campos_regex})\s*:\s*"

    ocorrencias = list(re.finditer(padrao, texto_chunk))

    for i, ocorrencia in enumerate(ocorrencias):

        nome = ocorrencia.group(1).lower()

        inicio = ocorrencia.end()

        if i + 1 < len(ocorrencias):
            fim = ocorrencias[i + 1].start()
        else:
            fim = len(texto_chunk)

        valor = texto_chunk[inicio:fim].strip()

        # Remove quebras de linha desnecessárias
        valor = re.sub(r"\s+", " ", valor)

        campos[nome] = valor

    return campos

def encontrar_pdf():
    """
    Localiza o PDF dentro da pasta raw.
    Espera encontrar apenas um documento.
    """

    arquivos = [
        arquivo for arquivo in RAW_DIR.iterdir()
        if arquivo.is_file() and arquivo.suffix.lower() == ".pdf"
    ]

    if len(arquivos) == 0:
        raise FileNotFoundError(
            f"Nenhum PDF encontrado em: {RAW_DIR}"
        )

    if len(arquivos) > 1:
        raise ValueError(
            "Mais de um PDF encontrado. "
            "Defina qual documento deve ser processado."
        )

    return arquivos[0]

def gerar_embeddings(chunks):
    """
    Gera embeddings para todos os chunks utilizando
    o modelo Sentence Transformers.
    """

    print("\nCarregando modelo de embeddings...")

    modelo = SentenceTransformer(MODELO_EMBEDDING)

    textos = [
        chunk["texto"]
        for chunk in chunks
    ]

    print("Gerando embeddings...")

    embeddings = modelo.encode(
        textos,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    return embeddings

def persistir_chroma(chunks, embeddings, nome_pdf):
    """
    Persiste os chunks, embeddings e metadados
    no ChromaDB.
    """

    print("\nConectando ao ChromaDB...")

    cliente = chromadb.PersistentClient(
        path=str(DB_DIR)
    )

    colecao = cliente.get_or_create_collection(
        name=NOME_COLECAO,
        metadata={"hnsw:space": "cosine"}
    )

    ids = []
    documentos = []
    metadados = []

    for chunk in chunks:

        ids.append(chunk["id"])
        documentos.append(chunk["texto"])
        metadata = chunk["metadados"].copy()

        # Informações adicionais
        metadata["numero"] = chunk["numero"]
        metadata["arquivo_origem"] = nome_pdf

        metadados.append(metadata)

    colecao.upsert(
        ids=ids,
        documents=documentos,
        embeddings=embeddings.tolist(),
        metadatas=metadados
    )

    print(f"\nTotal de registros na coleção: {colecao.count()}")
    print(f"Chunks processados: {len(chunks)}")
    print("Persistência concluída!")

    return colecao

def main():
    caminho_pdf = encontrar_pdf()

    print(f"Documento encontrado: {caminho_pdf.name}")

    # 1. Extração do PDF
    texto = extrair_texto_pdf(caminho_pdf)

    print(f"Caracteres extraídos: {len(texto)}")

    # 2. Segmentação dos chunks
    chunks = separar_chunks(texto)

    print(f"Chunks encontrados: {len(chunks)}")

    # 3. Extração dos metadados
    for chunk in chunks:
        chunk["metadados"] = extrair_metadados(
            chunk["texto"]
        )

    # 4. Geração dos embeddings
    embeddings = gerar_embeddings(chunks)

    # 5. Persistência no ChromaDB
    persistir_chroma(
        chunks,
        embeddings,
        caminho_pdf.name
    )

if __name__ == "__main__":
    main()
