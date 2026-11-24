package com.fluia.fluiagent.usage

import java.time.Instant
import java.time.ZoneId

/** Usa o início real do dia no fuso local, inclusive em mudanças de horário de verão. */
fun usagePeriodToday(now: Instant, zone: ZoneId): UsagePeriod? {
    return UsagePeriodPreset.TODAY.resolve(now, zone)
}

/** A apresentação arredonda para baixo; o contrato preserva os milissegundos. */
fun formatUsageDuration(milliseconds: Long): String {
    require(milliseconds >= 0) { "A duração não pode ser negativa." }
    if (milliseconds == 0L) return "0 s"
    if (milliseconds < 1_000L) return "menos de 1 s"
    val seconds = milliseconds / 1_000
    val hours = seconds / 3_600
    val minutes = (seconds % 3_600) / 60
    val remainingSeconds = seconds % 60
    return when {
        hours > 0 -> "${hours} h ${minutes} min ${remainingSeconds} s"
        minutes > 0 -> "${minutes} min ${remainingSeconds} s"
        else -> "${seconds} s"
    }
}
