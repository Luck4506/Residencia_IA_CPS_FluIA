package com.fluia.fluiagent.usage

import android.Manifest
import android.app.AppOpsManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build

/** Falha na verificação não deve aparecer como autorização concedida ou recusada. */
enum class UsageAccessStatus { GRANTED, DENIED, UNAVAILABLE }

/**
 * Consulta somente a autorização do próprio FluIA, sem ler histórico de uso.
 * Esse acesso especial é concedido nas configurações, não por um diálogo de
 * requestPermissions. A consulta real também precisará tratar eventual revogação.
 */
class UsageAccessChecker(context: Context) {
    // O contexto da aplicação evita manter uma Activity antiga após sua recriação.
    private val appContext = context.applicationContext

    @Suppress("DEPRECATION") // Os métodos antigos são necessários nas APIs anteriores à 36.
    fun checkAccess(): UsageAccessStatus {
        val appOps = appContext.getSystemService(AppOpsManager::class.java)
            ?: return UsageAccessStatus.UNAVAILABLE

        return try {
            val uid = appContext.applicationInfo.uid
            val packageName = appContext.packageName
            val mode = if (Build.VERSION.SDK_INT >= 36) {
                appOps.checkOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, uid, packageName)
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                appOps.unsafeCheckOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, uid, packageName)
            } else {
                appOps.checkOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, uid, packageName)
            }

            // MODE_DEFAULT delega a decisão à permissão do pacote; em instalações
            // comuns ela não está concedida até o usuário habilitar o acesso especial.
            val allowed = mode == AppOpsManager.MODE_ALLOWED ||
                (mode == AppOpsManager.MODE_DEFAULT &&
                    appContext.checkSelfPermission(Manifest.permission.PACKAGE_USAGE_STATS) ==
                    PackageManager.PERMISSION_GRANTED)

            if (allowed) UsageAccessStatus.GRANTED else UsageAccessStatus.DENIED
        } catch (_: SecurityException) {
            UsageAccessStatus.UNAVAILABLE
        }
    }
}
