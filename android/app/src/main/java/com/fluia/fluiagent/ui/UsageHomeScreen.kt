package com.fluia.fluiagent.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.clickable
import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.fluia.fluiagent.R
import com.fluia.fluiagent.ui.theme.MyApplicationTheme
import com.fluia.fluiagent.usage.UsageResult
import com.fluia.fluiagent.usage.AppUsage
import com.fluia.fluiagent.usage.UsageSource
import com.fluia.fluiagent.usage.UsageUiState
import com.fluia.fluiagent.usage.UsagePeriodPreset
import com.fluia.fluiagent.usage.formatUsageDuration
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Apenas apresenta o estado; a leitura do dispositivo pertence ao repositório. */
@Composable
fun UsageHomeScreen(
    state: UsageUiState,
    onQuery: () -> Unit,
    settingsError: Boolean,
    onManageAccess: () -> Unit,
    modifier: Modifier = Modifier,
    onSelectPeriod: (UsagePeriodPreset) -> Unit = {},
) {
    val result = state.result
    val report = (result as? UsageResult.Success)?.report
    val dateFormat = DateTimeFormatter.ofPattern("dd/MM/yyyy HH:mm:ss", Locale.forLanguageTag("pt-BR"))
        .withZone(state.zone)

    // LazyColumn cria os itens conforme aparecem, sem limitar o relatório a top 10.
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item {
            Text(stringResource(R.string.app_name), style = MaterialTheme.typography.headlineLarge)
            Text(stringResource(R.string.usage_home_title), style = MaterialTheme.typography.titleLarge)
            if (result != UsageResult.AccessDenied) Text(stringResource(R.string.usage_access_granted))
        }
        item { Text(stringResource(R.string.usage_query_description)) }
        item {
            // Seleção explícita, sem disparar coleta; desabilitada durante a leitura.
            var menuOpen by rememberSaveable { mutableStateOf(false) }
            Box {
                OutlinedButton(onClick = { menuOpen = true }, enabled = !state.loading) {
                    Text(stringResource(R.string.usage_selected_period, stringResource(periodLabel(state.preset))))
                }
                DropdownMenu(expanded = menuOpen && !state.loading, onDismissRequest = { menuOpen = false }) {
                    UsagePeriodPreset.entries.forEach { preset ->
                        DropdownMenuItem(text = { Text(stringResource(periodLabel(preset))) }, onClick = {
                            menuOpen = false
                            onSelectPeriod(preset)
                        })
                    }
                }
            }
        }
        item {
            Button(onClick = onQuery, enabled = !state.loading) {
                Text(stringResource(if (state.loading) R.string.usage_loading else R.string.usage_query))
            }
        }
        item {
            TextButton(onClick = onManageAccess) { Text(stringResource(R.string.usage_access_manage)) }
            if (settingsError) {
                Text(stringResource(R.string.usage_access_settings_error), color = MaterialTheme.colorScheme.error)
            }
        }
        if (state.loading) {
            item { CircularProgressIndicator() }
        }
        when (result) {
            null -> if (!state.loading) item { Text(stringResource(R.string.usage_idle)) }
            UsageResult.AccessDenied -> item {
                Text(stringResource(R.string.usage_query_denied), color = MaterialTheme.colorScheme.error)
            }
            is UsageResult.Failure -> item { Text(result.message, color = MaterialTheme.colorScheme.error) }
            is UsageResult.Success -> Unit // Metadados e lista são apresentados abaixo.
        }
        if (report != null) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(stringResource(
                        if (report.source == UsageSource.SIMULATED) R.string.usage_source_simulated
                        else R.string.usage_source_android,
                    ), style = MaterialTheme.typography.titleMedium)
                    Text(stringResource(R.string.usage_period,
                        dateFormat.format(report.requestedPeriod.start),
                        dateFormat.format(report.requestedPeriod.end), state.zone.id))
                    Text(stringResource(R.string.usage_collected, dateFormat.format(report.collectedAt)))
                    Text(stringResource(R.string.usage_aggregation_notice))
                    Text(stringResource(R.string.usage_filter_notice))
                }
            }
            if (report.apps.isEmpty()) item { Text(stringResource(R.string.usage_empty)) }
            else item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text(stringResource(R.string.usage_app_column), Modifier.weight(1f), style = MaterialTheme.typography.labelLarge)
                    Text(stringResource(R.string.usage_time_column), style = MaterialTheme.typography.labelLarge)
                }
                Text(stringResource(R.string.usage_expand_hint), style = MaterialTheme.typography.bodySmall)
            }
            items(report.apps, key = { it.packageName }) { app ->
                UsageAppRow(app)
            }
        }
    }
}

