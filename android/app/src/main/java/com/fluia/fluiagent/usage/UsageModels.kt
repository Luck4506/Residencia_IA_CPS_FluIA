package com.fluia.fluiagent.usage

import java.time.Instant

/**
 * Período solicitado: início inclusivo e fim exclusivo, como instantes absolutos.
 * A tela converte o início do dia no fuso local para Instant antes de consultar.
 * Isso evita confundir horário local com um timestamp UTC na integração futura.
 */
data class UsagePeriod(val start: Instant, val end: Instant) {
    init {
        require(start < end) { "O início deve ser anterior ao fim do período." }
    }
}

/**
 * Tempo em primeiro plano de um pacote, em milissegundos, sem arredondamento.
 * Não representa automaticamente tempo total de tela ou prejuízo ao usuário.
 * Quando o nome não estiver disponível, a implementação usará o próprio pacote.
 */
data class AppUsage(
    val packageName: String,
    val appName: String,
    val foregroundTimeMs: Long,
    // Título localizado fornecido pelo Android; null significa não informado ou
    // indisponível. Não inferimos categoria a partir do nome ou do comportamento.
    val category: String? = null,
) {
    init {
        require(packageName.isNotBlank()) { "O pacote não pode estar vazio." }
        require(appName.isNotBlank()) { "O nome não pode estar vazio." }
        require(foregroundTimeMs >= 0) { "A duração não pode ser negativa." }
    }
}

/** A origem acompanha os dados para impedir que a simulação pareça coleta real. */
enum class UsageSource {
    SIMULATED,
    ANDROID_USAGE_STATS,
}

/**
 * Relatório compartilhado pela tela e, futuramente, pelo monitor e pelos agentes.
 * requestedPeriod é o intervalo pedido, não uma garantia da cobertura exata:
 * o Android pode expandi-lo para seus intervalos de agregação.
 * collectedAt indica quando consultamos, não quando o Android atualizou os dados.
 * Uma lista vazia significa ausência de registros retornados, não prova de uso zero.
 */
data class UsageReport(
    val requestedPeriod: UsagePeriod,
    val collectedAt: Instant,
    val source: UsageSource,
    val apps: List<AppUsage>,
)

/** Estados explícitos evitam transformar falta de autorização ou erro em uso zero. */
sealed interface UsageResult {
    data class Success(val report: UsageReport) : UsageResult
    data object AccessDenied : UsageResult

    // Mensagem controlada pela implementação, sem incluir histórico pessoal ou stack trace.
    data class Failure(val message: String) : UsageResult
}
