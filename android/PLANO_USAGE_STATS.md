# Plano incremental — UsageStatsManager

Criado em 17/11/2026. Objetivo do componente: oferecer uma interface de acesso aos dados de uso do Android para os agentes do FluIA. A primeira demonstração permitirá autorizar o acesso, tocar em **Consultar uso** e visualizar o tempo em primeiro plano por aplicativo, mantendo a consulta separada da interface visual.

A evolução pretendida inclui um monitor que acompanhe o uso ao longo do tempo e forneça dados para detectar desvios em relação à rotina planejada pelo usuário. O botão é uma ferramenta inicial de validação; a consulta deve ser reutilizável pelo monitor. Frequência, execução em segundo plano e comunicação com os agentes ainda precisam ser definidas e validadas.

## Como acompanhar

Implementar uma etapa por vez. Explicar as alterações, verificar o resultado e atualizar este checklist antes de avançar. Marcar uma tarefa somente com evidência de conclusão: código escrito, compilação e execução no aparelho são verificações distintas.

Todo código novo terá comentários em português explicando responsabilidades das classes, métodos e blocos importantes, especialmente permissões, datas, unidades, execução assíncrona e limitações. Evitar comentários que apenas repitam a sintaxe.

**Testes E2E estão fora do escopo neste momento.** Manter testes unitários relevantes e validação manual.

## 1. Preparar e validar a base

- [x] Criar projeto com Kotlin, Compose e Kotlin DSL.
- [x] Conferir pacote `com.fluia.fluiagent` e `minSdk = 26`.
- [x] Colocar o projeto dentro do repositório e renomear a pasta para `android`.
- [x] Confirmar a branch `androidAPI` após a mudança.
- [x] Configurar e verificar `.gitignore`: configurações locais, caches, builds, arquivos do macOS e locais reservados para dados pessoais.
- [x] Reabrir o projeto no Android Studio pelo novo caminho (confirmado pelo usuário).
- [x] Confirmar sincronização do Gradle (informado pelo usuário).
- [x] Compilar a base original (Android Studio, sucesso informado pelo usuário; comando interno não registrado).
- [x] Abrir a tela inicial em emulador: Pixel 6 Pro API 37.0, execução confirmada pelo usuário.

**Conclusão:** projeto original compila e abre, separando problemas de ambiente dos problemas da implementação futura.

## 2. Definir o contrato dos dados

- [x] Criar `UsagePeriod` com início e fim, documentar timestamps e validar início anterior ao fim.
- [x] Criar `AppUsage` com pacote, nome e duração em milissegundos.
- [x] Criar `UsageReport` com período solicitado, instante da consulta e resultados.
- [x] Criar a interface `UsageRepository`, independente da tela.
- [x] Distinguir sucesso com dados, sucesso sem registros, acesso não autorizado e falha.
- [x] Criar implementação simulada para desenvolvimento e testes, claramente identificada.
- [x] Documentar a métrica: tempo em primeiro plano reportado pelo Android, sem equipará-lo automaticamente ao tempo total de tela.

**Conclusão:** contrato compreensível e utilizável sem dependência direta da tela com `UsageStatsManager`.

### Código desta etapa

Arquivos em `app/src/main/java/com/fluia/fluiagent/usage/`:

- `UsageModels.kt`: período com `Instant` (início inclusivo e fim exclusivo), duração em milissegundos, relatório, origem e estados de resultado.
- `UsageRepository.kt`: contrato `queryUsage(period)`. É síncrono; o futuro chamador executará a leitura real fora da thread principal, em IO. Não agenda monitoramento nem abre configurações.
- `FakeUsageRepository.kt`: cenários `WITH_DATA`, `EMPTY`, `ACCESS_DENIED` e `FAILURE`. Usa pacotes fictícios, identifica a origem como `SIMULATED` e aceita um relógio controlado nos testes. As amostras fixas não são um histórico filtrado pelo período.

O relatório registra o período solicitado, sem garantir que os agregados reais se restrinjam a ele. A implementação real e a tela que consomem esse contrato estão descritas nas etapas 4 e 5.

