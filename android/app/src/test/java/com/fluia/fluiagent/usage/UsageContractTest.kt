package com.fluia.fluiagent.usage

import java.time.Clock
import java.time.Instant
import java.time.ZoneOffset
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** Testes locais do contrato: não acessam Android, rede ou dados pessoais. */
class UsageContractTest {
    private val start = Instant.parse("2026-11-17T03:00:00Z")
    private val end = Instant.parse("2026-11-17T15:00:00Z")
    private val period = UsagePeriod(start, end)
    private val clock = Clock.fixed(end, ZoneOffset.UTC)

    @Test(expected = IllegalArgumentException::class)
    fun `rejeita periodo invertido`() {
        UsagePeriod(end, start)
    }

    @Test(expected = IllegalArgumentException::class)
    fun `rejeita periodo sem duracao`() {
        UsagePeriod(start, start)
    }

    @Test(expected = IllegalArgumentException::class)
    fun `rejeita duracao negativa`() {
        AppUsage("example.app", "App fictício", -1)
    }

    @Test
    fun `preserva duracoes sem arredondamento inclusive zero`() {
        assertEquals(0L, AppUsage("example.app", "App fictício", 0).foregroundTimeMs)
        assertEquals(60_001L, AppUsage("example.app", "App fictício", 60_001).foregroundTimeMs)
    }

    @Test
    fun `simulacao identifica origem e preserva periodo e instante da consulta`() {
        val repository: UsageRepository = FakeUsageRepository(clock = clock)
        val report = (repository.queryUsage(period) as UsageResult.Success).report

        assertEquals(period, report.requestedPeriod)
        assertEquals(end, report.collectedAt)
        assertEquals(UsageSource.SIMULATED, report.source)
        assertTrue(report.apps.isNotEmpty())
        assertTrue(report.apps.all { it.appName.contains("simulado") })
    }

    @Test
    fun `sucesso vazio nao se confunde com acesso negado ou falha`() {
        val empty = FakeUsageRepository(FakeUsageRepository.Scenario.EMPTY, clock)
            .queryUsage(period)
        val denied = FakeUsageRepository(FakeUsageRepository.Scenario.ACCESS_DENIED, clock)
            .queryUsage(period)
        val failure = FakeUsageRepository(FakeUsageRepository.Scenario.FAILURE, clock)
            .queryUsage(period)

        assertTrue((empty as UsageResult.Success).report.apps.isEmpty())
        assertEquals(UsageResult.AccessDenied, denied)
        assertTrue(failure is UsageResult.Failure)
        assertNotEquals(empty, denied)
        assertNotEquals(empty, failure)
    }
}
