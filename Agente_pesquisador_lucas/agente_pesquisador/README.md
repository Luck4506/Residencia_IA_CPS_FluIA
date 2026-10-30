# Agente pesquisador - FAQ de bem-estar digital

## Estrutura conforme a imagem

```text
agente_pesquisador/
├── data/
│   ├── raw/
│   │   └── faq_bem_estar_digital.pdf
│   └── processed/
├── scripts/
│   ├── buscar_relevancia_embeddings.py
│   ├── buscar_relevancia_tfidf.py
│   ├── extrair_pdf.py
│   └── segmentar_chunks.py
├── .gitignore
├── README.md
└── requirements.txt
```

## Ideia

O PDF contém oito FAQs completos. O programa extrai os pares, gera embeddings das perguntas cadastradas e procura perguntas de significado semelhante. Depois apresenta a resposta cadastrada, sua base teórica, o link original e a página do PDF. A segmentação não separa a pergunta da resposta.

A preferência escolhida é **dispositivo**: `android`, `mac`, `windows` ou `geral`. `todos` desativa o filtro. O filtro é estrito e aplicado antes do ranking: Android nunca retorna um registro Mac. Ele não tenta adivinhar o dispositivo pelo texto. Esse é o equivalente ao filtro de país do exemplo do professor.

RAG é recuperação de uma base externa para fornecer contexto à resposta. O índice local persiste os embeddings; esse cache evita recalculá-los, mas não é a memória interna nem treinamento do Llama. No modo direto há recuperação de FAQ sem geração. Ao habilitar Ollama, a recuperação alimenta a geração e compõe o fluxo RAG completo.

## Executar

Na raiz `Agente_pesquisador_lucas`, use o ambiente Python 3.12 já preparado:

```bash
source .venv/bin/activate
python app.py indexar
python app.py recuperar "Como pausar aplicativos no celular?" --preferencia android
python app.py perguntar "Como pausar aplicativos no celular?" --preferencia android
```

`recuperar` exibe a resposta original do FAQ. `perguntar` usa Llama via Ollama, que deve estar aberto e ter o modelo `llama3.2:3b` baixado. As fontes continuam vinculadas ao registro recuperado. Sem argumentos, `python app.py` abre um modo interativo com resposta direta.

Também é possível executar os quatro scripts da imagem diretamente, a partir desta pasta:

```bash
python scripts/extrair_pdf.py
python scripts/segmentar_chunks.py
python scripts/buscar_relevancia_tfidf.py "Como limitar aplicativos?" --preferencia mac
python scripts/buscar_relevancia_embeddings.py "Como limitar aplicativos?" --preferencia mac
python scripts/buscar_relevancia_embeddings.py "Como limitar aplicativos?" --preferencia mac --ollama
```

Em uma instalação nova, use Python 3.11 ou 3.12 e instale este `requirements.txt`. O modo Ollama reutiliza o cliente de `../src/bem_estar_digital/geracao/`, mantido no projeto. O E5 reutiliza o cache local de `../.cache/`; sem ele, o modelo é baixado na primeira consulta.

## Preferência e relevância

```bash
python app.py recuperar "Como controlar o tempo de uso?" --preferencia windows --top-k 2
python app.py recuperar "Como controlar o tempo de uso?" --preferencia windows --minimo 0.9
```

Execute os exemplos acima na raiz do repositório. O limiar é opcional e experimental, não uma probabilidade. Sem corte, o modo direto mostra o melhor **candidato**, mesmo que a pergunta seja fora do escopo. Confira a pergunta semelhante exibida. Para respostas fora da base, o modo Ollama pode declarar falta de evidência. Similaridade e filtros não garantem sustentação semântica.

## Editar a base

Coloque PDFs selecionáveis em `data/raw/`. Use os campos abaixo em cada par, mantendo cada par em uma página e IDs únicos em todos os PDFs:

```text
ID: FAQ009
Preferencia: android
Pergunta: ...
Resposta: ...
Base teorica: título, autoria e seção da fonte
Fonte: https://endereco-da-fonte
```

Depois execute `python app.py indexar` na raiz. Alterações nos PDFs são detectadas por assinatura e reextraídas na consulta. Os vetores são recalculados se as perguntas ou o modelo mudarem; mudanças só nas respostas reutilizam os vetores e exibem o novo texto. Os arquivos de `processed/` são reconstruíveis e ignorados pelo Git.

O material é uma síntese didática baseada em dois estudos e nas documentações oficiais de Google, Apple e Microsoft, com links no próprio PDF. Não estabelece um tempo universal de estudo nem oferece diagnóstico individual.