### Validação executada pelo assistente

Na pasta `android`, em 17/11/2026:

```sh
env JAVA_HOME='/Applications/Android Studio.app/Contents/jbr/Contents/Home' ./gradlew :app:testDebugUnitTest :app:assembleDebug --offline
```

Resultado: **BUILD SUCCESSFUL**. Seis testes novos em `UsageContractTest` passaram: períodos invertido e vazio, duração negativa, preservação de milissegundos/zero, origem/período/instante da simulação e distinção entre vazio/acesso negado/falha. O teste de exemplo do template também passou. Não foram executados testes E2E nem consultas ao dispositivo.

Ambiente observado: Gradle 9.6.0, JVM de lançamento JetBrains 25.0.4, daemon configurado para Java 25, macOS 26.6.2 aarch64. Configuração do projeto: AGP 9.5.1, plugin Compose Kotlin 2.2.10, compile/target SDK 37 e mínimo 26. Nenhuma dependência adicionada.

## 3. Implementar o acesso especial

- [x] Declarar `android.permission.PACKAGE_USAGE_STATS` no Manifest.
- [x] Implementar verificação com `AppOpsManager`, com caminhos para APIs 26–28, 29–35 e 36+; comportamento em cada versão ainda requer validação no dispositivo.
- [x] Implementar tela com finalidade da consulta, dados acessados e status da autorização.
- [x] Criar botão **Permitir acesso ao uso** com `Settings.ACTION_USAGE_ACCESS_SETTINGS` e tratar indisponibilidade da tela.
- [x] Implementar nova verificação em `onResume`; abrir configurações não significa autorização concedida.
- [x] Validar avanço automático para a tela principal após conceder acesso e retornar (confirmado pelo usuário).
- [ ] Validar manualmente concessão, recusa e revogação.

**Conclusão:** tela reflete a autorização real. Ainda não consultar o histórico nesta etapa.

### Como acompanhar o código e testar esta etapa

- `usage/UsageAccessChecker.kt`: verifica o acesso do próprio app com `AppOpsManager`, sem consultar estatísticas. Distingue autorização, ausência de autorização e impossibilidade de verificar.
- `MainActivity.kt`: abre as configurações e verifica o acesso na criação e em `onResume`. A autorização seleciona automaticamente `UsageHomeScreen`; acesso negado ou indisponível seleciona `UsageAccessScreen`. Ambas recebem estado e callbacks e têm Preview. A consulta da tela principal foi adicionada nas etapas 4 e 5.
- `AndroidManifest.xml`: declara o acesso especial. A supressão pontual de lint `ProtectedPermissions` se aplica porque esse acesso é concedido pelo usuário nas configurações, não por `requestPermissions`.
- `res/values/strings.xml`: textos em português e nome do aplicativo **FluIA**, facilitando encontrá-lo nas configurações.

Roteiro manual no Pixel 6 Pro API 37.0 (ainda pendente):

1. Executar novamente pelo botão Run do Android Studio para instalar a versão atualizada.
2. Com o acesso desabilitado, conferir **Acesso ainda não autorizado**.
3. Tocar em **Permitir acesso ao uso**, encontrar **FluIA** e voltar sem habilitar: o status deve continuar não autorizado.
4. Reabrir as configurações, habilitar o acesso e voltar: o app deve sair automaticamente da tela de autorização e mostrar **Uso de aplicativos**, **Acesso autorizado** e **Gerenciar acesso ao uso**.
5. Usar esse botão para revogar o acesso e voltar: o app deve retornar à tela de autorização. Reabrir o app com acesso concedido deve levar diretamente à tela principal.
6. Se a verificação falhar, usar **Verificar novamente**. Se a tela do sistema não puder ser aberta, o app mostra instruções para encontrá-la manualmente.

O acesso autorizado não comprova que a consulta real funciona: a leitura implementada na etapa 4 ainda precisa de validação no emulador. A verificação de autorização não consulta histórico. Nenhum teste E2E foi adicionado.

Validação local em 17/11/2026:

