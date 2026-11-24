package com.fluia.fluiagent.usage

import java.time.Clock
import java.time.Instant
import java.time.ZoneOffset
import org.junit.Assert.*
import org.junit.Test

/** Testa a adaptação com funções controladas; nenhum dado do dispositivo é lido. */
class AndroidUsageRepositoryTest {
    private val start = Instant.parse("2026-11-17T03:00:00Z")
    private val end = Instant.parse("2026-11-17T12:00:00Z")
    private val period = UsagePeriod(start, end)
    private val clock = Clock.fixed(end, ZoneOffset.UTC)

    @Test
    fun `preserva periodo e unidades filtra zero e ordena sem top dez`() {
        val repository = AndroidUsageRepository(
            { UsageAccessStatus.GRANTED },
            { from, to ->
                assertEquals(start.toEpochMilli(), from)
                assertEquals(end.toEpochMilli(), to)
                (0..12).map { AppUsage("example.$it", "Fictício $it", it * 1_001L) }
            }, clock,
        )
        val report = (repository.queryUsage(period) as UsageResult.Success).report
        assertEquals(12, report.apps.size)
        assertEquals(12_012L, report.apps.first().foregroundTimeMs)
        assertEquals(1_001L, report.apps.last().foregroundTimeMs)
        assertEquals(period, report.requestedPeriod)
        assertEquals(end, report.collectedAt)
        assertEquals(UsageSource.ANDROID_USAGE_STATS, report.source)
    }

    @Test
    fun `acesso negado ou indisponivel impede a leitura`() {
        for (status in listOf(UsageAccessStatus.DENIED, UsageAccessStatus.UNAVAILABLE)) {
            var calls = 0
            val repository = AndroidUsageRepository({ status }, { _, _ -> calls++; emptyList() }, clock)
            val result = repository.queryUsage(period)
            assertEquals(0, calls)
            if (status == UsageAccessStatus.DENIED) assertEquals(UsageResult.AccessDenied, result)
            else assertTrue(result is UsageResult.Failure)
        }
    }

    @Test
    fun `revogacao durante consulta descarta resultado`() {
        var status = UsageAccessStatus.GRANTED
        val repository = AndroidUsageRepository({ status }, { _, _ ->
            status = UsageAccessStatus.DENIED
            listOf(AppUsage("example.app", "Fictício", 1_000))
        }, clock)
        assertEquals(UsageResult.AccessDenied, repository.queryUsage(period))
    }

    @Test
    fun `distingue vazio indisponibilidade e excecao`() {
        fun repository(read: (Long, Long) -> List<AppUsage>?) =
            AndroidUsageRepository({ UsageAccessStatus.GRANTED }, read, clock)
        val empty = repository { _, _ -> emptyList() }.queryUsage(period) as UsageResult.Success
        assertTrue(empty.report.apps.isEmpty())
        assertTrue(repository { _, _ -> null }.queryUsage(period) is UsageResult.Failure)
        assertEquals(UsageResult.AccessDenied, repository { _, _ -> throw SecurityException() }.queryUsage(period))
        val failure = repository { _, _ -> error("Dado privado fictício") }.queryUsage(period) as UsageResult.Failure
        assertFalse(failure.message.contains("privado"))
    }

    @Test
    fun `rejeita intervalo que desaparece ao converter para milissegundos`() {
        var read = false
        val repository = AndroidUsageRepository({ UsageAccessStatus.GRANTED }, { _, _ ->
            read = true
            emptyList()
        }, clock)
        assertTrue(repository.queryUsage(UsagePeriod(start, start.plusNanos(1))) is UsageResult.Failure)
        assertFalse(read)
    }
}
