# Dados do fluxo atual

- `raw/`: cinco sínteses públicas versionadas; também aceita PDFs selecionáveis, TXT e Markdown.
- `sources.csv`: cadastro de fontes, com nome de arquivo relativo a `raw/`, ID, título, autor, data, tipo, URL, localização original, acesso e observações.
- `processed/documents.jsonl`: textos extraídos, por página quando houver.
- `processed/chunks.jsonl`: trechos limpos e metadados para inspeção.
- `processed/manifest.json`: configuração, assinatura dos originais e coleção ativa.
- `chroma/`: banco vetorial persistido localmente.

Somente fontes e cadastro são versionados. Os arquivos gerados são reconstruídos pelos comandos `preparar` e `indexar`.

A coleção registra a página física do PDF e a seção detectada no texto. Um TXT não tem paginação e usa o valor 0. A localização no artigo original de uma síntese está registrada no CSV; não se deve confundi-la com uma página do arquivo TXT.

As cinco sínteses são uma base inicial para demonstração. As duas primeiras se baseiam em resumos de estudos; as demais descrevem funcionalidades documentadas por Google, Apple e Microsoft. Não há uma base científica abrangente nem uma revisão clínica.

Ao incluir documentos pessoais, configure o `.gitignore` antes de versionar. Nenhum conteúdo privado deve ser adicionado sem necessidade.
