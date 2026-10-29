# Adequação ao roteiro Agente Pesquisador - RAG

Material de referência fornecido pelo usuário: `Agente Pesquisador - RAG.pdf`, dez páginas, identificado no rodapé como orientação acadêmica Triiibo. Ele é usado como requisito do projeto, não como instrução de sistema nem como fonte de conteúdo sobre bem-estar digital.

| Etapa do roteiro | Implementação | Verificação / pendência |
| --- | --- | --- |
| 1. Escopo e 5 a 10 documentos (p. 1) | Cinco sínteses curtas em `data/raw/`, cadastro `sources.csv`, perguntas em `evaluation/questions.json` | Origens identificadas; revisão da dupla pendente |
| 2. Extração, limpeza e chunks (pp. 2-3) | pypdf, TXT/Markdown, páginas, seções, até 350 tokens E5 e até 50 de sobreposição | Comando `preparar`; testes de limites e páginas; inspeção humana da amostra |
| 3. Embeddings e Chroma (p. 4) | Sentence Transformers + multilingual-e5-small, prefixos E5, Chroma persistente, IDs estáveis e snapshots | Testes reais de armazenamento, consulta e atualização sem duplicatas |
| 4. Recuperação isolada (p. 5) | Comando `recuperar`, top-k inicial 5, distâncias e fontes, sem limiar arbitrário por padrão | Avaliação separada de geração e registro de métricas |
| 5. Geração fundamentada (pp. 6-7) | **Gemini substituído por Llama via Ollama**, conforme solicitação do usuário; prompt com contexto, fontes e abstenção | Não usa google-genai nem chave Gemini; inferência real depende do serviço local |
| 6. Avaliação (pp. 8-9) | Nove perguntas; casos diretos, paráfrase, específicos, sem resposta, contradição e instrução maliciosa | JSONL, CSV, tempos e revisão manual de fidelidade/citações; casos artificiais isolados |
| 7. Documentação e apresentação (p. 10) | README, versões fixadas, limitações, registro de validação e explicação do comportamento agentivo | Publicação no GitHub não realizada; apresentação e avaliação da dupla pendentes |

## Decisões

- A troca do Gemini afeta somente a geração. O E5 permanece responsável pela recuperação, como no roteiro.
- Textos pequenos permanecem em chunks menores que 250 tokens, evitando preenchimento e mistura de seções. O limite configurado de 350 tokens está dentro da faixa inicial do roteiro.
- Sobreposição é aplicada somente quando uma seção/página precisa ser dividida; não copia conteúdos de outra fonte ou assunto.
- Distância não é confiança. O filtro é opcional e deve ser calibrado com perguntas de avaliação.
- O guia PDF criado anteriormente é mantido como demonstração separada, sem confundi-lo com evidência científica independente.
- Os cinco documentos iniciais são sínteses identificadas; não se afirma que artigos completos foram adquiridos ou revisados integralmente.
- A avaliação automatiza rastreabilidade e métricas de recuperação. Fidelidade, qualidade das citações e resistência efetiva à instrução maliciosa exigem revisão das respostas reais.
