# Residencia_IA_CPS_TIME_07

## Fluxo atual: FAQ com preferência por dispositivo

A versão simplificada segue a estrutura da imagem em [agente_pesquisador/](agente_pesquisador/README.md). O novo PDF contém oito perguntas e respostas com fontes. Use:

```bash
source .venv/bin/activate
python app.py indexar
python app.py recuperar "Como pausar aplicativos no celular?" --preferencia android
python app.py perguntar "Como pausar aplicativos no celular?" --preferencia android
```

`recuperar` mostra a resposta original; `perguntar` redige com Llama via Ollama. O filtro é estrito por dispositivo. A similaridade encontra candidatos, não garante relevância. O modo interativo direto abre com `python app.py`.

A documentação abaixo registra o fluxo documental anterior; para os comandos de consulta e indexação atuais, siga o README do FAQ acima. O código anterior de avaliação foi preservado.

## Fluxo documental anterior - referência

Protótipo de **LLM + RAG** para consultar documentos sobre distrações, estudos e recursos de organização digital. O projeto foi adaptado às sete etapas do documento **Agente Pesquisador - RAG** fornecido pela dupla.

O roteiro indica Gemini na geração. Por solicitação do projeto, essa parte foi substituída por **Llama 3.2 da Meta via Ollama local**. A preparação de PDFs, os embeddings **multilingual-e5-small**, o **ChromaDB** e a avaliação separada da recuperação seguem a proposta do roteiro.

## Instalação

Use **Python 3.11 ou 3.12**. O ambiente local foi preparado com Python 3.12; o Python 3.15 instalado no sistema não é o ambiente validado para estas dependências.

Se a pasta `.venv` já existir, ative-a:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Para reproduzir o ambiente do zero, instale o Python 3.12 se necessário e execute:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

`requirements.txt` fixa as dependências principais. `requirements.lock.txt` registra todas as versões do ambiente de testes macOS/Python 3.12. Para reproduzir integralmente esse ambiente, use `python -m pip install -r requirements.lock.txt`.

