from typing import List
from schemas import AlertAnalysisInput, AlertAnalysisOutput, RagChunk


MIN_RAG_SCORE = 0.65


def _extract_valid_citations(
    status: str, chunks: List[RagChunk], limitations: List[str]
) -> List[dict]:
    if status == "error":
        limitations.append(
            "Falha na consulta ao RAG; análise realizada sem novas evidências da base."
        )
        return []

    if status == "empty" or not chunks:
        limitations.append(
            "Nenhuma referência encontrada na base de conhecimento para este alerta."
        )
        return []

    relevant_chunks = [c for c in chunks if c.score >= MIN_RAG_SCORE]
    if not relevant_chunks:
        limitations.append(
            f"Trechos recuperados ficaram abaixo do limiar de relevância ({MIN_RAG_SCORE}); referências descartadas."
        )
        return []

    citations = []
    for chunk in relevant_chunks:
        citations.append({
            "chunk_id": chunk.chunk_id,
            "source": chunk.source,
            "section": chunk.section or "Não especificada",
            "relevance_score": chunk.score,
            "excerpt": chunk.content,
        })
    return citations


def analyze_alert(data: AlertAnalysisInput) -> AlertAnalysisOutput:
    limitations: List[str] = []
    supporting_data: List[str] = []

    # 1. Verifica disponibilidade de dados de perfil, metas e uso
    has_profile = bool(data.user_profile)
    has_goals = bool(data.user_goals)
    has_usage = bool(data.usage_data)

    if not has_profile:
        limitations.append("Dados de perfil do usuário não informados.")
    if not has_goals:
        limitations.append("Metas do usuário não configuradas; avaliação sem meta explícita.")
    if not has_usage:
        limitations.append("Dados de uso insuficientes para comparar com o alerta.")

    # 2. Recupera e valida fontes do RAG (mantendo rastreabilidade)
    citations = _extract_valid_citations(data.rag_status, data.rag_chunks, limitations)

    # 3. Avalia validade e importância com base nos dados disponíveis
    screen_today = data.usage_data.get("screen_minutes_today")
    screen_goal = data.user_goals.get("daily_screen_goal_minutes")
    late_night_min = data.usage_data.get("late_night_minutes")
    sleep_target = data.user_profile.get("sleep_target_time")

    if screen_today is not None:
        supporting_data.append(f"Uso de tela registrado hoje: {screen_today} min")
    if screen_goal is not None:
        supporting_data.append(f"Meta diária de tela: {screen_goal} min")
    if late_night_min is not None:
        supporting_data.append(f"Uso tardio/noturno registrado: {late_night_min} min")
    if sleep_target is not None:
        supporting_data.append(f"Horário alvo de sono no perfil: {sleep_target}")

    # Caso crítico: não há dado de uso nenhum para sustentar o alerta
    if not has_usage:
        return AlertAnalysisOutput(
            alert_id=data.alert_id,
            is_valid=False,
            importance="baixa",
            conclusion="Não é possível validar a importância do alerta por falta de dados de uso.",
            justification="O alerta foi recebido, mas não há registros de uso suficientes para confirmar a situação.",
            supporting_data=supporting_data,
            citations=citations,
            limitations=limitations,
        )

    exceeded_goal = (
        screen_today is not None
        and screen_goal is not None
        and screen_today > screen_goal
    )
    heavy_late_usage = late_night_min is not None and late_night_min >= 45

    if exceeded_goal and heavy_late_usage:
        is_valid = True
        importance = "alta"
        conclusion = "Alerta válido e de alta importância: houve excesso de tela frente à meta e uso prolongado no período noturno."
        justification = (
            f"O uso de {screen_today} min ultrapassou a meta de {screen_goal} min e houve {late_night_min} min "
            f"de uso noturno (meta de sono: {sleep_target or 'não definida'})."
        )
    elif exceeded_goal or heavy_late_usage:
        is_valid = True
        importance = "media" if has_goals else "baixa"
        conclusion = "Alerta válido com importância moderada/ajustada conforme os dados disponíveis."
        justification = (
            f"Foi identificado o evento '{data.alert_summary}' com base nos registros disponíveis, "
            "porém sem todos os indicadores críticos simultâneos ou com metas parciais."
        )
    else:
        is_valid = False
        importance = "baixa"
        conclusion = "Alerta com baixa relevância no contexto atual do usuário."
        justification = (
            "Os dados registrados não indicam desvio severo frente às metas ou padrões observados."
        )

    return AlertAnalysisOutput(
        alert_id=data.alert_id,
        is_valid=is_valid,
        importance=importance,
        conclusion=conclusion,
        justification=justification,
        supporting_data=supporting_data,
        citations=citations,
        limitations=limitations,
    )