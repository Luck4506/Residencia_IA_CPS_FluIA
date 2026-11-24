import math

def precision_at_k(resultados, relevantes, k):
    """
    Calcula a Precision@K.

    Mede a proporção de chunks relevantes entre os K
    primeiros resultados recuperados.

    relevantes: dicionário {chunk_id: grau_relevancia}
    """

    if k <= 0:
        raise ValueError("K deve ser maior que zero.")

    recuperados = resultados[:k]

    acertos = sum(
        1 for chunk in recuperados
        if relevantes.get(chunk, 0) > 0
    )

    return acertos / k


def recall_at_k(resultados, relevantes, k):
    """
    Calcula a Recall@K.

    Mede a proporção dos chunks relevantes esperados
    que foram recuperados.

    Retorna None quando não existem chunks relevantes
    no gabarito.
    """

    if k <= 0:
        raise ValueError("K deve ser maior que zero.")

    total_relevantes = sum(
        1 for grau in relevantes.values()
        if grau > 0
    )

    if total_relevantes == 0:
        return None

    recuperados = resultados[:k]

    acertos = sum(
        1 for chunk in recuperados
        if relevantes.get(chunk, 0) > 0
    )

    return acertos / total_relevantes


def reciprocal_rank(resultados, relevantes):
    """
    Calcula o Reciprocal Rank (RR).

    Retorna o inverso da posição do primeiro
    chunk relevante encontrado.

    Retorna 0 quando nenhum chunk relevante é encontrado.
    """

    for posicao, chunk in enumerate(resultados, start=1):

        if relevantes.get(chunk, 0) > 0:
            return 1 / posicao

    return 0.0


def ndcg_at_k(resultados, relevantes, k):
    """
    Calcula o Normalized Discounted Cumulative Gain (nDCG@K).

    Considera o grau de relevância dos chunks e
    suas posições nos resultados recuperados.

    Utiliza ganho exponencial:
    2^relevancia - 1

    Retorna None quando não existem chunks relevantes.
    """

    if k <= 0:
        raise ValueError("K deve ser maior que zero.")

    # Ordenação real dos resultados
    recuperados = resultados[:k]

    dcg = 0.0

    for posicao, chunk in enumerate(recuperados, start=1):

        relevancia = relevantes.get(chunk, 0)

        ganho = (2 ** relevancia) - 1

        desconto = math.log2(posicao + 1)

        dcg += ganho / desconto

    # Melhor ordenação possível (IDCG)
    melhores_relevancias = sorted(
        relevantes.values(),
        reverse=True
    )[:k]

    idcg = 0.0

    for posicao, relevancia in enumerate(
        melhores_relevancias,
        start=1
    ):

        ganho = (2 ** relevancia) - 1

        desconto = math.log2(posicao + 1)

        idcg += ganho / desconto

    if idcg == 0:
        return None

    return dcg / idcg


def avaliar_diagnostico(resultados, relevantes, k):
    """
    Executa todas as métricas para um diagnóstico.

    Retorna um dicionário com os resultados.
    """

    return {
        "precision": precision_at_k(resultados, relevantes, k),
        "recall": recall_at_k(resultados, relevantes, k),
        "mrr": reciprocal_rank(resultados[:k], relevantes),
        "ndcg": ndcg_at_k(resultados, relevantes, k)
    }


def avaliar_dataset(diagnosticos, resultados_por_id, k):
    """
    Avalia um conjunto de diagnósticos.

    diagnosticos:
        Lista de diagnósticos carregados do JSON.

    resultados_por_id:
        Dicionário contendo os resultados recuperados
        para cada diagnóstico.

    k:
        Quantidade de chunks considerados na avaliação.

    Retorna:
        Resultados individuais e médias das métricas.
    """

    resultados_individuais = []

    metricas_acumuladas = {
        "precision": [],
        "recall": [],
        "mrr": [],
        "ndcg": []
    }

    for diagnostico in diagnosticos:

        diagnostico_id = diagnostico["diagnostico_id"]

        relevantes = diagnostico["chunks_relevantes"]

        recuperados = resultados_por_id.get(
            diagnostico_id, []
        )

        metricas = avaliar_diagnostico(
            recuperados,
            relevantes,
            k
        )

        resultados_individuais.append({
            "diagnostico_id": diagnostico_id,
            "resultados_recuperados": recuperados[:k],
            **metricas
        })

        for nome, valor in metricas.items():

            # Métricas indefinidas não entram na média
            if valor is not None:
                metricas_acumuladas[nome].append(valor)

    # Calcula a média das métricas
    medias = {}

    for nome, valores in metricas_acumuladas.items():

        if valores:
            medias[nome] = sum(valores) / len(valores)
        else:
            medias[nome] = None

    return {
        "k": k,
        "total_diagnosticos": len(diagnosticos),
        "resultados_individuais": resultados_individuais,
        "medias": medias
    }
