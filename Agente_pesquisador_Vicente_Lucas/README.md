# Agente pesquisador Vicente + Lucas

Veja [o fluxo e a explicação do sistema](FLUXO_SISTEMA.md).

Versão simplificada: usa **somente o FAQ do Vicente**, com oito chunks. O MiniLM encontra a pergunta semelhante e o Ollama redige a resposta usando o chunk escolhido. O programa mostra o ID, a fonte e as páginas do PDF.

## Rodar

Dentro desta pasta, ative o ambiente já instalado:

```bash
source ../Agente_pesquisador_lucas/.venv/bin/activate
python app.py perguntar
```

Mantenha o Ollama aberto e o modelo `llama3.2:3b` instalado. Se necessário, baixe com `ollama pull llama3.2:3b`.

O `while True` pede uma nova pergunta após cada resposta. Digite `sair` ou pressione `Ctrl+C` para encerrar. As perguntas são independentes, sem histórico de conversa.

Para uma única pergunta:

```bash
python app.py perguntar "Como reduzir distrações nos estudos?" --uma-vez
```

Para mostrar a resposta original do FAQ, sem chamar o Ollama:

```bash
python app.py recuperar "Como reduzir distrações nos estudos?" --uma-vez
```

## Atualizar o PDF

Coloque o PDF em `data/raw/` e execute:

```bash
python app.py indexar
```

Use o formato do Vicente em cada registro:

```text
ID: FAQ-001
PERGUNTA: ...
RESPOSTA: ...
REFERÊNCIA BIBLIOGRÁFICA: ...
FIM DO REGISTRO
```

Cada FAQ vira um chunk inteiro, mesmo que atravesse páginas. O índice no ChromaDB guarda os vetores das perguntas e os textos dos chunks. Na consulta, o texto é recuperado do ChromaDB; o PDF não é extraído novamente. O arquivo original é apenas conferido por assinatura para detectar alterações. A biblioteca `pypdf` só é importada na extração/indexação. Alterações na base exigem reindexação. O modelo baixado fica no cache local.

## Código

- `app.py`: inicia o programa e mantém os comandos do terminal.
- `scripts/extrair_pdf.py`: lê as páginas do PDF.
- `scripts/segmentar_chunks.py`: separa os FAQs e identifica suas páginas.
- `scripts/indexar_base.py`: cria e salva os vetores no ChromaDB.
- `scripts/buscar_relevancia_embeddings.py`: busca o chunk e executa o loop.
- `scripts/ollama.py`: envia a pergunta e o chunk para o Llama.
- `scripts/buscar_relevancia_tfidf.py`: busca por palavras para comparação.

Há comentários curtos no código. A fonte é mostrada pelo programa a partir do chunk original; o Llama não precisa devolver uma estrutura JSON de citações. Isso simplifica a geração e evita o erro anterior de formatação das referências. A associação ao chunk não garante que toda frase gerada esteja correta: confira a resposta com o FAQ.

O PDF do Vicente contém **referências fictícias para testes**, que continuam sinalizadas. O limiar de similaridade padrão é 0,50, experimental; abaixo dele não há chamada ao Ollama. Use `--minimo` para ajustá-lo. Todos os FAQs atuais são `geral`; os filtros de preferência foram mantidos por compatibilidade.

## Instalação independente e testes

Use Python 3.11 ou 3.12:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Os projetos originais foram preservados. As bibliotecas e o Ollama são dependências externas; o código deste projeto não importa arquivos das outras pastas.
