from pprint import pprint
from Residencia_IA_CPS_FluIA.analise_alerta.schemas import AlertAnalysisInput, RagChunk
from Residencia_IA_CPS_FluIA.analise_alerta.analista import analyze_alert


# Cenário 1: Alerta válido + metas + uso + RAG confiável com fonte
cenario_completo = AlertAnalysisInput(
    alert_id="alrt-101",
    alert_type="late_night_screen",
    alert_summary="Uso de tela por 70 min tarde da noite",
    user_profile={"sleep_target_time": "23:00"},
    user_goals={"daily_screen_goal_minutes": 180},
    usage_data={"screen_minutes_today": 230, "late_night_minutes": 70},
    rag_status="ok",
    rag_chunks=[
        RagChunk(
            chunk_id="c-01",
            source="guia_higiene_sono_bem_estar.pdf",
            section="Uso de telas à noite",
            score=0.91,
            content="Exposição prolongada a telas no período noturno pode atrasar o sono e reduzir o descanso.",
        )
    ],
)

# Cenário 2: Falta de meta + falha no RAG (mostrando fallback e limitações)
cenario_fallback = AlertAnalysisInput(
    alert_id="alrt-102",
    alert_type="late_night_screen",
    alert_summary="Uso de tela por 50 min à noite",
    user_profile={},
    user_goals={},
    usage_data={"screen_minutes_today": 150, "late_night_minutes": 50},
    rag_status="error",
    rag_chunks=[],
)

# Cenário 3: RAG retornou trecho com baixa relevância (deve descartar e avisar)
cenario_baixa_relevancia = AlertAnalysisInput(
    alert_id="alrt-103",
    alert_type="late_night_screen",
    alert_summary="Uso de tela por 50 min à noite",
    user_profile={"sleep_target_time": "23:00"},
    user_goals={"daily_screen_goal_minutes": 180},
    usage_data={"screen_minutes_today": 200, "late_night_minutes": 50},
    rag_status="ok",
    rag_chunks=[
        RagChunk(
            chunk_id="c-99",
            source="alongamento_escritorio.pdf",
            section="Postura",
            score=0.25,
            content="Alongar os ombros a cada hora ajuda na postura.",
        )
    ],
)


if __name__ == "__main__":
    print("=== CENÁRIO 1: COMPLETO COM FONTE ===")
    pprint(analyze_alert(cenario_completo).__dict__)

    print("\n=== CENÁRIO 2: COM FALLBACK (SEM META + ERRO NO RAG) ===")
    pprint(analyze_alert(cenario_fallback).__dict__)

    print("\n=== CENÁRIO 3: RAG COM BAIXA RELEVÂNCIA ===")
    pprint(analyze_alert(cenario_baixa_relevancia).__dict__)