```sh
env JAVA_HOME='/Applications/Android Studio.app/Contents/jbr/Contents/Home' ./gradlew :app:testDebugUnitTest :app:assembleDebug :app:lintDebug
```

**BUILD SUCCESSFUL**: sete testes existentes passaram e APK gerado. Lint concluiu sem erros bloqueantes, com avisos sobre label redundante e cores não usadas do template, além de sugestões de atualização de ferramentas/dependências. Não foram alteradas versões. A tentativa inicial com `--offline` falhou porque `lint-gradle:32.5.1` não estava no cache; a execução acima baixou a ferramenta e concluiu. Validação manual de autorização no emulador permanece pendente, assim como verificação em APIs anteriores.

## 4. Implementar a consulta Android

- [x] Criar `AndroidUsageRepository`, implementando o contrato.
- [x] Validar período, verificar acesso e tratar falhas durante a operação.
- [x] Usar inicialmente `queryAndAggregateUsageStats(inicio, fim)` e `totalTimeInForeground`.
- [x] Executar a consulta fora da thread principal, pelo ViewModel em `Dispatchers.IO`.
- [x] Converter resultados para os modelos do projeto.
- [x] Resolver nomes quando disponíveis; usar pacote como alternativa, sem exigir acesso amplo à lista de apps.
- [x] Ordenar por duração decrescente e documentar filtros, inclusive para duração zero.
- [x] Não interpretar ausência de registros como prova de uso zero ou como confirmação de acesso autorizado.
- [x] Documentar as limitações dos intervalos agregados.
- [ ] Validar a leitura real no emulador; testes locais usam funções controladas, sem leitura do Android.

**Conclusão:** dados reais estruturados e estados explícitos, sem depender de componentes visuais.

**Limitação:** o Android pode expandir o período solicitado para seus intervalos de agregação. Não prometer medição exata de uma sessão ou recorte temporal estrito. Avaliar `queryEvents` futuramente apenas se essa precisão for necessária.

**Contrato aplicado:** o repositório retorna apenas pacotes com `foregroundTimeMs > 0`, em ordem decrescente, com desempate pelo pacote. Não aplica top 10 nem exclui aplicativos de sistema ou o próprio FluIA. Mantém milissegundos no modelo; nomes indisponíveis usam o pacote como alternativa. Confere autorização antes e depois da leitura e distingue sucesso vazio de indisponibilidade do serviço/usuário bloqueado. Não armazena nem transmite o relatório.

## 5. Conectar botão e lista

- [x] Criar tela Compose e `ViewModel` simples para controlar os estados.
- [x] Conectar tela → ViewModel → UsageRepository → UsageStatsManager.
- [x] Usar inicialmente o início do dia no fuso local até o momento da consulta.
- [x] Adicionar seleção de Hoje, últimas 24h, últimas 72h e últimos 7 dias (168h), com cálculo comum reutilizável pela futura integração.
- [ ] Validar manualmente o seletor e os resultados dos quatro períodos no emulador.
- [x] Exibir período solicitado, instante da consulta e ressalva sobre agregação.
- [x] Adicionar **Consultar uso**, acionando leitura por ação do usuário.
- [x] Exibir carregamento e impedir consultas simultâneas pelo botão.
- [x] Listar nome, pacote e duração formatada por aplicativo.
- [x] Exibir nome (ou pacote quando indisponível) e duração lado a lado; tocar na linha expande nome completo, pacote e categoria opcional do Android.
- [ ] Validar manualmente expansão/recolhimento, nomes longos, fonte ampliada e categoria no emulador.
- [x] Exibir mensagens para acesso pendente, ausência de registros e erro.
- [x] Identificar explicitamente relatórios simulados quando fornecidos à tela; o app está conectado ao repositório real.
- [ ] Validar manualmente lista, atualização, rotação e retorno após revogação no emulador.

**Conclusão:** após autorizar o acesso, a pessoa toca no botão e recebe resultados ou uma mensagem adequada.

### Como acompanhar esta implementação

