package com.fluia.fluiagent.usage

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import java.time.Clock
import java.time.ZoneId
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Estado em memória, preservado na rotação e descartado ao encerrar o processo. */
data class UsageUiState(
    val loading: Boolean = false,
    val result: UsageResult? = null,
    val zone: ZoneId = ZoneId.systemDefault(),
    val preset: UsagePeriodPreset = UsagePeriodPreset.TODAY,
)

/** Coordena a consulta sem colocar acesso ao Android dentro dos composables. */
class UsageViewModel(
    private val repository: UsageRepository,
    private val clock: Clock = Clock.systemUTC(),
    private val zoneProvider: () -> ZoneId = { ZoneId.systemDefault() },
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO,
) : ViewModel() {
    var state by mutableStateOf(UsageUiState())
        private set
    private var queryJob: Job? = null

    /** Compatibilidade para chamadas que explicitamente pedem o dia atual. */
    fun queryToday() {
        if (state.loading) return
        selectPreset(UsagePeriodPreset.TODAY)
        querySelectedPeriod()
    }

    /** Trocar a seleção não coleta dados e limpa resultados de outro período. */
    fun selectPreset(preset: UsagePeriodPreset) {
        if (state.loading || preset == state.preset) return
        state = UsageUiState(preset = preset, zone = state.zone)
    }

    /** O relógio é lido no clique, não quando o usuário abriu o seletor. */
    fun querySelectedPeriod() {
        if (state.loading) return
        val zone = zoneProvider()
        val preset = state.preset
        val period = preset.resolve(clock.instant(), zone)
        if (period == null) {
            state = UsageUiState(result = UsageResult.Failure("O dia acabou de começar. Aguarde e tente novamente."), zone = zone, preset = preset)
            return
        }
        // Limpa o relatório anterior para não apresentá-lo como resultado da nova consulta.
        state = UsageUiState(loading = true, zone = zone, preset = preset)
        queryJob = viewModelScope.launch {
            val result = try {
                withContext(ioDispatcher) { repository.queryUsage(period) }
            } catch (error: CancellationException) {
                throw error
            } catch (_: Exception) {
                UsageResult.Failure("Não foi possível consultar o uso. Tente novamente.")
            }
            state = UsageUiState(result = result, zone = zone, preset = preset)
        }
    }

    /** Ao perder autorização, cancela a leitura e remove dados antigos da tela. */
    fun clearUsage() {
        queryJob?.cancel()
        queryJob = null
        state = UsageUiState(preset = state.preset)
    }
}
