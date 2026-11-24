package com.fluia.fluiagent.usage

import java.time.Clock

/**
 * Fonte fictícia para desenvolver e testar sem permissões nem dados do aparelho.
 * As amostras são fixas: não representam um histórico filtrado pelo período.
 * O relógio injetável permite testar timestamps sem depender do horário da máquina.
 */
class FakeUsageRepository(
    private val scenario: Scenario = Scenario.WITH_DATA,
    private val clock: Clock = Clock.systemUTC(),
) : UsageRepository {
    /** Permite exercitar os quatro resultados sem precisar provocar falhas reais. */
    enum class Scenario { WITH_DATA, EMPTY, ACCESS_DENIED, FAILURE }

    override fun queryUsage(period: UsagePeriod): UsageResult = when (scenario) {
        Scenario.ACCESS_DENIED -> UsageResult.AccessDenied
        Scenario.FAILURE -> UsageResult.Failure("Falha simulada ao consultar o uso.")
        Scenario.WITH_DATA, Scenario.EMPTY -> {
            // Nomes e pacotes fictícios; nenhum aplicativo do dispositivo é consultado.
            val apps = if (scenario == Scenario.WITH_DATA) {
                listOf(
                    AppUsage("example.simulated.reader", "Leitor (simulado)", 1_200_000L),
                    AppUsage("example.simulated.video", "Vídeo (simulado)", 600_000L),
                )
            } else {
                emptyList()
            }

            UsageResult.Success(
                UsageReport(
                    requestedPeriod = period,
                    collectedAt = clock.instant(),
                    source = UsageSource.SIMULATED,
                    apps = apps,
                ),
            )
        }
    }
}
