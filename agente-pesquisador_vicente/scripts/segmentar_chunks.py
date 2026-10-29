import json
import re
from pathlib import Path

# Caminhos dos arquivos
INPUT_PATH = Path("agente-pesquisador/data/processed/base_conhecimento_extraido.txt")
OUTPUT_PATH = Path("agente-pesquisador/data/processed/chunks.json")


def limpar_texto(texto: str) -> str:
    """Remove espaços extras e normaliza quebras de linha."""
    texto = texto.replace("\r\n", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n+", "\n", texto)
    return texto.strip()


def extrair_campo(bloco: str, inicio: str, fim: str) -> str:
    """Extrai o conteúdo entre dois marcadores."""
    padrao = rf"{re.escape(inicio)}\s*(.*?)\s*(?={re.escape(fim)})"

    resultado = re.search(padrao, bloco, flags=re.DOTALL | re.IGNORECASE)

    if not resultado:
        return ""

    return limpar_texto(resultado.group(1))


def segmentar_chunks(texto: str) -> list[dict]:
    """Transforma cada registro FAQ em um chunk independente."""

    # Divide o texto pelo marcador de fim de registro.
    blocos = re.split(
        r"FIM DO REGISTRO",
        texto,
        flags=re.IGNORECASE
    )

    chunks = []

    for bloco in blocos:
        bloco = limpar_texto(bloco)

        # Ignora blocos vazios ou sem identificador.
        if not bloco or not re.search(r"\bID\s*:", bloco, re.IGNORECASE):
            continue

        # Extrai os campos do registro.
        id_faq = extrair_campo(
            bloco, "ID:", "PERGUNTA:"
        )
        pergunta = extrair_campo(
            bloco, "PERGUNTA:", "RESPOSTA:"
        )
        resposta = extrair_campo(
            bloco, "RESPOSTA:", "REFERÊNCIA BIBLIOGRÁFICA:"
        )

        # A referência vai até o final do bloco.
        referencia = re.split(
            r"REFERÊNCIA BIBLIOGRÁFICA\s*:",
            bloco,
            maxsplit=1,
            flags=re.IGNORECASE
        )

        referencia = (
            limpar_texto(referencia[1])
            if len(referencia) == 2
            else ""
        )

        # Registra campos ausentes para revisão posterior.
        campos = {
            "id": id_faq,
            "pergunta": pergunta,
            "resposta": resposta,
            "referencia_bibliografica": referencia,
        }

        campos_ausentes = [
            nome for nome, valor in campos.items() if not valor
        ]

        # Texto completo que poderá ser usado na busca semântica.
        conteudo = (
            f"Pergunta: {pergunta}\n"
            f"Resposta: {resposta}\n"
            f"Referência bibliográfica: {referencia}"
        )

        chunks.append({
            **campos,
            "texto": conteudo,
            "valido": len(campos_ausentes) == 0,
            "campos_ausentes": campos_ausentes,
        })

    return chunks


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {INPUT_PATH.resolve()}"
        )

    texto = INPUT_PATH.read_text(encoding="utf-8")
    chunks = segmentar_chunks(texto)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    validos = sum(chunk["valido"] for chunk in chunks)
    invalidos = len(chunks) - validos

    print(f"Chunks encontrados: {len(chunks)}")
    print(f"Chunks válidos: {validos}")
    print(f"Chunks com campos ausentes: {invalidos}")
    print(f"Arquivo salvo em: {OUTPUT_PATH.resolve()}")

    for chunk in chunks:
        if not chunk["valido"]:
            print(
                f"Aviso: {chunk['id'] or 'ID ausente'} — "
                f"campos ausentes: {chunk['campos_ausentes']}"
            )


if __name__ == "__main__":
    main()
