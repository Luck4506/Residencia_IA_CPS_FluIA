# Passo 4 — acompanhamento independente do chat

Agora há duas entradas:

- `python agente.py`: conversa com o modelo local e altera a configuração.
- `python monitor.py`: acompanha os arquivos e avisa sozinho, mesmo sem chat aberto.

## Teste editando arquivos

Na pasta do projeto:

```bash
source .venv/bin/activate
python monitor.py
```

O monitor relê os dois JSONs a cada 5 segundos. Para testar mais rápido:

```bash
python monitor.py --intervalo 1
```

1. Abra `configuracao.json` e confira seu `limite_distracao`.
2. Abra `uso.json`. Inicialmente há Docs 20, Instagram 10 e YouTube 3 minutos.
3. Com Docs relacionado ao foco, isso representa **13 minutos de distração**.
4. Edite YouTube para `25` e salve: a próxima leitura encontrará **35 minutos**.
5. Se o limite estiver em 30, aparecerá um evento `"tipo": "alerta"`, sem mensagem no chat.
6. Você também pode editar o limite ou os apps relacionados diretamente no JSON.

Esses exemplos pressupõem que só Docs seja relacionado. O monitor sempre usa sua
configuração atual; não a substitui pelos valores do exemplo. `Ctrl+C` encerra.

## Como conferir que ele realmente leu

Cada ciclo imprime uma linha JSON de `"tipo": "leitura"`, contendo:

- horário e caminhos dos arquivos;
- `configuracao_lida` e `uso_lido`, exatamente os valores usados na avaliação;
- `minutos_distraidos` e `ultrapassou`.

Quando ultrapassa, imprime também `"tipo": "alerta"`, com objetivo, uso, limite,
motivo e mensagem. Para guardar o registro em arquivo:

```bash
python monitor.py > monitor.log
```

O monitor **não escreve nos arquivos** e não inventa aumentos de uso.
`uso.json` contém **totais acumulados na mesma janela fictícia de 60 minutos**:
ler 13 minutos dez vezes continua sendo 13 minutos, nunca 130.
Os valores por app devem ser números finitos entre 0 e 60; os nomes devem ser preenchidos.
Este formato ainda é simplificado e não é o formato bruto do Android.

## Quando o alerta aparece

- Dispara quando `minutos_distraidos > limite_distracao`.
- Também dispara se o monitor já inicia acima do limite.
- Enquanto continuar acima, não repete o alerta a cada leitura.
- Ao voltar ao limite ou abaixo, rearma; uma nova ultrapassagem gera outro alerta.
- Essa memória dura só enquanto o monitor está aberto. Reiniciar acima do limite gera novo alerta.
- JSON incompleto, ausente ou inválido gera `erro_leitura`. O monitor não assume zero,
  não apaga o arquivo e tenta novamente no próximo ciclo, sem rearmar o alerta.

A saída inicial é o **terminal**, independente do chat. A função `imprimir_evento`
é o ponto de saída: `MonitorFoco(emitir=outra_funcao)` permite ligar uma notificação,
uma fila ou outro agente depois. Não há notificação do macOS nesta etapa.
O monitor não usa LLM; o alerta tem texto fixo e funciona sem Ollama. Ele fica ativo
somente enquanto o processo estiver rodando, não é um serviço instalado no sistema.

## Chat e configuração persistente

```bash
python agente.py
```

O Ollama precisa estar aberto e ter `qwen2.5:3b` instalado (`ollama pull qwen2.5:3b`).
Diga **“Mude meu limite para 30 minutos”**. A ferramenta salva em `configuracao.json`;
o monitor perceberá isso na próxima leitura. O chat também passou a ler `uso.json`
quando você pergunta sobre seu foco. Não há mais totais de uso fixos no código.

`consultar_configuracao` lê o plano, `atualizar_configuracao` salva apenas os campos
solicitados, e `verificar_foco` relê ambos os JSONs para calcular o resultado.
Campo omitido ou `null` preserva o valor atual; `apps_de_foco: []` significa nenhum
app relacionado. A configuração permanece após fechar o chat; o histórico não.
O modelo pode interpretar um pedido incorretamente: o arquivo registra os valores
que foram realmente salvos.

Os caminhos padrão são relativos aos scripts, não à pasta do terminal. Para testar
outros arquivos sem alterar os seus, o monitor aceita `--configuracao CAMINHO --uso CAMINHO`.
Evite salvar a configuração no editor e no chat ao mesmo tempo: a última gravação vence.
Os arquivos são lidos separadamente, não como uma transação única.

## Arquivos

- `agente.py`: validação, leitura, avaliação e conversa LangChain.
- `configuracao.json`: objetivo, tolerância e apps relacionados.
- `uso.json`: totais de uso editáveis, que futuramente virão de um coletor.
- `monitor.py`: loop de leitura, registro e emissão de alertas.
- `tests/`: testes em arquivos temporários, incluindo um monitor real em outro processo.

```bash
python -m pytest tests -q
```

Não há coleta Android, janela de horário real ou redefinição automática diária nesta
etapa. Os totais pertencem à mesma janela simulada; para testar outra, edite os valores.
As versões anteriores estão em `old/`. O comando antigo `focus-agent` executa a versão
arquivada; use `python agente.py` ou `python monitor.py`.
