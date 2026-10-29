# Fluxo e funcionamento do sistema

## 1. O que o projeto faz

O sistema recebe uma pergunta sobre bem-estar digital, procura uma pergunta semelhante no FAQ do Vicente e usa a resposta cadastrada para orientar o Llama, executado pelo Ollama.

Ao responder, o programa mostra o chunk utilizado, a pergunta encontrada, o PDF de origem, as páginas e a referência bibliográfica. A base atual tem oito FAQs, organizados em oito chunks.

O fluxo tem dois momentos: **preparar a base** e **consultar a base**.

## 2. Preparação da base: indexação

Esta etapa é executada pelo comando:

```bash
python app.py indexar
```

O caminho dos dados é:

```text
PDF do Vicente
    ↓
Extrair o texto de cada página
    ↓
Separar os registros de pergunta e resposta
    ↓
Criar um chunk completo para cada FAQ
    ↓
Transformar as perguntas em vetores com MiniLM
    ↓
Salvar vetores, textos e metadados no ChromaDB
```

### Extração do PDF

O arquivo fica em `data/raw/vicente_base_conhecimento.pdf`.

O script `scripts/extrair_pdf.py` usa a biblioteca `pypdf` para extrair o texto, preservando o número de cada página. Também grava uma cópia do texto em `data/processed/`.

### Separação dos chunks

O script `scripts/segmentar_chunks.py` reconhece os campos do formato Vicente:

```text
ID: FAQ-001
PERGUNTA: ...
RESPOSTA: ...
REFERÊNCIA BIBLIOGRÁFICA: ...
FIM DO REGISTRO
```

Cada registro completo vira um chunk. A pergunta não é separada da resposta, mesmo quando o registro começa em uma página e termina em outra.

Um chunk guarda:

| Informação | Para que serve |
| --- | --- |
| ID do chunk | Identificar exatamente o conteúdo recuperado |
| ID do FAQ | Preservar o identificador original do PDF |
| Pergunta | Fazer a comparação com a pergunta do usuário |
| Resposta | Fornecer o conteúdo que será usado pelo Ollama |
| Referência bibliográfica | Mostrar a origem declarada no FAQ |
| Arquivo e páginas | Localizar o registro no PDF |
| Preferência | Permitir filtrar os registros antes da busca |
| Indicação de referência fictícia | Preservar o aviso existente na base do Vicente |

Exemplo de ID:

```text
vicente_base_conhecimento:FAQ-002
```

### Vetores e armazenamento

O script `scripts/indexar_base.py` usa o modelo:

```text
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Esse modelo transforma cada **pergunta cadastrada** em um vetor, uma lista de números utilizada na comparação por significado.

A comparação é feita entre perguntas. A resposta e a referência permanecem associadas ao mesmo chunk no banco.

O ChromaDB salva o índice em `data/chromadb/`. O arquivo `data/processed/indice.json` registra a coleção ativa, o modelo e uma assinatura dos PDFs. Uma nova indexação só substitui a coleção anterior depois de concluir a gravação.

## 3. Consulta: da pergunta até a resposta

A consulta é iniciada com:

```bash
python app.py perguntar
```

O fluxo é:

```text
Usuário digita uma pergunta
    ↓
MiniLM transforma a pergunta em vetor
    ↓
ChromaDB compara esse vetor com os vetores das perguntas cadastradas
    ↓
O programa escolhe o chunk de maior similaridade
    ↓
Confere se a similaridade atinge o limite mínimo
    ↓
Mostra o chunk, a referência e as páginas
    ↓
Envia a pergunta e o conteúdo desse chunk ao Ollama
    ↓
O Llama redige uma resposta com base no FAQ recuperado
    ↓
O programa pede outra pergunta
```

### Como a pergunta semelhante é escolhida

O script `scripts/buscar_relevancia_embeddings.py` consulta o ChromaDB. Por padrão, recupera até três candidatos, ordenados pela distância de cosseno.

O código calcula:

```text
similaridade = 1 - distância
```

Depois usa somente o primeiro candidato, ou seja, o mais semelhante. Os outros candidatos não são enviados ao Ollama.

O limiar padrão é `0.50`. Se o melhor candidato ficar abaixo desse valor, o sistema informa que não encontrou uma pergunta suficientemente semelhante e não chama o Ollama. Esse limite é experimental: similaridade não é uma probabilidade de acerto.

### O que o Ollama recebe

O script `scripts/ollama.py` envia:

- A pergunta do usuário.
- A pergunta cadastrada no chunk.
- A resposta cadastrada no chunk.
- A referência bibliográfica do chunk.

O Llama recebe os **textos**, não os vetores. Também recebe uma instrução para usar somente o FAQ fornecido e reconhecer quando faltam informações.

O modelo padrão de geração é `llama3.2:3b`. Ele é consultado no serviço local `http://localhost:11434/api/chat`.

A fonte e o ID do chunk são mostrados pelo próprio programa, a partir dos dados recuperados. O sistema não depende de o Llama escrever uma citação em um formato específico.

## 4. Exemplo de consulta

Entrada:

```text
Como reduzir distrações durante os estudos?
```

