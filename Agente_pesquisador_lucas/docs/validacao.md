# Registro de validação

Execução local em 28/10/2026, macOS ARM64, Python 3.12.14. Versões de pacotes registradas em `requirements.lock.txt`.

## Verificado

- 13 testes automatizados passaram, sem testes pulados, incluindo ChromaDB real em diretórios temporários.
- `pip check`: nenhuma dependência incompatível encontrada.
- E5 real baixado, com revisão fixada em `614241f622f53c4eeff9890bdc4f31cfecc418b3`.
- Cinco documentos cadastrados geraram oito chunks. As seções curtas resultaram em 38 a 162 tokens; não houve preenchimento artificial para atingir 250 tokens.
- ChromaDB persistiu e consultou a coleção principal localmente.
- O PDF didático anterior foi lido diretamente: quatro páginas, 18 chunks em uma coleção separada de demonstração. Essa coleção gerada foi removida na limpeza; o PDF foi preservado e pode ser reindexado conforme o README.
- A pergunta “Como organizar uma sessão de estudo?” recuperou os trechos “Primeiro exercício” (p. 1, distância 0,1249) e “Faça pausas planejadas” (p. 2, distância 0,1371) na coleção do PDF.
- Nove casos de avaliação somente da recuperação executados sem erros. Os sete casos com arquivos esperados tiveram hit@5 e recall de fontes igual a 1 nesta pequena amostra; dois casos sem resposta não têm métrica de fonte esperada.

## Interpretação

Os resultados confirmam a execução do fluxo e a recuperação das fontes cadastradas nessa amostra. Top-k 5 sobre uma coleção de oito chunks oferece cobertura ampla e não demonstra alta precisão. Dois casos são artificiais e isolados. Os resultados não comprovam generalização, resistência a instruções maliciosas ou fidelidade da geração.

As perguntas fora da base ainda podem recuperar resultados porque não há um limiar de distância calibrado. A decisão de abstenção precisa ser avaliada com as respostas reais do Llama.

## Pendências identificadas na validação inicial

O serviço Ollama não estava disponível durante a validação inicial. O contrato HTTP de geração, as referências e o prompt foram testados de forma controlada, mas não foi executada inferência real com o Llama. Para completar a avaliação:

```bash
source .venv/bin/activate
ollama pull llama3.2:3b
python app.py avaliar
```

Mantenha o Ollama aberto. Depois revise `scorecard.csv` e `traces.jsonl`, conferindo fidelidade, referências, incerteza, contradições e instruções maliciosas. Esses campos permanecem pendentes; não foram preenchidos como aprovados automaticamente.

## Apresentação sugerida

Demonstre uma pergunta direta, uma paráfrase e uma pergunta fora da base. Mostre os documentos, a recuperação isolada e a resposta, incluindo eventuais falhas. Explique que E5 busca evidências, Chroma armazena os vetores e o Llama via Ollama redige a resposta. Compare novas configurações usando os mesmos casos e registre a mudança observada.

## Correção do formato de referências - 28/10/2026

Após o relato de resposta sem referências válidas, a geração passou a usar o JSON Schema do Ollama: cada afirmação possui texto e uma lista de IDs de fontes. O programa valida esses IDs e monta as citações, sem atribuir fontes arbitrariamente a uma resposta livre. Uma resposta inválida recebe no máximo uma nova tentativa de correção. A abstenção também usa formato estruturado.

- 17 testes passaram, incluindo referências inexistentes, referências ocultas no texto, abstenção, montagem de citações e recuperação de uma resposta malformada.
- Foi executada inferência real com o Ollama usando a pergunta “Como reduzir distrações durante os estudos?”. O comando terminou com sucesso, recuperou cinco trechos e exibiu quatro afirmações com citações. Não foi necessário reindexar.
- A inferência confirma o funcionamento do formato, não a fidelidade de cada frase. A resposta de exemplo ainda extrapolou a fonte de notificações ao incluir redução de estresse; esse benefício não consta desse trecho. A revisão semântica da dupla permanece necessária e não foi marcada como aprovada.
- A avaliação contabiliza as chamadas reais, incluindo a eventual correção automática.

## FAQ por preferência - 29/10/2026

A pasta `agente_pesquisador/` reproduz a estrutura da imagem: `data/raw`, `data/processed` e quatro scripts de extração, segmentação e relevância por TF-IDF/embeddings. O novo PDF tem quatro páginas e oito FAQs, cada um com pergunta, resposta, base teórica, fonte e preferência de dispositivo.

Os 21 testes passaram, incluindo a leitura dos oito pares do PDF, o filtro estrito de dispositivo e a consulta TF-IDF exata. A busca E5 real no filtro Windows recuperou FAQ008 para a pergunta de sessão de foco; no filtro Android, FAQ003 foi recuperado para a pergunta de pausa de aplicativos. Similaridade não foi tratada como probabilidade de acerto.

O novo índice FAQ é um cache NumPy de embeddings das perguntas, separado do Chroma do experimento anterior. Mudar perguntas/modelo invalida os vetores; mudar respostas ou fontes atualiza o texto recuperado sem exigir novos vetores. O PDF continua sendo a origem lida pelo extrator.

A consulta FAQ real com Llama via Ollama também terminou com sucesso: a pergunta sobre pausar aplicativos no Android recuperou FAQ003, gerou resposta com [T1] e mostrou a documentação Google e a página 2 do PDF. A validação semântica de cada frase continua sendo uma revisão humana.
