# Recebimento de alertas pelo Agente Analista

## Fluxo

1. O script monitora continuamente os dados de uso. No protótipo, `monitor.py` relê `configuracao.json` e `uso.json` a cada ciclo.
2. Quando o uso fora do foco supera o limite, o monitor emite um alerta por episódio. Cada leitura continua seguindo a saída usual do monitor.
3. Com `--analista USUARIO_ID`, o monitor converte o evento de alerta para o contrato abaixo e chama `analista.receber_alerta` no mesmo processo.
4. O Analista valida o objeto. Se estiver completo e válido, a análise começa na etapa `consulta_contexto` com usuário, motivo, período e evidências do alerta. Caso haja erros, o retorno identifica os campos que precisam de correção.

## Contrato de entrada

O script passa um objeto Python, por exemplo um `dict` obtido de um JSON. O objeto deve conter estes campos.

| Campo | Tipo | Obrigatório | Significado |
| --- | --- | --- | --- |
| `usuario_id` | Texto não vazio | Sim | Identificador do usuário associado ao alerta. |
| `script_origem` | Texto não vazio | Sim | Identificador do script emissor, por exemplo `monitor_foco`. |
| `motivo` | Texto não vazio | Sim | Condição observada pelo script que motivou o alerta. |
| `horario_alerta` | Texto ISO 8601 com fuso | Sim | Instante em que o script emitiu o alerta. |
| `periodo_uso.inicio` | Texto ISO 8601 com fuso | Sim | Início do intervalo de uso observado. |
| `periodo_uso.fim` | Texto ISO 8601 com fuso | Sim | Fim do intervalo observado, posterior ao início. |
| `indicadores` | Objeto com valores numéricos finitos | Não | Evidências opcionais, em unidades indicadas nas chaves, como `minutos_excedidos`. |

Use `Z` ou um deslocamento como `-03:00` nos horários. No monitor de foco, o fim do intervalo é `atualizado_em`, o instante até o qual o uso foi medido. O fim planejado da sessão pode ser posterior a esse instante.

Objetos com campos extras ou tipos inválidos também são rejeitados. Quando omitidos, os indicadores são representados por `{}` no contexto da análise.

## Retorno

- `analise_iniciada` inclui `analise`, com a etapa `consulta_contexto` e os dados validados prontos para a futura consulta ao perfil e às metas.
- `rejeitado` inclui `erros`, cada um com `campo`, `codigo` e `mensagem`. O período usa caminhos como `periodo_uso.fim` e a validação pode indicar vários problemas na mesma chamada.

## Exemplos de chamadas

Com o ambiente Python do protótipo ativado, execute na pasta `simples_langchain/`. Os [exemplos JSON](tests/fixtures/alertas_analista.json) são os mesmos usados nos testes.

```bash
python - <<'PY'
import json
from pathlib import Path
from analista import receber_alerta

exemplos = json.loads(Path('tests/fixtures/alertas_analista.json').read_text(encoding='utf-8'))
for nome, alerta in exemplos.items():
    print(nome, json.dumps(receber_alerta(alerta), ensure_ascii=False))
PY
```

| Exemplo | Resultado esperado |
| --- | --- |
| `valido` | `analise_iniciada`, com usuário, motivo e período identificados. |
| `incompleto` | `rejeitado`, com `usuario_id` e `periodo_uso.fim` ausentes. |
| `invalido` | `rejeitado`, com motivo vazio, fuso ausente e período invertido. |

Para exercitar a ligação com o monitor contínuo, use os dados simulados do protótipo.

```bash
python monitor.py --intervalo 1 --analista usuario-teste-01
```

Ao ultrapassar o limite configurado, procure a linha JSON com `tipo` igual a `resultado_analista`. O identificador informado vale para os alertas daquela execução do monitor.
