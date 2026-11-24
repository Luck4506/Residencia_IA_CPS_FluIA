package com.fluia.fluiagent.usage

/**
 * Porta de entrada para consultar uso, sem expor classes do Android à tela.
 * A implementação real e a simulada obedecerão ao mesmo contrato.
 *
 * A operação é síncrona: quem a chamar deve executá-la fora da thread principal
 * quando houver leitura do sistema. O futuro ViewModel usará uma coroutine em IO.
 * O repositório não abre configurações, agenda monitoramento nem envia dados.
 */
interface UsageRepository {
    fun queryUsage(period: UsagePeriod): UsageResult
}
