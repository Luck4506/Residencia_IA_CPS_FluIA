package com.fluia.fluiagent

import android.content.ActivityNotFoundException
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.TextButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.fluia.fluiagent.ui.theme.MyApplicationTheme
import com.fluia.fluiagent.ui.UsageHomeScreen
import com.fluia.fluiagent.usage.AndroidUsageRepository
import com.fluia.fluiagent.usage.UsageAccessChecker
import com.fluia.fluiagent.usage.UsageAccessStatus
import com.fluia.fluiagent.usage.UsageViewModel

/** Coordena o ciclo de vida e a navegação para as configurações do sistema. */
class MainActivity : ComponentActivity() {
    private lateinit var accessChecker: UsageAccessChecker
    private lateinit var usageViewModel: UsageViewModel

    // O Compose redesenha a tela quando esses estados mudam. Não salvamos uma
    // autorização antiga: ela sempre é consultada novamente ao retomar o app.
    private var accessStatus by mutableStateOf(UsageAccessStatus.UNAVAILABLE)
    private var settingsError by mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        accessChecker = UsageAccessChecker(this)
        // A fábrica injeta o repositório real. O ViewModelProvider reutiliza o
        // mesmo ViewModel após rotação, sem iniciar uma nova consulta automaticamente.
        usageViewModel = ViewModelProvider(this, object : ViewModelProvider.Factory {
            override fun <T : ViewModel> create(modelClass: Class<T>): T {
                require(modelClass == UsageViewModel::class.java)
                @Suppress("UNCHECKED_CAST")
                return UsageViewModel(AndroidUsageRepository(applicationContext)) as T
            }
        })[UsageViewModel::class.java]
        refreshAccess()
        enableEdgeToEdge()
        setContent {
            MyApplicationTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    // A autorização define a tela atual, sem empilhar a tela de
                    // permissão no histórico. onResume atualiza esse estado ao
                    // voltar das configurações; revogar o acesso faz o caminho inverso.
                    if (accessStatus == UsageAccessStatus.GRANTED) {
                        UsageHomeScreen(
                            state = usageViewModel.state,
                            onQuery = usageViewModel::querySelectedPeriod,
                            onSelectPeriod = usageViewModel::selectPreset,
                            settingsError = settingsError,
                            onManageAccess = ::openUsageSettings,
                            modifier = Modifier.padding(innerPadding),
                        )
                    } else {
                        UsageAccessScreen(
                            status = accessStatus,
                            settingsError = settingsError,
                            onOpenSettings = ::openUsageSettings,
                            onRefresh = ::refreshAccess,
                            modifier = Modifier.padding(innerPadding),
                        )
                    }
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Também cobre recusa, concessão ou revogação enquanto o app estava fora
        // de foco. Não usamos o retorno da tela de configurações como autorização.
        refreshAccess()
    }

    private fun refreshAccess() {
        accessStatus = accessChecker.checkAccess()
        if (accessStatus != UsageAccessStatus.GRANTED) usageViewModel.clearUsage()
    }

    private fun openUsageSettings() {
        settingsError = false
        try {
            // Abre a lista de acesso especial do Android. A escolha continua com
            // o usuário; nenhum histórico é consultado ao tocar nesse botão.
            startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS))
        } catch (_: ActivityNotFoundException) {
            settingsError = true
        } catch (_: SecurityException) {
            settingsError = true
        }
    }
}

/** Tela sem chamadas ao Android: recebe estado e ações, permitindo usar Preview. */
@Composable
fun UsageAccessScreen(
    status: UsageAccessStatus,
    settingsError: Boolean,
    onOpenSettings: () -> Unit,
    onRefresh: () -> Unit,
    modifier: Modifier = Modifier,
) {
    // A rolagem mantém as ações acessíveis com fonte ampliada ou tela pequena.
    Column(
        modifier = modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(stringResource(R.string.app_name), style = MaterialTheme.typography.headlineLarge)
        Text(stringResource(R.string.usage_access_title), style = MaterialTheme.typography.titleLarge)
        Text(stringResource(R.string.usage_access_description))
        Text(stringResource(R.string.usage_access_stage))

        val statusText = when (status) {
            UsageAccessStatus.GRANTED -> R.string.usage_access_granted
            UsageAccessStatus.DENIED -> R.string.usage_access_denied
            UsageAccessStatus.UNAVAILABLE -> R.string.usage_access_unavailable
        }
        // Texto explícito comunica o estado sem depender apenas de uma cor.
        Text(stringResource(statusText), style = MaterialTheme.typography.titleMedium)
        Button(onClick = onOpenSettings) {
            Text(stringResource(
                if (status == UsageAccessStatus.GRANTED) R.string.usage_access_manage
                else R.string.usage_access_allow,
            ))
        }
        Text(stringResource(R.string.usage_access_instructions))
        if (settingsError) {
            Text(stringResource(R.string.usage_access_settings_error), color = MaterialTheme.colorScheme.error)
        }
        TextButton(onClick = onRefresh) {
            Text(stringResource(R.string.usage_access_retry))
        }
    }
}

/** Prévia visual sem aparelho, autorização ou consulta a dados reais. */
@Preview(showBackground = true)
@Composable
fun UsageAccessPreview() {
    MyApplicationTheme {
        UsageAccessScreen(UsageAccessStatus.DENIED, false, {}, {})
    }
}
