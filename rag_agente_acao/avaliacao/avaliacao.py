import json
from datetime import datetime
from pathlib import Path
from util.consulta import ConsultorRAG
from .metricas import avaliar_dataset

# CONFIGURAÇÕES DO EXPERIMENTO
TOP_K = 10
VALORES_K = [3, 4, 5, 10]
THRESHOLD = 0.36 #None # None = sem threshold

CAMINHO_DIAGNOSTICOS = Path("avaliacao/diagnosticos_teste.json")
PASTA_RESULTADOS = Path("avaliacao/resultados")

# 1. CARREGAR DIAGNÓSTICOS
with open(CAMINHO_DIAGNOSTICOS, "r", encoding="utf-8") as arquivo:
    diagnosticos = json.load(arquivo)["diagnosticos"]

# 2. INICIALIZAR O CONSULTOR
consultor = ConsultorRAG()
resultados_por_id = {}
detalhes_por_id = {}

# 3. EXECUTAR AS BUSCAS
for diagnostico in diagnosticos:

    id_diagnostico = diagnostico["diagnostico_id"]

    resultados = consultor.buscar(
        diagnostico["diagnostico"],
        top_k=TOP_K
    )

    # Aplicar threshold, se configurado
    if THRESHOLD is not None:
        resultados = [
            chunk for chunk in resultados
            if chunk["distancia"] <= THRESHOLD
        ]

    # Padronizar os IDs para comparar com o gabarito
    ids = [
        f"CHUNK {int(chunk['id'].split('-')[1]):02d}"
        for chunk in resultados
    ]

    resultados_por_id[id_diagnostico] = ids

    # Guardar os chunks junto com suas distâncias
    detalhes_por_id[id_diagnostico] = [
        f"{id_chunk} - Distância {chunk['distancia']:.4f}"
        for id_chunk, chunk in zip(ids, resultados)
    ]

# 4. CALCULAR AS MÉTRICAS
resultados_avaliacao = {}

for k in VALORES_K:
    avaliacao = avaliar_dataset(
        diagnosticos,
        resultados_por_id,
        k
    )

    for item in avaliacao["resultados_individuais"]:
        item["resultados_recuperados"] = detalhes_por_id[item["diagnostico_id"]][:k]

    resultados_avaliacao[f"top_{k}"] = {
        "medias": avaliacao["medias"],
        "resultados_individuais": avaliacao["resultados_individuais"]
    }


# 5. DEFINIR O NOME DO ARQUIVO
data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

if THRESHOLD is None:
    nome_arquivo = f"baseline_{data_hora}.json"
else:
    nome_arquivo = f"threshold_{THRESHOLD}_{data_hora}.json"
''
# 6. SALVAR RESULTADOS
PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)

dados = {
    "experimento": "baseline" if THRESHOLD is None else "threshold",
    "configuracao": {
        "top_k": TOP_K,
        "valores_k": VALORES_K,
        "threshold": THRESHOLD
    },
    "resultados": resultados_avaliacao
}

caminho_saida = PASTA_RESULTADOS / nome_arquivo

with open(caminho_saida, "w", encoding="utf-8") as arquivo:
    json.dump(dados, arquivo, ensure_ascii=False, indent=4)

print(f"\nAvaliação concluída!")
print(f"Resultados salvos em: {caminho_saida}")