**Atualização de 24/11/2026:** `usage/UsagePeriods.kt` centraliza `UsagePeriodPreset.resolve(now, zone)`. Hoje é meia-noite local até agora; os outros presets são janelas móveis de 24, 72 e 168 horas, sem confundir a semana móvel com a semana civil anterior. O instante de referência é capturado no clique. Trocar a seleção limpa o resultado anterior e não coleta dados; durante uma leitura a seleção fica desabilitada. `UsageRepository.queryUsage(UsagePeriod)` continua aceitando início/fim personalizados, sem UI ou ViewModel. O seletor não muda a limitação de precisão dos agregados Android.

Guia da conexão com Python: [INTEGRACAO_AGENTES.md](INTEGRACAO_AGENTES.md). Inclui a API Kotlin existente, contrato HTTP proposto, exemplos LangChain com e sem Ollama e pendências. A ponte de rede, serialização JSON e consulta a sessões/eventos ainda não estão implementadas.

1. `usage/AndroidUsageRepository.kt` conecta os serviços reais ao contrato. Seu construtor interno permite testar a lógica sem acessar dados do aparelho.
2. `usage/UsagePresentation.kt` calcula o período no fuso local e formata durações; inclui tratamento de meia-noite e horário de verão.
3. `usage/UsageViewModel.kt` controla carregamento e resultado em memória. A leitura ocorre em IO, o botão não dispara consultas simultâneas e a perda de autorização cancela o trabalho e limpa o estado. O ViewModel sobrevive à rotação, sem persistir dados em disco.
4. `ui/UsageHomeScreen.kt` apresenta metadados, origem, avisos e lista com `LazyColumn`. Não chama a API Android diretamente.
5. `MainActivity.kt` injeta o repositório real no ViewModel e mantém o fluxo de autorização.

Dependências: `lifecycle-viewmodel-ktx` 2.11.0 declarado explicitamente para o ViewModel e seu escopo (já estava presente transitivamente); `kotlinx-coroutines-test` 1.9.0 adicionado somente aos testes para controlar carregamento e cancelamento. Sem framework de injeção ou biblioteca de rede.

**Atualização visual de 18/11/2026:** cada resultado ocupa uma linha com nome e duração; o pacote substitui o nome quando indisponível. `UsageAppRow` usa estado de expansão por pacote e mostra nome completo, pacote e categoria ao toque, sem fazer nova coleta. Inclui ação/estado para leitores de tela e Preview com exemplos fictícios. A categoria opcional `AppUsage.category` recebe o título localizado de `ApplicationInfo.getCategoryTitle`, disponível desde API 26. Não vem do UsageStatsManager nem é inferida pelo FluIA. Categoria indefinida ou metadados inacessíveis aparecem como **Não informada ou indisponível**; a categoria não determina se o uso está alinhado à rotina do usuário.

### Roteiro de validação manual da consulta (pendente)

1. Sincronizar o Gradle e executar pelo Run do Android Studio no Pixel 6 Pro API 37.0.
2. Com acesso autorizado, tocar em **Consultar uso**. Conferir carregamento, período, origem Android e lista ou mensagem de ausência de registros.
   Repetir para Hoje, últimas 24h, últimas 72h e últimos 7 dias; conferir os limites solicitados e que trocar a seleção limpa a lista antes da nova consulta.
3. Usar algum aplicativo do emulador, voltar ao FluIA e consultar novamente. Pode haver atraso na atualização; não exigir igualdade imediata com um cronômetro.
4. Conferir nomes/pacotes e ordenação; o identificador do pacote é uma alternativa esperada quando o Android não expõe o nome.
5. Rotacionar durante ou após a consulta: a consulta não deve ser duplicada e o resultado deve permanecer na mesma instância do ViewModel.
6. Revogar acesso em **Gerenciar acesso ao uso** e voltar: a tela de autorização deve reaparecer. Ao autorizar novamente, o relatório antigo não deve reaparecer sem nova consulta.

Não publicar capturas, relatórios ou logs com histórico pessoal. O assistente não executou consultas ao emulador.

### Validação local das etapas 4 e 5

Executado pelo assistente em 17/11/2026, na pasta `android`:

