package com.fluia.fluiagent.usage

import java.time.Duration
import java.time.Instant
import java.time.ZoneId

/** Identificadores estáveis para os períodos usados pela tela e pela futura ponte dos agentes. */
enum class UsagePeriodPreset {
    TODAY, LAST_24_HOURS, LAST_72_HOURS, LAST_7_DAYS;

    /**
     * Hoje segue o calendário local; os demais intervalos têm duração fixa.
     * O instante de referência é recebido para tornar a resolução reproduzível.
     * Estes são limites solicitados, não garantia de precisão dos agregados Android.
     */
    fun resolve(now: Instant, zone: ZoneId): UsagePeriod? {
        val start = when (this) {
            TODAY -> now.atZone(zone).toLocalDate().atStartOfDay(zone).toInstant()
            LAST_24_HOURS -> now.minus(Duration.ofHours(24))
            LAST_72_HOURS -> now.minus(Duration.ofHours(72))
            LAST_7_DAYS -> now.minus(Duration.ofDays(7))
        }
        // Exatamente à meia-noite TODAY ainda não possui duração consultável em ms.
        return if (start.toEpochMilli() < now.toEpochMilli()) UsagePeriod(start, now) else null
    }
}
