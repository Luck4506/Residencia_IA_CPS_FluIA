package com.fluia.fluiagent.usage

import java.time.Duration
import java.time.Instant
import java.time.ZoneId
import org.junit.Assert.*
import org.junit.Test

/** Diferencia calendário local de janelas móveis, inclusive ao mudar o fuso. */
class UsagePeriodsTest {
    private val zone = ZoneId.of("America/Sao_Paulo")

    @Test
    fun `hoje comeca a meia noite local e nao vinte e quatro horas antes`() {
        val now = Instant.parse("2026-11-24T13:30:00Z")
        assertEquals(Instant.parse("2026-11-24T03:00:00Z"), UsagePeriodPreset.TODAY.resolve(now, zone)!!.start)
        assertEquals(Instant.parse("2026-11-23T13:30:00Z"), UsagePeriodPreset.LAST_24_HOURS.resolve(now, zone)!!.start)
    }

    @Test
    fun `janelas moveis preservam duracao em mudanca de horario de verao`() {
        val now = Instant.parse("2026-03-08T16:00:00Z")
        for ((preset, hours) in listOf(UsagePeriodPreset.LAST_24_HOURS to 24L,
            UsagePeriodPreset.LAST_72_HOURS to 72L, UsagePeriodPreset.LAST_7_DAYS to 168L)) {
            val period = preset.resolve(now, ZoneId.of("America/New_York"))!!
            assertEquals(Duration.ofHours(hours), Duration.between(period.start, period.end))
            assertEquals(now, period.end)
            assertEquals(period, preset.resolve(now, zone))
        }
    }

    @Test
    fun `virada de mes e meia noite nao confundem calendario com janela movel`() {
        val now = Instant.parse("2026-12-01T03:00:00Z")
        assertNull(UsagePeriodPreset.TODAY.resolve(now, zone))
        assertEquals(Instant.parse("2026-11-28T03:00:00Z"), UsagePeriodPreset.LAST_72_HOURS.resolve(now, zone)!!.start)
    }
}
