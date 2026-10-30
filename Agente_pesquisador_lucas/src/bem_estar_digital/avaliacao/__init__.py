"""Avaliação reproduzível; métricas estruturais não atestam fidelidade semântica."""
import csv
import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from ..config import RAIZ, CONFIG
from ..geracao import responder, SEM_EVIDENCIA
from ..recuperacao import recuperar, indexar


def avaliar(embedder, cliente, modelo, base=RAIZ/"data", sem_geracao=False, top_k=5, max_distancia=None):
    casos=json.loads((RAIZ/"evaluation/questions.json").read_text(encoding="utf-8"))
    pasta=RAIZ/"evaluation/results"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    pasta.mkdir(parents=True)
    resultados=[]
    for caso in casos:
        inicio=time.perf_counter()
        chamadas_antes=getattr(cliente,"chamadas",0)
        erro=""
        resposta=""
        trechos=[]
        tempo_busca=0
        try:
            def consultar(base_atual):
                nonlocal tempo_busca
                t=time.perf_counter()
                encontrados=recuperar(caso["pergunta"],embedder,base_atual,top_k,max_distancia)
                tempo_busca=time.perf_counter()-t
                return encontrados
            if caso.get("fixture"):
                # Casos artificiais nunca entram na coleção de conhecimento principal.
                with tempfile.TemporaryDirectory() as tmp:
                    base_teste=Path(tmp)/"data"
                    indexar(RAIZ/"tests/fixtures"/caso["fixture"],embedder,base_teste)
                    trechos=consultar(base_teste)
            else:
                trechos=consultar(base)
            if not sem_geracao:
                resposta=responder(caso["pergunta"],trechos,cliente,modelo)
        except Exception as exc:
            erro=str(exc)
        esperados=set(caso["arquivos_esperados"])
        obtidos={t["arquivo"] for t in trechos}
        registro={**caso,"config":CONFIG,"top_k":top_k,"max_distancia":max_distancia,
            "modelo_llm":modelo,"trechos":trechos,"resposta":resposta,"erro":erro,
            "hit_at_k":bool(esperados & obtidos) if esperados else None,
            "recall_fontes_at_k":len(esperados & obtidos)/len(esperados) if esperados else None,
            "abstencao":resposta==SEM_EVIDENCIA if not sem_geracao else None,
            "segundos_busca":round(tempo_busca,4),"segundos_total":round(time.perf_counter()-inicio,4),
            "chamadas_llm":getattr(cliente,"chamadas",0)-chamadas_antes,
            "fidelidade_manual":"pendente","citacoes_sustentam_manual":"pendente"}
        resultados.append(registro)
        with (pasta/"traces.jsonl").open("a",encoding="utf-8") as f:
            f.write(json.dumps(registro,ensure_ascii=False)+"\n")
    campos=["id","tipo","pergunta","criterio_esperado","hit_at_k","recall_fontes_at_k","abstencao",
            "segundos_busca","segundos_total","chamadas_llm","resposta","erro",
            "fidelidade_manual","citacoes_sustentam_manual"]
    with (pasta/"scorecard.csv").open("w",newline="",encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f,fieldnames=campos,extrasaction="ignore")
        writer.writeheader();writer.writerows(resultados)
    return pasta,resultados
