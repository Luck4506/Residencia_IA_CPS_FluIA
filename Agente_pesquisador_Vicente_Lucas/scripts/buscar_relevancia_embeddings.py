"""Encontra o FAQ mais próximo e pede uma resposta ao Ollama."""
import argparse
import json
import os
from config import PROCESSED, MODEL_NAME, PREFERENCIAS
from extrair_pdf import assinatura
from indexar_base import carregar_modelo, cliente, indexar
from ollama import responder


def buscar_relevancia(pergunta, modelo, top_k=3, preferencia='todos'):
    if not pergunta.strip():
        raise ValueError('Digite uma pergunta.')

    if preferencia not in PREFERENCIAS or not 1 <= top_k <= 10:
        raise ValueError('Confira a preferência e use top-k entre 1 e 10.')

    caminho = PROCESSED / 'indice.json'

    if not caminho.exists():
        raise ValueError('Execute python app.py indexar primeiro.')

    info = json.loads(caminho.read_text())

    if info['assinatura'] != assinatura() or info['modelo'] != MODEL_NAME:
        raise ValueError('A base mudou. Execute python app.py indexar novamente.')

    if len(modelo.tokenizer.encode(pergunta, add_special_tokens=False)) > 120:
        raise ValueError('Faça uma pergunta mais curta, com até 120 tokens.')

    colecao = cliente().get_collection(info['colecao'], embedding_function=None)
    filtro = None if preferencia == 'todos' else {'preferencia': preferencia}
    quantidade = len(colecao.get(where=filtro, include=[])['ids'])

    if not quantidade:
        return []

    # Converte a pergunta em vetor e procura os chunks mais próximos.
    vetor = modelo.encode([pergunta], normalize_embeddings=True).tolist()
    resposta = colecao.query(
        query_embeddings=vetor, n_results=min(top_k, quantidade), where=filtro,
        include=['documents', 'metadatas', 'distances'])
    resultados = []

    for texto, dados, distancia in zip(
            resposta['documents'][0], resposta['metadatas'][0], resposta['distances'][0]):
        resultados.append({'chunk': {**dados, 'texto': texto},
                           'similaridade': 1 - float(distancia)})

    return resultados


def exibir_resultado(resultados, pergunta, usar_ollama=True,
                     modelo_llm='llama3.2:3b', minimo=0.50):
    if not resultados or resultados[0]['similaridade'] < minimo:
        print('Não encontrei uma pergunta suficientemente semelhante.')
        return

    # Somente o primeiro chunk é usado para responder.
    chunk = resultados[0]['chunk']
    print(f"\nChunk utilizado: {chunk['id']}")
    print(f"Similaridade: {resultados[0]['similaridade']:.3f}")
    print(f"PDF: {chunk['arquivo']} | páginas {chunk['pagina_inicio']}–{chunk['pagina_fim']}")
    print(f"Pergunta semelhante: {chunk['pergunta']}")
    if not usar_ollama:
        print(f"\nResposta do FAQ: {chunk['resposta']}")
    print(f"\nReferência do chunk: {chunk['referencia_bibliografica']}")

    if chunk['referencia_ficticia']:
        print('Referência fictícia do PDF Vicente, usada apenas para testes.')

    if usar_ollama:
        print('\nResposta do Ollama:', flush=True)
        print(responder(pergunta, chunk, modelo_llm))


def main():
    parser = argparse.ArgumentParser(description='FAQ Vicente: busca vetorial e Ollama.')
    parser.add_argument('pergunta', nargs='?')
    parser.add_argument('--indexar', action='store_true')
    parser.add_argument('--sem-ollama', action='store_true')
    parser.add_argument('--uma-vez', action='store_true')
    parser.add_argument('--preferencia', choices=PREFERENCIAS, default='todos')
    parser.add_argument('--top-k', type=int, default=3)
    parser.add_argument('--minimo', type=float, default=0.50)
    parser.add_argument('--modelo', default=os.getenv('LLAMA_MODEL', 'llama3.2:3b'))
    args = parser.parse_args()

    try:
        if not -1 <= args.minimo <= 1:
            raise ValueError('Use um limiar entre -1 e 1.')

        # Carrega o modelo uma vez para toda a sessão.
        print('Carregando o modelo de busca...', flush=True)
        modelo = carregar_modelo()

        if args.indexar:
            print(f'{indexar(modelo)} chunks indexados.')

            return 0

        print('Digite sair para encerrar ou pressione Ctrl+C.')
        pergunta = args.pergunta

        while True:
            if pergunta is None:
                pergunta = input('\nSua pergunta: ')

            pergunta = pergunta.strip()

            if pergunta.lower() in {'sair', 'exit'}:
                break

            if not pergunta:
                print('Digite uma pergunta.')
                pergunta = None
                continue

            try:
                resultados = buscar_relevancia(pergunta, modelo, args.top_k, args.preferencia)
                exibir_resultado(resultados, pergunta, not args.sem_ollama, args.modelo, args.minimo)
            except Exception as erro:
                print(f'Erro na consulta: {erro}')

                if args.uma_vez:
                    return 1

            if args.uma_vez:
                break

            pergunta = None

        return 0
    except (EOFError, KeyboardInterrupt):
        return 0
    except Exception as erro:
        print(f'Erro: {erro}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