Instale e abra o [Ollama](https://ollama.com/download/mac), depois baixe o modelo de geração:

```bash
ollama pull llama3.2:3b
```

Não é necessária uma chave de API. O modelo E5 é baixado automaticamente na primeira execução e armazenado em `.cache/huggingface/`. As execuções seguintes reutilizam esse cache. O `embeddinggemma` da versão anterior não é utilizado pelo novo fluxo.

## Executar por etapas

Dentro da pasta do projeto, com o ambiente ativado:

### 1. Preparar e inspecionar documentos

```bash
python app.py preparar
```

Extrai o conteúdo, limpa o texto e grava `data/processed/documents.jsonl` e `chunks.jsonl`. Exibe uma amostra para a dupla conferir se definições e explicações continuam compreensíveis. Não cria uma coleção vetorial nem consulta o Llama.

### 2. Indexar

```bash
python app.py indexar
```

Gera embeddings e cria uma coleção local persistente no ChromaDB. Um manifesto aponta para a coleção ativa. A reindexação usa uma nova coleção temporária e só troca a ativa após concluir; se falhar, preserva a coleção anterior. Os IDs dos trechos são estáveis por conteúdo, arquivo, página e seção.

### 3. Avaliar somente a recuperação

```bash
python app.py recuperar "Só receber um aviso de mensagem já pode me distrair?"
```

Exibe cinco trechos por padrão, com distância, documento, página quando houver, seção, ID e URL. Não usa o Ollama. Distâncias de cosseno menores indicam maior proximidade; não são uma garantia de relevância.

### 4. Fazer uma pergunta ao agente

Com o aplicativo Ollama aberto:

```bash
python app.py perguntar "Quais hábitos podem ajudar a reduzir distrações durante os estudos?" --mostrar-trechos
```

O Llama recebe a pergunta e os trechos recuperados e devolve JSON com afirmações e IDs de fontes, limitado por um esquema enviado ao Ollama. O programa valida os IDs e monta as citações `[T1]`, `[T2]` etc. Se o formato for inválido, solicita uma correção automática uma única vez. O terminal identifica os documentos, páginas e seções correspondentes. Os identificadores de citação valem somente para aquela consulta.

Cada pergunta é independente; não há memória de conversa.

### 5. Executar a avaliação

Somente busca, sem Ollama:

```bash
python app.py avaliar --sem-geracao
```

Busca e geração:

```bash
python app.py avaliar
```

São nove casos: pergunta direta, paráfrase, perguntas específicas, ausência de evidência, contradição e instrução maliciosa. Os dois últimos usam coleções temporárias com textos explicitamente fictícios, separados da base principal.

Os resultados ficam em `evaluation/results/<execucao>/`:

- `traces.jsonl`: pergunta, critério esperado, trechos, distâncias, resposta, configuração, erros e tempos.
- `scorecard.csv`: planilha de comparação e campos de revisão humana.

`hit_at_k` indica se alguma fonte esperada foi recuperada; `recall_fontes_at_k` mede a proporção dos arquivos esperados encontrados. Campos sem fonte esperada ficam vazios. Abstenção é comparada ao texto padrão, sem garantir por si só que a decisão foi correta. Fidelidade e sustentação das citações ficam **pendentes de revisão manual**.

O tempo total dos casos artificiais inclui a criação da coleção temporária e não deve ser comparado diretamente ao tempo de uma pergunta comum. `segundos_busca` registra apenas a recuperação. As chamadas ao Llama são locais; não há tarifa de API configurada, mas existem custos de processamento e energia não estimados.

## Documentos e fontes

A coleção inicial tem **cinco documentos curtos em português**, com sínteses de dois artigos e três documentações oficiais. O cadastro `data/sources.csv` registra origem, título, autoria, data quando disponível, tipo, localização original, acesso e observações. As sínteses não são cópias integrais dos materiais e aguardam revisão da dupla.

| Arquivo | Origem | Tema |
| --- | --- | --- |
| `notificacoes.txt` | Stothart, Mitchum e Yehnert, 2015 | Notificações e atenção |
| `interrupcoes.txt` | Mark, Gudith e Klocke, 2008 | Interrupções e custos percebidos |
| `android.txt` | Google | Temporizadores e modo de foco |
| `mac.txt` | Apple | Tempo de Uso |
| `windows.txt` | Microsoft | Foco e Não perturbe |

Para adicionar materiais, coloque PDFs com texto selecionável, TXT ou Markdown em `data/raw/`, cadastre-os em `data/sources.csv` e execute `preparar` e `indexar`. Páginas sem texto extraível geram aviso de possível necessidade de OCR; OCR automático ainda não está implementado. Fontes não cadastradas recebem metadados mínimos, sem autoria ou URL inventadas.

Não coloque o roteiro da atividade na base de bem-estar digital: ele orienta o desenvolvimento, não fornece evidências sobre o tema.

### PDF didático criado anteriormente

O guia está preservado em [output/pdf/bem_estar_digital_base.pdf](output/pdf/bem_estar_digital_base.pdf). Agora pode ser lido **diretamente como PDF**, sem a antiga cópia TXT intermediária. Para testar uma coleção separada com ele:

```bash
python app.py indexar --documentos output/pdf --base data/demo
python app.py recuperar "Como organizar uma sessão de estudo?" --base data/demo
python app.py perguntar "Como organizar uma sessão de estudo?" --base data/demo
```

O guia é material didático gerado para demonstração, não uma fonte científica independente. A base de demonstração é criada sob demanda em outro diretório para preservar a coleção principal. Seus arquivos gerados podem ser removidos após o teste.

## Configuração documentada

| Parâmetro | Valor inicial |
| --- | --- |
| Embeddings | `intfloat/multilingual-e5-small`, Sentence Transformers; revisão fixada em `config.py` |
| Prefixo de documento / pergunta | `passage: ` / `query: ` |
| Chunk | Até 350 tokens do tokenizer E5 |
| Sobreposição | Até 50 tokens dentro da mesma seção/página |
| Estratégia | Parágrafos e seções; frases longas divididas somente quando necessário |
| Persistência | ChromaDB local com distância de cosseno |
| Recuperação | `top_k=5` |
| Limiar | Sem corte fixo por padrão; calibrar nos testes |
| Geração | `llama3.2:3b`, Ollama, temperatura zero |

Documentos ou seções menores geram chunks menores, sem preenchimento artificial. Não há sobreposição entre páginas ou seções distintas. Cabeçalhos/rodapés repetidos nas bordas de páginas PDF são removidos por uma heurística; a amostra deve ser conferida.

Os metadados incluem fonte, arquivo, título, autor, data, tipo, página e seção. Em TXT/Markdown, `pagina=0` representa ausência de paginação. Em PDFs, a página exibida é a posição física no arquivo, contando a partir de 1; a paginação impressa pode diferir.

A assinatura dos documentos e do cadastro é conferida antes de consultar. Mudanças no modelo/configuração invalidam o índice. Caso atualize os pesos do E5 sob o mesmo nome, reindexe a coleção.

Opções úteis:

```bash
python app.py recuperar "Como controlar notificações?" --top-k 4
python app.py recuperar "Como controlar notificações?" --max-distancia 0.2
python app.py perguntar "O que a base diz sobre interrupções?" --modelo llama3.2:1b
```

O filtro `--max-distancia` é opcional e experimental: ajuste-o com os resultados reais. Antes de usar outra variante Llama, baixe-a no Ollama. `LLAMA_MODEL` e `OLLAMA_BASE_URL` configuram modelo e servidor por variáveis de ambiente; arquivos `.env` não são carregados automaticamente.

## Limitações e comportamento do agente

RAG significa recuperar evidências externas antes de gerar uma resposta. O comportamento agentivo deste protótipo é limitado: ele executa o fluxo de busca, usa as evidências e pode declarar insuficiência. Não planeja tarefas autonomamente nem escolhe ferramentas dinamicamente.

O prompt distingue evidências, inferências e divergências, proíbe diagnósticos individuais e trata documentos como dados, sem conceder autoridade a instruções neles contidas. Isso reduz riscos, mas não prova resistência a instruções maliciosas.

A validação automática confirma o formato estruturado e a existência dos IDs de fontes; não demonstra que todas as afirmações são sustentadas. A avaliação registra o número real de chamadas ao Llama, incluindo uma eventual tentativa de correção. A pequena coleção não cobre sono, saúde ou hábitos digitais de forma abrangente. Sem limiar calibrado, a recuperação pode trazer trechos distantes do assunto, cabendo ao gerador reconhecer a insuficiência e à dupla avaliar o resultado.

Não são treinados ou ajustados os pesos do Llama. A busca é feita pelo E5, e a geração pelo Llama. A primeira execução requer internet para obter os modelos; o serviço Ollama padrão é local. Se configurar outro servidor, os textos serão enviados ao endereço configurado.

## Testes e reprodução

```bash
python -m unittest discover -s tests -v
```

Os testes cobrem preparação, limites de chunks, seções, PDF real com páginas, cinco fontes cadastradas, Chroma persistente, reindexação, preservação do índice após falha, filtro de distância, prompt e referências. Os vetores controlados dos testes unitários não medem a qualidade semântica do E5 nem a fidelidade do Llama.

Consulte [docs/adequacao_roteiro.md](docs/adequacao_roteiro.md) para a correspondência das sete etapas e [docs/validacao.md](docs/validacao.md) para os resultados efetivamente verificados.

## Organização

```text
app.py
requirements.txt / requirements.lock.txt
src/bem_estar_digital/
  config.py
  ingestao/       # PDF, TXT, limpeza e chunks
  recuperacao/    # E5, Chroma e atualização do índice
  geracao/        # Llama via Ollama e referências
  avaliacao/      # Casos, métricas e rastros
  rag.py          # Importações do fluxo
prompts/resposta.txt
data/
  raw/            # Coleção inicial de cinco documentos
  sources.csv     # Cadastro verificável
  processed/      # JSONL e manifesto gerados
  chroma/         # Persistência local gerada
evaluation/questions.json
evaluation/results/  # Resultados locais, ignorados pelo Git
tests/fixtures/     # Contradição e instrução maliciosa artificiais
output/pdf/         # Guia didático anterior
```

O código e os documentos públicos podem ser versionados. Caches, ambiente virtual, índices e resultados locais são ignorados. Não foram enviados commits ou alterações ao GitHub nesta tarefa.

## Próximas evoluções

Revisar a base em dupla, ampliar os documentos originais, testar as respostas com o Llama real, calibrar recuperação e registrar falhas e melhorias. OCR, interface visual e avaliadores como Ragas podem ser explorados depois.

## Referências técnicas

- [Chroma: cliente Python persistente](https://docs.trychroma.com/reference/python)
- [Chroma: distância e configuração da coleção](https://docs.trychroma.com/docs/collections/configure)
- [Multilingual E5 Small](https://huggingface.co/intfloat/multilingual-e5-small)
- [pypdf: extração e limitações de OCR](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
- [Ollama: API de chat](https://docs.ollama.com/api/chat)
