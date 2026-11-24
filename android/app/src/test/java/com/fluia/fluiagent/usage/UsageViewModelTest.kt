package com.fluia.fluiagent.usage

import java.time.Clock
import java.time.Instant
import java.time.ZoneOffset
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/** Controla as coroutines sem espera real e sem implementar testes E2E. */
@OptIn(ExperimentalCoroutinesApi::class)
class UsageViewModelTest {
    private val dispatcher = StandardTestDispatcher()
    private val clock = Clock.fixed(Instant.parse("2026-11-17T12:00:00Z"), ZoneOffset.UTC)

    @Before fun setup() { Dispatchers.setMain(dispatcher) }
    @After fun cleanup() { Dispatchers.resetMain() }

    private fun model(repository: UsageRepository) = UsageViewModel(repository, clock, { ZoneOffset.UTC }, dispatcher)

    @Test
    fun `selecionar periodo nao consulta e limpa resultado anterior`() = runTest {
        var calls = 0
        var received: UsagePeriod? = null
        val vm = model(object : UsageRepository {
            override fun queryUsage(period: UsagePeriod): UsageResult {
                calls++
                received = period
                return UsageResult.Success(UsageReport(period, clock.instant(), UsageSource.SIMULATED, emptyList()))
            }
        })
        vm.queryToday()
        advanceUntilIdle()
        vm.selectPreset(UsagePeriodPreset.LAST_72_HOURS)
        assertEquals(1, calls)
        assertNull(vm.state.result)
        vm.querySelectedPeriod()
        // Uma mudança enquanto a leitura está em andamento não troca o rótulo.
        vm.selectPreset(UsagePeriodPreset.LAST_24_HOURS)
        assertEquals(UsagePeriodPreset.LAST_72_HOURS, vm.state.preset)
        advanceUntilIdle()
        assertEquals(2, calls)
        assertEquals(UsagePeriodPreset.LAST_72_HOURS.resolve(clock.instant(), ZoneOffset.UTC), received)
        assertEquals(UsagePeriodPreset.LAST_72_HOURS, vm.state.preset)
    }

    @Test
    fun `nao consulta ao criar e evita duplo clique durante leitura`() = runTest {
        var calls = 0
        val vm = model(object : UsageRepository {
            override fun queryUsage(period: UsagePeriod): UsageResult {
                calls++
                return UsageResult.Success(UsageReport(period, clock.instant(), UsageSource.SIMULATED, emptyList()))
            }
        })
        assertEquals(0, calls)
        assertNull(vm.state.result)
        vm.queryToday()
        assertTrue(vm.state.loading)
        vm.queryToday()
        advanceUntilIdle()
        assertEquals(1, calls)
        assertFalse(vm.state.loading)
        assertTrue(vm.state.result is UsageResult.Success)
    }

    @Test
    fun `apresenta os quatro resultados e permite nova tentativa`() = runTest {
        for (scenario in FakeUsageRepository.Scenario.entries) {
            val vm = model(FakeUsageRepository(scenario, clock))
            vm.queryToday()
            advanceUntilIdle()
            assertFalse(vm.state.loading)
            when (scenario) {
                FakeUsageRepository.Scenario.WITH_DATA -> assertTrue((vm.state.result as UsageResult.Success).report.apps.isNotEmpty())
                FakeUsageRepository.Scenario.EMPTY -> assertTrue((vm.state.result as UsageResult.Success).report.apps.isEmpty())
                FakeUsageRepository.Scenario.ACCESS_DENIED -> assertEquals(UsageResult.AccessDenied, vm.state.result)
                FakeUsageRepository.Scenario.FAILURE -> assertTrue(vm.state.result is UsageResult.Failure)
            }
            vm.queryToday()
            assertTrue(vm.state.loading)
            assertNull(vm.state.result)
            advanceUntilIdle()
        }
    }

    @Test
    fun `revogacao limpa relatorio e cancela consulta pendente`() = runTest {
        val vm = model(FakeUsageRepository(clock = clock))
        vm.queryToday()
        advanceUntilIdle()
        assertNotNull(vm.state.result)
        vm.clearUsage()
        assertNull(vm.state.result)
        vm.queryToday()
        vm.clearUsage()
        advanceUntilIdle()
        assertNull(vm.state.result)
        assertFalse(vm.state.loading)
    }

    @Test
    fun `excecao inesperada nao deixa a tela carregando nem expoe mensagem interna`() = runTest {
        val vm = model(object : UsageRepository {
            override fun queryUsage(period: UsagePeriod): UsageResult = error("Detalhe privado")
        })
        vm.queryToday()
        advanceUntilIdle()
        assertFalse(vm.state.loading)
        assertFalse((vm.state.result as UsageResult.Failure).message.contains("privado"))
    }
}