```sh
env JAVA_HOME='/Applications/Android Studio.app/Contents/jbr/Contents/Home' ./gradlew :app:testDebugUnitTest :app:assembleDebug :app:lintDebug --offline
```

Resultado final: **BUILD SUCCESSFUL**, APK gerado e **19 testes passaram, sem falhas**: 6 de contrato, 5 do repositório com funções controladas, 3 de datas/formatação, 4 de estados/cancelamento do ViewModel e 1 do template. Antes dessa execução, o comando sem `--offline` baixou as dependências necessárias. Ambiente e versões base permanecem os registrados na etapa 2; dependências adicionais estão justificadas acima.

Lint concluiu sem erros bloqueantes, com avisos de label redundante e cores não usadas do template, além de sugestões de atualização de versões (incluindo a biblioteca de testes de coroutines). Essas sugestões não foram aplicadas nesta etapa. Não foram executados testes E2E nem coleta real pelo assistente. Resultados locais não comprovam exatidão dos agregados nem funcionamento nas diferentes versões do Android.

## 6. Verificar e documentar

### Testes unitários e verificações locais

- [x] Testar período inválido e duração negativa; preservar precisão em milissegundos.
- [x] Testar ordenação e filtros, incluindo preservação de mais de dez resultados.
- [x] Testar formatação de duração, incluindo zero e valores acima de uma hora.
- [x] Testar estados com repositório simulado: sucesso, vazio, acesso negado e erro, além de duplo clique e cancelamento.
- [x] Executar compilação e lint das etapas 4 e 5, registrando resultados.

### Validação manual

- [ ] Verificar acesso concedido, recusado e revogado.
- [ ] Verificar ausência de registros e erros quando reproduzíveis.
- [ ] Usar aplicativos e consultar novamente; registrar comportamento observado, atrasos e diferenças.
- [ ] Confirmar que os dados permanecem locais e em memória nesta versão.

### Documentação

- [x] Documentar como abrir, compilar e executar a versão atual.
- [x] Registrar ambiente, versões, comandos efetivamente executados e resultados.
- [x] Documentar contrato, unidades, período, filtros e limitações.
- [x] Separar resultados de testes simulados da validação real no aparelho, ainda pendente para a consulta.
- [x] Atualizar este checklist com pendências e evidências, sem dados pessoais; continuar atualizando nas próximas etapas.

**Conclusão:** demonstração reproduzível com limites conhecidos. Não implementar testes E2E nesta etapa.

## 7. Planejar a integração com agentes e o monitor

Direção do produto, ainda sem implementação de coleta contínua ou envio de dados.

- [ ] Definir onde os agentes executarão e o contrato de comunicação com o Android: formato, unidades, timestamps, erros e versão do schema.
- [ ] Definir a rotina planejada pelo usuário e o que constitui um desvio, separando observações de interpretações dos agentes.
- [ ] Definir janelas, frequência de consulta e latência aceitável; avaliar se agregados bastam ou se será necessário processar `queryEvents`.
- [ ] Avaliar execução em segundo plano nas versões Android suportadas, consumo de bateria e comportamento com o app fechado. Não prometer observação ininterrupta antes dessa validação.
- [ ] Planejar início, pausa e encerramento pelo usuário, consentimento explícito e revogação do acesso.
- [ ] Definir minimização, retenção e exclusão; identificar destino e autorização antes de qualquer transmissão.
- [ ] Reutilizar `UsageRepository`, mantendo monitoramento, regras de rotina, agentes e tela separados.

**Conclusão futura:** estratégia documentada e validável para conectar a fonte Android aos agentes e acompanhar a rotina definida pelo usuário.

## Limites da primeira demonstração

- Nesta primeira demonstração, consultas locais acionadas pelo usuário após autorização, sem coleta periódica, persistência de histórico ou envio de telemetria. O monitoramento é uma evolução planejada na etapa 7.
- Não incluir dados pessoais de uso ou capturas sensíveis no Git.
- Manter implementação simples; justificar qualquer dependência adicional.
- Integração com agentes Python e transporte de dados, possivelmente JSON, serão planejados depois. A interface Kotlin não é diretamente acessível por agentes Python externos ao app.
- Esta API local, isoladamente, não comprova o atendimento ao requisito acadêmico de APIs externas e colaboração entre agentes.
- Tempo elevado de uso não será apresentado como diagnóstico ou prejuízo automático.

