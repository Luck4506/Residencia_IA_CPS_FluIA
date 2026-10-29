# Agente de foco

Agente local que acompanha um plano de foco salvo em JSON. Há dois programas:

- `python agente.py` conversa com um modelo no Ollama e pode alterar a configuração.
- `python monitor.py` relê os arquivos e avisa no terminal quando o uso fora do foco passa do limite. Funciona sem chat e sem Ollama.

Os minutos em `uso.json` são um exemplo, numa janela fictícia de 60 minutos. Este projeto não coleta o uso real do celular.

## Requisitos

- Python 3.11 ou superior
- [Ollama](https://ollama.com) em execução, apenas para o chat
- O modelo `qwen2.5:3b`

## Instalação

Na pasta `simples_langchain`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "langchain>=1.0,<2" "langchain-ollama>=1.0,<2" "pydantic>=2.7,<3" "pytest>=8,<10"
ollama pull qwen2.5:3b
```

No Windows, ative o ambiente com `.venv\Scripts\activate`.

Deixe o Ollama aberto antes de iniciar o chat. O agente usa `http://127.0.0.1:11434`.

## Arquivos de configuração

`configuracao.json` guarda o plano:

- `objetivo`: o que a pessoa quer fazer
- `limite_distracao`: minutos aceitos fora do foco, de 0 a 60
- `apps_de_foco`: apps que contam como foco. Os demais contam como distração

`uso.json` guarda os minutos acumulados de cada app. Cada valor fica entre 0 e 60. O exemplo do repositório é Docs 20, Instagram 10 e YouTube 3. Com só Docs relacionado ao foco, a distração é 13 minutos. O limite de exemplo é 30, então ainda não há alerta.

Os programas leem os JSON que estão na mesma pasta dos scripts. Para usar outros arquivos:

```bash
python monitor.py --configuracao CAMINHO --uso CAMINHO
```

## Conversar com o agente

Com o ambiente ativado e o Ollama aberto:

```bash
python agente.py
```

Digite `/sair` para encerrar. A conversa existe só enquanto o programa está aberto. O que for alterado permanece em `configuracao.json`.

Exemplos do que dizer:

- `Mude meu limite para 30 minutos`
- `Como está meu foco?`

Se não houver resposta, confira se o Ollama está aberto e se `qwen2.5:3b` foi baixado.

## Acompanhar sem chat

```bash
python monitor.py
```

A cada 5 segundos o monitor imprime uma linha JSON com `"tipo": "leitura"`. Para observar mais rápido:

```bash
python monitor.py --intervalo 1
```

`Ctrl+C` encerra. O monitor só lê os arquivos. Para ver um alerta com os valores de exemplo, mude `YouTube` para `25` em `uso.json` e salve. A leitura seguinte encontra 35 minutos de distração e, com limite 30, imprime `"tipo": "alerta"`.

O alerta sai quando os minutos fora dos apps de foco passam do limite, inclusive se o monitor já abrir nessa situação. Enquanto o uso continuar acima, o aviso não se repete. Depois que o uso volta ao limite ou abaixo, uma nova ultrapassagem gera outro alerta. JSON ausente ou inválido gera `"tipo": "erro_leitura"` e a tentativa seguinte acontece no próximo ciclo.

Para guardar a saída:

```bash
python monitor.py > monitor.log
```

## Testes

Na mesma pasta, com o ambiente ativado:

```bash
python -m pytest tests -q
```

## Arquivos

- `agente.py`: conversa, validação e avaliação do foco
- `monitor.py`: leitura periódica e alerta no terminal
- `configuracao.json`: objetivo, limite e apps de foco
- `uso.json`: minutos acumulados por app
- `tests/`: testes do monitor e da configuração
