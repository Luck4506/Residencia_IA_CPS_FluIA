package com.fluia.fluiagent.usage

import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.UserManager
import java.time.Clock
import java.util.concurrent.CancellationException

/**
 * Adapta a API Android ao contrato do FluIA. Não agenda coletas nem grava dados.
 * As funções do construtor interno permitem testar autorização e transformação
 * sem acessar o dispositivo; o construtor público conecta os serviços reais.
 */
class AndroidUsageRepository internal constructor(
    private val checkAccess: () -> UsageAccessStatus,
    private val readUsage: (Long, Long) -> List<AppUsage>?,
    private val clock: Clock = Clock.systemUTC(),
) : UsageRepository {
    constructor(context: Context) : this(
        checkAccess = UsageAccessChecker(context.applicationContext)::checkAccess,
        readUsage = createReader(context.applicationContext),
    )

    override fun queryUsage(period: UsagePeriod): UsageResult {
        return try {
            accessProblem()?.let { return it }
            // A API recebe milissegundos desde o epoch. Rejeitamos intervalos que
            // perdem toda a duração na conversão, em vez de consultar limites iguais.
            val startMs = period.start.toEpochMilli()
            val endMs = period.end.toEpochMilli()
            if (startMs >= endMs) {
                return UsageResult.Failure("O período precisa ter ao menos um milissegundo.")
            }
            val records = readUsage(startMs, endMs)
            // Uma revogação durante a leitura não deve resultar em lista vazia ou
            // na exibição de um relatório obtido com uma autorização já revogada.
            accessProblem()?.let { return it }
            if (records == null) {
                return UsageResult.Failure("Dados indisponíveis. Desbloqueie o aparelho e tente novamente.")
            }

            val apps = records.filter { it.foregroundTimeMs > 0 }
                .sortedWith(compareByDescending<AppUsage> { it.foregroundTimeMs }.thenBy { it.packageName })
            UsageResult.Success(
                UsageReport(period, clock.instant(), UsageSource.ANDROID_USAGE_STATS, apps),
            )
        } catch (error: CancellationException) {
            throw error // Cancelar uma consulta não é uma falha a mostrar ao usuário.
        } catch (_: SecurityException) {
            UsageResult.AccessDenied
        } catch (_: RuntimeException) {
            // Não exibimos mensagens internas que possam conter dados do aparelho.
            UsageResult.Failure("Não foi possível consultar o uso. Tente novamente.")
        }
    }

    /** Falha na verificação é diferente de uma recusa conhecida. */
    private fun accessProblem(): UsageResult? = when (checkAccess()) {
        UsageAccessStatus.GRANTED -> null
        UsageAccessStatus.DENIED -> UsageResult.AccessDenied
        UsageAccessStatus.UNAVAILABLE -> UsageResult.Failure("Não foi possível verificar o acesso ao uso.")
    }

    companion object {
        /** Usa somente applicationContext para não reter uma Activity antiga. */
        private fun createReader(context: Context): (Long, Long) -> List<AppUsage>? = { start, end ->
            val manager = context.getSystemService(UsageStatsManager::class.java)
            val userManager = context.getSystemService(UserManager::class.java)
            if (manager == null || userManager?.isUserUnlocked != true) {
                null
            } else {
                // O Android agrupa por pacote e pode expandir o período solicitado.
                // totalTimeInForeground não é duração de serviço em primeiro plano.
                manager.queryAndAggregateUsageStats(start, end)?.map { (packageName, stats) ->
                    resolveApp(context, packageName, stats.totalTimeInForeground)
                }
            }
        }

        @Suppress("DEPRECATION") // Esta sobrecarga continua compatível com o mínimo API 26.
        private fun resolveApp(context: Context, packageName: String, durationMs: Long): AppUsage = try {
            // A visibilidade de pacotes pode impedir obter o nome; isso não elimina
            // a estatística. Não solicitamos QUERY_ALL_PACKAGES para resolver nomes.
            val packages = context.packageManager
            val info = packages.getApplicationInfo(packageName, 0)
            val name = packages.getApplicationLabel(info).toString().ifBlank { packageName }
            // Categoria é metadado de ApplicationInfo, não uma estatística de uso.
            // API disponível desde 26; categorias indefinidas retornam null.
            val category = ApplicationInfo.getCategoryTitle(context, info.category)
                ?.toString()?.takeIf { it.isNotBlank() }
            AppUsage(packageName, name, durationMs, category)
        } catch (_: PackageManager.NameNotFoundException) {
            AppUsage(packageName, packageName, durationMs)
        } catch (_: SecurityException) {
            AppUsage(packageName, packageName, durationMs)
        }
    }
}