## Registro de progresso

| Data | Evidência / alteração | Pendências |
| --- | --- | --- |
| 17/11/2026 | Arquivos inspecionados: Kotlin DSL, Compose, pacote e SDK mínimo. Pasta renomeada para `android`; branch `androidAPI` confirmada. | Compilação e execução não verificadas pelo assistente. |
| 17/11/2026 | Plano criado; testes E2E excluídos por solicitação do usuário. | Implementação do acesso e da consulta ainda não iniciada. |
| 17/11/2026 | Configurados ignores da raiz e do Android. Usuário confirmou projeto aberto no Android Studio. Registrado objetivo de interface para agentes e futuro monitor de rotina. | Sincronização, compilação e estratégia do monitor ainda pendentes. |
| 17/11/2026 | Usuário confirmou sync, primeira build e execução no Pixel 6 Pro API 37.0. Implementado contrato e repositório simulado comentados; build e testes unitários locais passaram. Configurações `.idea` da pasta antiga também ignoradas, sem excluir arquivos. | Próxima etapa: acesso especial do Android. Consulta real, tela e monitor ainda não implementados. |
| 17/11/2026 | Implementada tela de autorização, verificação com AppOpsManager e retorno via onResume. Build, sete testes unitários e lint concluíram. | Validar concessão, recusa e revogação no emulador. Consulta real e monitor ainda não implementados. |
| 17/11/2026 | Após feedback do usuário, autorização passa a selecionar automaticamente a tela principal ao retornar das configurações ou reabrir o app. Revogação seleciona novamente a tela de autorização. | Validar manualmente a transição; tela principal ainda sem consulta de tempos. |
| 17/11/2026 | Usuário confirmou o funcionamento da transição automática após a correção. Build e testes unitários da correção também passaram. | Recusa, revogação e reabertura ainda sem confirmação específica. Próxima implementação: consulta real ao UsageStatsManager. |
| 17/11/2026 | Implementados repositório Android, consulta manual em IO, ViewModel e lista com origem/período/avisos. Build, 19 testes unitários e lint concluíram. | Validar leitura real, atualização, rotação e revogação no emulador. Monitor e integração com agentes ainda não implementados. |
| 18/11/2026 | Usuário aprovou o resultado anterior e solicitou lista linear expansível. Implementados nome/tempo lado a lado, detalhes ao toque e categoria opcional do Android. Mesmo comando de validação das etapas 4/5: build e 19 testes passaram; lint sem erros bloqueantes. Nenhuma dependência adicionada. | Validar nova apresentação e metadados no emulador; sem testes E2E nem leitura de dados pelo assistente. |
| 24/11/2026 | Implementados quatro períodos selecionáveis e resolução reutilizável. Criado INTEGRACAO_AGENTES.md. Executado o comando de build/testes/lint da seção 4/5 com `--offline`: sucesso, 23 testes sem falhas e lint sem erros bloqueantes (avisos de template/versões). Exemplos Python/JSON verificados apenas quanto à sintaxe. Nenhuma dependência adicionada. | Validar seletor no emulador. API HTTP e transporte Python–Android são propostas; precisão por sessão exige outra implementação. |

## Referências

- [UsageStatsManager](https://developer.android.com/reference/android/app/usage/UsageStatsManager)
- [UsageStats](https://developer.android.com/reference/android/app/usage/UsageStats)
- [AppOpsManager](https://developer.android.com/reference/android/app/AppOpsManager)
- [ApplicationInfo: categoria e título localizado](https://developer.android.com/reference/android/content/pm/ApplicationInfo#getCategoryTitle(android.content.Context,%20int))
- [Configuração de acesso ao uso](https://developer.android.com/reference/android/provider/Settings#ACTION_USAGE_ACCESS_SETTINGS)
