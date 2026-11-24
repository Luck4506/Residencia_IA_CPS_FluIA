package com.fluia.fluiagent.usage

import java.time.Instant
import java.time.ZoneId
import org.junit.Assert.*
import org.junit.Test

/** Casos de fronteira de datas e duração, independentes do Android. */
class UsagePresentationTest {
    @Test
    fun `inicio do dia respeita fuso local e horario de verao`() {
        val now = Instant.parse("2026-03-08T16:00:00Z")
        val period = usagePeriodToday(now, ZoneId.of("America/New_York"))!!
        // O início do dia ainda estava em UTC-5; ao meio-dia local já é UTC-4.
        assertEquals(Instant.parse("2026-03-08T05:00:00Z"), period.start)
        assertEquals(now, period.end)
    }

    @Test
    fun `meia noite exata nao cria periodo vazio`() {
        assertNull(usagePeriodToday(Instant.parse("2026-11-17T03:00:00Z"), ZoneId.of("America/Sao_Paulo")))
    }

    @Test
    fun `formata limites sem confundir milissegundos com segundos`() {
        assertEquals("0 s", formatUsageDuration(0))
        assertEquals("menos de 1 s", formatUsageDuration(999))
        assertEquals("59 s", formatUsageDuration(59_999))
        assertEquals("1 min 0 s", formatUsageDuration(60_000))
        assertEquals("1 h 1 min 1 s", formatUsageDuration(3_661_999))
        assertEquals("25 h 0 min 0 s", formatUsageDuration(90_000_000))
    }
}