/** Rótulos da tela ficam separados dos identificadores do contrato. */
private fun periodLabel(preset: UsagePeriodPreset): Int = when (preset) {
    UsagePeriodPreset.TODAY -> R.string.usage_period_today
    UsagePeriodPreset.LAST_24_HOURS -> R.string.usage_period_24h
    UsagePeriodPreset.LAST_72_HOURS -> R.string.usage_period_72h
    UsagePeriodPreset.LAST_7_DAYS -> R.string.usage_period_7d
}

/**
 * A linha recolhida prioriza nome e duração. Detalhes são locais à apresentação:
 * expandir não dispara outra consulta. A chave do pacote mantém a expansão ligada
 * ao aplicativo correto durante rolagem e rotação, mesmo se a ordem mudar.
 */
@Composable
private fun UsageAppRow(app: AppUsage, initiallyExpanded: Boolean = false) {
    var expanded by rememberSaveable(app.packageName) { mutableStateOf(initiallyExpanded) }
    val action = stringResource(if (expanded) R.string.usage_collapse else R.string.usage_expand)
    val expansionState = stringResource(if (expanded) R.string.usage_expanded else R.string.usage_collapsed)
    Column(Modifier.fillMaxWidth().animateContentSize()) {
        Row(
            modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
                .semantics { stateDescription = expansionState }
                .clickable(role = Role.Button, onClickLabel = action) { expanded = !expanded }
                .padding(vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            // O sinal é decorativo: leitores de tela recebem ação e estado acima.
            Text(if (expanded) "−" else "+", Modifier.clearAndSetSemantics {})
            Text(app.appName, Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.titleMedium)
            Text(formatUsageDuration(app.foregroundTimeMs), Modifier.weight(0.8f),
                textAlign = TextAlign.End, style = MaterialTheme.typography.bodyMedium)
        }
        if (expanded) {
            Column(Modifier.padding(bottom = 12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                // Repete o nome completo aqui para permitir ler nomes truncados na linha.
                Text(app.appName, style = MaterialTheme.typography.titleSmall)
                Text(stringResource(R.string.usage_package_detail, app.packageName))
                Text(stringResource(R.string.usage_category_detail,
                    app.category ?: stringResource(R.string.usage_category_unknown)))
            }
        }
        HorizontalDivider()
    }
}

/** Amostras fictícias para conferir linhas recolhida e expandida no Preview. */
@Preview(showBackground = true, widthDp = 360)
@Composable
fun UsageRowsPreview() {
    MyApplicationTheme {
        Column(Modifier.padding(16.dp)) {
            UsageAppRow(AppUsage("example.reader", "Leitor (simulado)", 3_661_000))
            UsageAppRow(AppUsage("example.video", "Vídeo (simulado)", 120_000, "Vídeo"), initiallyExpanded = true)
            UsageAppRow(AppUsage("example.long.package.without.name", "example.long.package.without.name", 1_000), initiallyExpanded = true)
        }
    }
}

/** Prévia inicial sem consulta, autorização ou dados reais. */
@Preview(showBackground = true)
@Composable
fun UsageHomePreview() {
    MyApplicationTheme { UsageHomeScreen(UsageUiState(), {}, false, {}) }
}