Na consulta verificada durante o desenvolvimento, o sistema recuperou:

```text
Chunk utilizado: vicente_base_conhecimento:FAQ-002
Pergunta semelhante: Que estratégias simples posso experimentar
para reduzir distrações digitais durante o estudo?
PDF: vicente_base_conhecimento.pdf
Página: 1
```

O programa envia a resposta original desse FAQ ao Ollama sem repeti-la na tela. A resposta original só é exibida no modo `recuperar`, sem Ollama. Abaixo dos dados do chunk, mostra a resposta redigida pelo Llama.

O resultado depende da pergunta e da base indexada. O exemplo não representa uma garantia para qualquer consulta.

## 5. Por que há dois modelos?

| Componente | Responsabilidade |
| --- | --- |
| MiniLM, carregado por Sentence Transformers | Criar os vetores usados na busca |
| ChromaDB | Armazenar os vetores e recuperar os chunks |
| Llama, executado pelo Ollama | Redigir a resposta usando o chunk escolhido |

O aplicativo Python coordena essas etapas. O Llama não consulta o ChromaDB sozinho.

Esse é o fluxo RAG: **recuperar um conteúdo externo e fornecê-lo como contexto para gerar a resposta**. Os pesos do Llama não são treinados ou alterados nesta execução.

## 6. O PDF é lido a cada pergunta?

O texto do PDF **não é extraído novamente** durante cada consulta. O conteúdo usado para responder vem do ChromaDB.

Há, porém, uma conferência da assinatura dos PDFs: o programa lê os bytes dos arquivos para verificar se a base mudou. Essa verificação não utiliza `pypdf` nem refaz a segmentação.

Se os PDFs mudarem, o programa pede uma nova indexação:

```bash
python app.py indexar
```

A biblioteca `pypdf` é necessária para extrair e preparar os documentos. Sentence Transformers e ChromaDB são necessários para a busca.

O modelo MiniLM baixado fica em `.cache/huggingface/`, evitando novos downloads. O banco vetorial persiste os vetores, evitando gerá-los novamente para todos os FAQs a cada pergunta. Esses arquivos locais não são memória de conversa do Llama.

## 7. Como funciona o while True

O programa carrega o modelo de busca uma vez e entra no loop:

```text
Pedir uma pergunta → buscar → responder → pedir outra pergunta
```

- Uma entrada vazia é ignorada.
- Um erro de consulta é informado e o loop continua.
- `sair`, `exit` ou `Ctrl+C` encerram a execução.
- `--uma-vez` faz apenas uma consulta e encerra.

Cada pergunta é tratada separadamente. O sistema não envia o histórico das perguntas anteriores ao Ollama.

## 8. Função de cada arquivo

| Arquivo | Função |
| --- | --- |
| `app.py` | Entrada do programa e identificação do comando |
| `scripts/config.py` | Caminhos e configurações compartilhadas |
| `scripts/extrair_pdf.py` | Extração das páginas e assinatura dos PDFs |
| `scripts/segmentar_chunks.py` | Separação dos registros FAQ e localização das páginas |
| `scripts/indexar_base.py` | Geração dos vetores e gravação no ChromaDB |
| `scripts/buscar_relevancia_embeddings.py` | Busca vetorial, seleção do chunk e loop de perguntas |
| `scripts/ollama.py` | Envio do contexto ao Llama e recebimento da resposta |
| `scripts/buscar_relevancia_tfidf.py` | Comparação por palavras, como alternativa de teste |
| `tests/test_integracao.py` | Testes da extração, busca, referências, loop e integração |

O TF-IDF não participa da consulta padrão com Ollama. Ele serve para comparar uma busca por palavras com a busca vetorial.

## 9. Comandos principais

Execute dentro de `Agente_pesquisador_Vicente_Lucas` e ative o ambiente que já tem as bibliotecas instaladas:

```bash
source ../Agente_pesquisador_lucas/.venv/bin/activate
```

Para conversar com o sistema, mantenha o Ollama aberto:

```bash
python app.py perguntar
```

Para atualizar a base:

```bash
python app.py indexar
```

Para consultar sem geração pelo Ollama:

```bash
python app.py recuperar "Como organizar pausas?" --uma-vez
```

Para fazer uma única pergunta ao Ollama:

```bash
python app.py perguntar "Como organizar pausas?" --uma-vez
```

Para testar o projeto:

```bash
python -m unittest discover -s tests -v
```

Todos os FAQs atuais pertencem à preferência `geral`. Portanto, use a consulta sem filtro ou com `--preferencia geral`. Os demais filtros não têm registros nesta base.

## 10. Limitações importantes

O PDF do Vicente contém referências bibliográficas fictícias, identificadas como material de teste. O sistema preserva e mostra esse aviso; elas não são fontes científicas verificadas.

A busca encontra perguntas semelhantes, mas pode selecionar um conteúdo inadequado. O Llama também pode acrescentar uma informação que não aparece no chunk, mesmo recebendo instruções para não fazer isso. Por isso, a resposta deve ser conferida com o FAQ recuperado.

O fato de o programa mostrar uma referência prova de qual registro veio o contexto, mas não garante que toda frase gerada esteja sustentada por ela.
