"""
================================================================================
FluIA — SISTEMA MULTIAGENTE DE BEM-ESTAR DIGITAL (MVP 01 — PoLP + OLLAMA/QWEN)
================================================================================
Evolução do MVP 00 integrando Modelo de Linguagem Local (Ollama / Qwen2.5) via
API HTTP local (ou LangChain ChatOllama quando disponível) dentro dos agentes:
  • #5 AgenteAcaoPrescricaoFluIA: Redige recomendações personalizadas fundamentadas
    exclusivamente nos trechos recuperados via RAG (Chunks 44–87), respeitando
    restrições rígidas (needs_color_screen, needs_phone_reachable_for_care_or_work)
    e mantendo fallback determinístico caso o servidor Ollama esteja offline.
  • #3 AgenteChatFluIA: Conduz diálogo empático e contextualizado sobre a sugestão
    já validada pelo Juiz (#4 Agente Analista), sem alterar o conteúdo clínico,
    sem acessar RAG ou logs brutos e registrando o Contrato 1B.

MANTÉM INTEGRALMENTE:
  • Isolamento de Privilégios (PoLP) por agente e por ferramenta
  • Contratos JSON formais datados (YYYY-MM-DD) v1.1
  • Prioridade máxima e inegociável ao Chunk 87 (Segurança)
  • Auditoria pelo Juiz (#4 Agente Analista) antes da entrega ao usuário
================================================================================
"""

import os
import re
import glob
import json
import math
import urllib.request
import urllib.error
from datetime import datetime, timezone
from collections import defaultdict
from typing import Optional, Dict, Any, List


# ==============================================================================
# CLIENTE LLM LOCAL (OLLAMA / QWEN) COM FALLBACK DETERMINÍSTICO SEGURO
# ==============================================================================

class OllamaLocalLLMClient:
    """
    Cliente leve e isolado para inferência local via Ollama (ex.: qwen2.5:7b ou qwen2.5:3b).
    • Não possui acesso a arquivos em disco, telemetria bruta ou base RAG.
    • Recebe apenas o prompt estritamente montado pelo agente autorizado.
    • Possui fallback automático caso o daemon Ollama não esteja ativo no ambiente.
    """
    def __init__(
        self,
        model_name: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        timeout_sec: int = 25,
        temperature: float = 0.3
    ):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.temperature = temperature

    def gerar_resposta(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        Tenta invocar o endpoint local /api/chat do Ollama.
        Retorna None em caso de indisponibilidade para acionar o fallback seguro.
        """
        endpoint = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": 220
            }
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                texto = body.get("message", {}).get("content", "").strip()
                return texto if texto else None
        except (urllib.error.URLError, TimeoutError, ConnectionError, Exception):
            return None


# ==============================================================================
# ETAPA #1 — COLETA E PARSE DE TELEMETRIA ANDROID (ARQUIVOS ADB POR DATA)
# ==============================================================================

def converter_duracao_segundos(duracao_str: str) -> int:
    partes = [int(p) for p in duracao_str.strip().split(":")]
    if len(partes) == 3:
        return partes[0] * 3600 + partes[1] * 60 + partes[2]
    elif len(partes) == 2:
        return partes[0] * 60 + partes[1]
    return int(partes[0])


def extrair_data_referencia(raw_text: str, caminho_arquivo: str) -> str:
    range_match = re.search(r'timeRange="[^"]*?(\d{2})/(\d{2})/(\d{4})[^"]*"', raw_text)
    if range_match:
        todas_datas = re.findall(r'(\d{2})/(\d{2})/(\d{4})', range_match.group(0))
        if todas_datas:
            dia, mes, ano = todas_datas[-1]
            return f"{ano}-{mes}-{dia}"

    eventos_ts = re.findall(r'time="(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}:\d{2}"', raw_text)
    if eventos_ts:
        return eventos_ts[-1]

    nome_match = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(caminho_arquivo))
    if nome_match:
        return nome_match.group(1)

    return datetime.now().strftime("%Y-%m-%d")


def processar_arquivo_telemetria(caminho_arquivo: str) -> dict:
    with open(caminho_arquivo, "r", encoding="utf-8", errors="ignore") as f:
        raw_text = f.read()

    data_ref = extrair_data_referencia(raw_text, caminho_arquivo)
    range_match = re.search(r'timeRange="([^"]+)"', raw_text)
    time_range = range_match.group(1) if range_match else "Não identificado"

    apps_usados = []
    if "In-memory daily stats" in raw_text and "packages" in raw_text:
        bloco = raw_text.split("In-memory daily stats", 1)[1].split("packages", 1)[1]
        for linha in bloco.splitlines():
            s = linha.strip()
            if not s.startswith("package="):
                if apps_usados:
                    break
                continue

            m_pkg = re.search(r"package=([^\s]+)", s)
            m_used = re.search(r'totalTimeUsed="([^"]+)"', s)
            m_fs = re.search(r'totalTimeFS="([^"]+)"', s)
            m_cnt = re.search(r"appLaunchCount=(\d+)", s)

            if m_pkg and m_used:
                pkg = m_pkg.group(1)
                sec_fg = converter_duracao_segundos(m_used.group(1))
                sec_fs = converter_duracao_segundos(m_fs.group(1)) if m_fs else 0
                launches = int(m_cnt.group(1)) if m_cnt else 0

                if sec_fg > 0 or sec_fs > 0:
                    apps_usados.append({
                        "package": pkg,
                        "foreground_str": m_used.group(1),
                        "foreground_minutes": round(sec_fg / 60, 2),
                        "fg_service_str": m_fs.group(1) if m_fs else "00:00",
                        "fg_service_minutes": round(sec_fs / 60, 2),
                        "launch_count": launches
                    })

    apps_usados.sort(key=lambda x: x["foreground_minutes"], reverse=True)

    event_pattern = re.compile(r'time="([^"]+)"\s+type=([A-Z_]+)\s+package=([^\s]+)')
    desbloqueios = 0
    notificacoes = defaultdict(int)
    segundos_noturno = 0.0
    sessoes_ativas = {}

    for linha in raw_text.splitlines():
        m = event_pattern.search(linha)
        if not m:
            continue
        ts_str, ev_type, pkg = m.groups()
        dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")

        if ev_type == "KEYGUARD_HIDDEN":
            desbloqueios += 1
        elif ev_type == "NOTIFICATION_INTERRUPTION":
            notificacoes[pkg] += 1
        elif ev_type == "ACTIVITY_RESUMED":
            sessoes_ativas[pkg] = dt
        elif ev_type in ("ACTIVITY_PAUSED", "ACTIVITY_STOPPED", "SCREEN_NON_INTERACTIVE"):
            alvos = list(sessoes_ativas.keys()) if ev_type == "SCREEN_NON_INTERACTIVE" else ([pkg] if pkg in sessoes_ativas else [])
            for p in alvos:
                start_dt = sessoes_ativas.pop(p)
                dur = (dt - start_dt).total_seconds()
                if 0 < dur < 7200 and 19 <= start_dt.hour <= 23 and p not in ("com.sec.android.app.launcher", "com.android.settings"):
                    segundos_noturno += dur

    apps_trabalho_sistema = {
        "com.ubercab.driver", "co.gigu.app", "com.android.settings",
        "com.sec.android.app.launcher", "com.google.android.permissioncontroller",
        "com.android.systemui"
    }
    tela_total_min = round(sum(a["foreground_minutes"] for a in apps_usados), 2)
    uso_pessoal_min = round(sum(a["foreground_minutes"] for a in apps_usados if a["package"] not in apps_trabalho_sistema), 2)
    top_notif = sorted(notificacoes.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "reference_date": data_ref,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "source_info": {
            "mode": "adb_file_dump",
            "source_file": caminho_arquivo,
            "time_range": time_range
        },
        "summary": {
            "total_screen_minutes": tela_total_min,
            "total_leisure_screen_minutes": uso_pessoal_min,
            "night_window_19h_23h_minutes": round(segundos_noturno / 60, 2),
            "unlock_count": desbloqueios,
            "total_notifications": sum(notificacoes.values()),
            "top_notification_sources": [{"package": k, "count": v} for k, v in top_notif]
        },
        "apps_ranked": apps_usados
    }


def executar_etapa_1_telemetria(pasta_saida: str = "/content/historico_telemetria") -> List[Dict[str, Any]]:
    arquivos_encontrados = []
    for pasta in ["/content/sample_data", "/content", "sample_data", "."]:
        if os.path.isdir(pasta):
            for arq in sorted(glob.glob(os.path.join(pasta, "*.txt"))):
                if os.path.basename(arq) != "README.md" and os.path.basename(arq) not in [os.path.basename(x) for x in arquivos_encontrados]:
                    arquivos_encontrados.append(arq)

    if not arquivos_encontrados:
        raise FileNotFoundError("Nenhum arquivo .txt de telemetria encontrado em /content/sample_data/ ou /content/.")

    os.makedirs(pasta_saida, exist_ok=True)
    historico = []

    for caminho in arquivos_encontrados:
        dados = processar_arquivo_telemetria(caminho)
        data_ref = dados["reference_date"]
        resumo = dados["summary"]

        arquivo_json = os.path.join(pasta_saida, f"telemetria_{data_ref}.json")
        with open(arquivo_json, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

        historico.append(dados)

        print("=================================================================")
        print(f"   #1 TELEMETRIA DO CELULAR COLETADA VIA ARQUIVO ({data_ref})    ")
        print("=================================================================")
        print(f"Arquivo lido:      {caminho}")
        print(f"Janela analisada:  {dados['source_info']['time_range']}")
        print(f"Tela Total (Fg):   {resumo['total_screen_minutes']} min")
        print(f"Uso Pessoal/Lazer: {resumo['total_leisure_screen_minutes']} min (excluindo trabalho/sistema)")
        print(f"Janela Noturna:    {resumo['night_window_19h_23h_minutes']} min (19h às 23h)")
        print(f"Desbloqueios:      {resumo['unlock_count']} (KEYGUARD_HIDDEN)")
        print(f"Notificações:      {resumo['total_notifications']} interrupções")

        print("\n--- Top Aplicativos por Tempo em Primeiro Plano ---")
        for idx, app in enumerate(dados["apps_ranked"], start=1):
            if app["foreground_minutes"] > 0:
                print(f"  {idx:02d}. {app['package']:<40} | {app['foreground_str']:<8} ({app['foreground_minutes']:6.2f} min) | Aberturas: {app['launch_count']}")

        print(f"\n[OK] Dados salvos por data em: {arquivo_json}\n")

    return historico


# ==============================================================================
# ETAPA #2 — CHECK-IN INTERATIVO COM NOME DINÂMICO (08 PERGUNTAS — UMA POR VEZ)
# ==============================================================================

def executar_etapa_2_checkin_8_perguntas(
    pasta_saida: str = "/content/historico_checkins",
    data_referencia: Optional[str] = None
) -> Dict[str, Any]:
    """
    Conduz o check-in diário perguntando inicialmente o nome do usuário (sem valores fixos)
    e fazendo 08 perguntas curtas, uma por vez.
    """
    print("=================================================================")
    print("   ETAPA #2 — CHECK-IN INTERATIVO (08 PERGUNTAS — UMA POR VEZ)   ")
    print("=================================================================")
    print("Bem-vindo ao FluIA! Antes de começarmos, qual é o seu nome?\n")

    while True:
        nome_usuario = input("Digite seu nome: ").strip()
        if nome_usuario:
            break
        print("⚠️ Por favor, informe seu nome para iniciarmos o check-in.\n")

    slug_nome = re.sub(r"[^a-z0-9]+", "_", nome_usuario.lower()).strip("_") or "usuario"
    user_id = f"usr_{slug_nome}_01"

    print(f"\nOlá, {nome_usuario}! Responda às 8 perguntas curtas abaixo (ENTER para avançar):\n")

    def perguntar_texto(numero: int, categoria: str, enunciado: str) -> str:
        while True:
            resp = input(f"[{numero}/8 — {categoria}]\n{enunciado}\n-> ").strip()
            if resp:
                print("-" * 65)
                return resp
            print("⚠️ Por favor, digite uma resposta antes de avançar.\n")

    p1_horario_telas = perguntar_texto(1, "Higiene do Sono", "A que horas você largou ou bloqueou o celular ontem à noite antes de dormir?")
    p2_qualidade_sono = perguntar_texto(2, "Higiene do Sono", "Como foi a qualidade do seu sono (demorou para adormecer, acordou à noite ou acordou disposto)?")
    p3_exercicio_hoje = perguntar_texto(3, "Atividade Física", "Você realizou alguma caminhada, alongamento ou exercício físico hoje? Se sim, qual e por quanto tempo?")
    p4_tempo_sentado = perguntar_texto(4, "Atividade Física", "Passou muitas horas contínuas sentado ou dirigindo hoje sem pausas ativas?")
    p5_progresso_metas = perguntar_texto(5, "Metas de Bem-Estar", "Como você avalia o seu progresso hoje na meta de reduzir o uso noturno de telas?")

    while True:
        p6_txt = input("[6/8 — Nível de Energia]\nDe 1 a 5 (1 = esgotado, 5 = muito disposto), qual é o seu nível de energia agora?\n-> ").strip()
        if p6_txt.isdigit() and 1 <= int(p6_txt) <= 5:
            p6_energia = int(p6_txt)
            print("-" * 65)
            break
        print("⚠️ Digite apenas um número inteiro entre 1 e 5.\n")

    p7_humor = perguntar_texto(7, "Estado Emocional / Humor", "Em uma palavra, como você descreve o seu humor neste momento (ex.: disposto, cansado, focado, estressado)?")

    while True:
        p8_txt = input("[8/8 — Triagem de Bem-Estar Emocional]\nNos últimos dias, você tem sentido tristeza, ansiedade ou esgotamento intenso e persistente? (sim/não)\n-> ").strip().lower()
        if p8_txt in ("sim", "s", "não", "nao", "n"):
            p8_distress = p8_txt in ("sim", "s")
            print("-" * 65)
            break
        print("⚠️ Responda apenas com 'sim' ou 'não'.\n")

    agora = datetime.now(timezone.utc)
    data_str = data_referencia or datetime.now().strftime("%Y-%m-%d")

    print("\n=================================================================")
    print(f"   RESUMO DO CHECK-IN — {nome_usuario.upper()} ({data_str})")
    print("=================================================================")
    print(f"• Usuário:                     {nome_usuario} (ID: {user_id})")
    print(f"1. Horário que largou telas:   {p1_horario_telas}")
    print(f"2. Qualidade do sono:          {p2_qualidade_sono}")
    print(f"3. Exercício/caminhada hoje:   {p3_exercicio_hoje}")
    print(f"4. Tempo sentado/dirigindo:    {p4_tempo_sentado}")
    print(f"5. Progresso nas metas:        {p5_progresso_metas}")
    print(f"6. Nível de energia:           {p6_energia}/5")
    print(f"7. Humor atual:                {p7_humor}")
    print(f"8. Sofrimento persistente:     {'Sim' if p8_distress else 'Não'}")
    print("=================================================================")

    confirmar = input("\nDeseja confirmar e salvar o check-in desta data? (sim/não): ").strip().lower()
    if confirmar not in ("sim", "s", ""):
        print("❌ Operação cancelada. Nenhum arquivo foi salvo.")
        return {}

    contract_1a = {
        "contract_version": "1.1",
        "event_type": "daily_checkin",
        "reference_date": data_str,
        "timestamp": agora.isoformat(),
        "user_id": user_id,
        "user_data": {
            "profile": {
                "name": nome_usuario,
                "preferences": {
                    "notification_window": "19:00-22:00",
                    "communication_tone": "empatico",
                    "do_not_disturb_weekends": True
                },
                "accessibility_or_work_needs": {
                    "needs_color_screen": False,
                    "needs_phone_reachable_for_care_or_work": True,
                    "bedtime_target": "22:30"
                }
            },
            "checkin_payload": {
                "mood": p7_humor,
                "energy_level": p6_energia,
                "persistent_emotional_distress": p8_distress,
                "structured_answers": {
                    "q1_bedtime_screen_cutoff": p1_horario_telas,
                    "q2_sleep_quality": p2_qualidade_sono,
                    "q3_physical_activity": p3_exercicio_hoje,
                    "q4_sedentary_driving_time": p4_tempo_sentado,
                    "q5_goals_progress": p5_progresso_metas,
                    "q6_energy_level": p6_energia,
                    "q7_mood": p7_humor,
                    "q8_persistent_emotional_distress": p8_distress
                },
                "free_text_notes": (
                    f"Sono (telas): {p1_horario_telas} | Qualidade: {p2_qualidade_sono} | "
                    f"Atividade: {p3_exercicio_hoje} | Sedentarismo: {p4_tempo_sentado} | "
                    f"Metas: {p5_progresso_metas}"
                )
            }
        }
    }

    os.makedirs(pasta_saida, exist_ok=True)
    arquivo_data = os.path.join(pasta_saida, f"checkin_contract_1a_{data_str}.json")
    with open(arquivo_data, "w", encoding="utf-8") as f:
        json.dump(contract_1a, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Etapa #2 concluída! Check-in salvo em: '{arquivo_data}'\n")
    return contract_1a


# ==============================================================================
# TOOLS DE CONTROLE DE ACESSO (PoLP — PRINCÍPIO DO MENOR PRIVILÉGIO)
# ==============================================================================

class BasePerfilReadWriteTool:
    """Tool de Leitura/Escrita na Base de Perfil (Exclusiva do Agente Chat)."""
    def __init__(self, caminho_perfil: str = "/content/base_perfil_usuario.json"):
        self.caminho_perfil = caminho_perfil
        self._garantir_perfil_inicial()

    def _garantir_perfil_inicial(self):
        if not os.path.exists(self.caminho_perfil):
            perfil_padrao = {
                "user_id": "usr_padrao_01",
                "profile": {
                    "name": "Usuário",
                    "preferences": {
                        "notification_window": "19:00-22:00",
                        "communication_tone": "empatico",
                        "do_not_disturb_weekends": True
                    },
                    "accessibility_or_work_needs": {
                        "needs_color_screen": False,
                        "needs_phone_reachable_for_care_or_work": True,
                        "bedtime_target": "22:30"
                    }
                },
                "goals": [
                    {
                        "goal_id": "goal_sono_01",
                        "description": "Reduzir o uso recreativo de telas após as 21h00 para melhorar a higiene do sono",
                        "target_frequency": "diario"
                    },
                    {
                        "goal_id": "goal_atv_02",
                        "description": "Realizar ao menos 20 minutos de caminhada ou alongamento ativo nos dias de trabalho",
                        "target_frequency": "diario"
                    }
                ],
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            os.makedirs(os.path.dirname(self.caminho_perfil) or ".", exist_ok=True)
            with open(self.caminho_perfil, "w", encoding="utf-8") as f:
                json.dump(perfil_padrao, f, indent=2, ensure_ascii=False)

    def ler_perfil(self) -> Dict[str, Any]:
        with open(self.caminho_perfil, "r", encoding="utf-8") as f:
            return json.load(f)

    def sincronizar_identidade_usuario(self, user_id: str, nome: str) -> Dict[str, Any]:
        dados = self.ler_perfil()
        alterado = False
        if user_id and dados.get("user_id") != user_id:
            dados["user_id"] = user_id
            alterado = True
        if nome and dados.get("profile", {}).get("name") != nome:
            dados["profile"]["name"] = nome
            alterado = True
        if alterado:
            dados["updated_at"] = datetime.now(timezone.utc).isoformat()
            with open(self.caminho_perfil, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
        return dados


class ReadOnlyDataAccessTool:
    """Tool Somente Leitura de Perfil, Dados de Uso e Modelo Calibrado (Exclusiva do Analista)."""
    def __init__(
        self,
        caminho_perfil: str = "/content/base_perfil_usuario.json",
        pasta_telemetria: str = "/content/historico_telemetria",
        pasta_checkins: str = "/content/historico_checkins",
        pasta_contratos_chat: str = "/content/contratos_chat",
        caminho_modelo_calibrado: str = "/content/fluia_analyst_calibrated_model.json",
        caminho_taxonomia_apps: str = "/content/fluia_app_taxonomy_lookup.json"
    ):
        self.caminho_perfil = caminho_perfil
        self.pasta_telemetria = pasta_telemetria
        self.pasta_checkins = pasta_checkins
        self.pasta_contratos_chat = pasta_contratos_chat
        self.caminho_modelo_calibrado = caminho_modelo_calibrado
        self.caminho_taxonomia_apps = caminho_taxonomia_apps

    def ler_perfil_somente_leitura(self) -> Dict[str, Any]:
        with open(self.caminho_perfil, "r", encoding="utf-8") as f:
            return json.load(f)

    def ler_historico_telemetria(self, limite_dias: int = 7) -> List[Dict[str, Any]]:
        if not os.path.isdir(self.pasta_telemetria):
            return []
        arquivos = sorted(glob.glob(os.path.join(self.pasta_telemetria, "telemetria_*.json")))[-limite_dias:]
        return [json.load(open(arq, "r", encoding="utf-8")) for arq in arquivos]

    def ler_historico_checkins(self, limite_dias: int = 7) -> List[Dict[str, Any]]:
        if not os.path.isdir(self.pasta_checkins):
            return []
        arquivos = sorted(glob.glob(os.path.join(self.pasta_checkins, "checkin_contract_1a_*.json")))[-limite_dias:]
        return [json.load(open(arq, "r", encoding="utf-8")) for arq in arquivos]

    def ler_feedbacks_recentes(self, limite: int = 5) -> List[Dict[str, Any]]:
        if not os.path.isdir(self.pasta_contratos_chat):
            return []
        arquivos = sorted(glob.glob(os.path.join(self.pasta_contratos_chat, "feedback_contract_1b_*.json")))[-limite:]
        return [json.load(open(arq, "r", encoding="utf-8")) for arq in arquivos]

    def ler_artefatos_modelo_calibrado(self) -> Dict[str, Any]:
        for c in [self.caminho_modelo_calibrado, "fluia_analyst_calibrated_model.json"]:
            if os.path.exists(c):
                with open(c, "r", encoding="utf-8") as f:
                    return json.load(f)
        return {
            "selected_features": [
                "esm_hour", "hour_sin", "hour_cos", "esm_weekday", "esm_is_weekend",
                "is_late_night_sleep_risk", "screen_time_minutes", "unique_apps_today",
                "is_high_engagement_app", "is_work_or_study_app", "is_messaging_app",
                "is_high_daily_screen_load"
            ],
            "scaler_mean": [12.971806, -0.102509, -0.418077, 2.964186, 0.281179, 0.075438, 145.225129, 36.735331, 0.290577, 0.122936, 0.18161, 0.290069],
            "scaler_scale": [4.876891, 0.671817, 0.602767, 1.981496, 0.449574, 0.264097, 148.10787, 25.718915, 0.454028, 0.328364, 0.385523, 0.453794],
            "coefficients": [-0.061082, -0.216062, 0.194978, -0.069805, 0.061103, 0.097291, -0.303965, -0.361559, 0.182565, -0.183322, 0.151099, 0.039149],
            "intercept": -1.091719,
            "platt_calibration": {"a": -0.833029, "b": 0.175704},
            "decision_threshold": 0.30,
            "real_population_baselines": {"screen_time_minutes_p50": 109.21}
        }

    def ler_taxonomia_apps(self) -> Dict[str, str]:
        for c in [self.caminho_taxonomia_apps, "fluia_app_taxonomy_lookup.json"]:
            if os.path.exists(c):
                with open(c, "r", encoding="utf-8") as f:
                    return json.load(f)
        return {}


class KnowledgeBaseRAGReadOnlyTool:
    """Tool de Busca RAG Somente Leitura (Chunks 44–87) — Exclusiva do Agente Ação."""
    _CHUNKS = {
        "45": {
            "chunk_id": "45",
            "category": "Uso automático",
            "title": "Quebra de Uso Automático e Pausas Ativas",
            "clinical_guideline": "Ativar escala de cinza no descanso ou, se precisar de tela colorida, usar temporizador de 20 min com pausa ativa de alongamento/caminhada leve."
        },
        "74": {
            "chunk_id": "74",
            "category": "Notificações",
            "title": "Gestão Seletiva de Interrupções",
            "clinical_guideline": "Silenciar notificações promocionais e de navegadores, mantendo apenas chamadas e mensagens essenciais de trabalho/cuidado."
        },
        "83": {
            "chunk_id": "83",
            "category": "Uso noturno",
            "title": "Higiene do Sono e Transição Noturna",
            "clinical_guideline": "Desacelerar o uso de telas 45 minutos antes do horário alvo de sono, silenciando apenas alertas recreativos sem desligar chamadas críticas."
        },
        "87": {
            "chunk_id": "87",
            "category": "Segurança",
            "title": "Acolhimento Empático e Encaminhamento Profissional",
            "clinical_guideline": "Acolher sem julgamento ou diagnóstico médico, orientando busca por profissional de saúde na UBS ou CAPS e apoio gratuito 24h no CVV (telefone 188)."
        }
    }

    def buscar_trecho(self, target_category: str) -> Dict[str, Any]:
        if target_category == "Segurança":
            return dict(self._CHUNKS["87"])
        for c in self._CHUNKS.values():
            if c["category"].lower() == target_category.lower():
                return dict(c)
        return dict(self._CHUNKS["45"])


# ==============================================================================
# ETAPA #3 — AGENTE CHAT (CONSOLIDAÇÃO + DIÁLOGO EMPÁTICO COM LLM LOCAL)
# ==============================================================================

class AgenteChatFluIA:
    """
    ETAPA #3 — AGENTE CHAT (Interface Conversacional com LLM Local Ollama/Qwen):
      • Lê exclusivamente JSONs processados (#1 e #2) e sincroniza nome dinâmico na Base de Perfil
      • Apresenta ao usuário apenas mensagens JÁ VALIDADAS pelo Juiz (Contrato 4)
      • Utiliza o LLM local (Ollama/Qwen) apenas para conduzir uma resposta empática
        de acolhimento pós-feedback, sem inventar recomendações clínicas nem violar PoLP
      • Registra o feedback estruturado (Contrato 1B)
    """
    def __init__(
        self,
        pasta_telemetria: str = "/content/historico_telemetria",
        pasta_checkins: str = "/content/historico_checkins",
        pasta_contratos_chat: str = "/content/contratos_chat",
        caminho_perfil: str = "/content/base_perfil_usuario.json",
        llm_client: Optional[OllamaLocalLLMClient] = None
    ):
        self.pasta_telemetria = pasta_telemetria
        self.pasta_checkins = pasta_checkins
        self.pasta_contratos_chat = pasta_contratos_chat
        self.perfil_tool = BasePerfilReadWriteTool(caminho_perfil)
        self.llm_client = llm_client or OllamaLocalLLMClient(model_name="qwen2.5:7b")
        os.makedirs(self.pasta_contratos_chat, exist_ok=True)

    def _validar_nao_eh_log_bruto(self, caminho: str):
        if not caminho.endswith(".json"):
            raise PermissionError(f"[VIOLAÇÃO PoLP] Agente Chat não pode ler log bruto: {caminho}")

    def ler_e_consolidar_entradas(self, data_referencia: Optional[str] = None) -> Dict[str, Any]:
        arqs_chk = sorted(glob.glob(os.path.join(self.pasta_checkins, "checkin_contract_1a_*.json")))
        if not arqs_chk:
            raise FileNotFoundError("Nenhum check-in da Etapa #2 encontrado.")
        arq_chk = os.path.join(self.pasta_checkins, f"checkin_contract_1a_{data_referencia}.json") if data_referencia else arqs_chk[-1]
        if not os.path.exists(arq_chk):
            arq_chk = arqs_chk[-1]
        self._validar_nao_eh_log_bruto(arq_chk)

        with open(arq_chk, "r", encoding="utf-8") as f:
            dados_checkin = json.load(f)

        user_id_dinamico = dados_checkin.get("user_id", "usr_padrao_01")
        nome_dinamico = dados_checkin.get("user_data", {}).get("profile", {}).get("name", "Usuário")
        perfil_base = self.perfil_tool.sincronizar_identidade_usuario(user_id=user_id_dinamico, nome=nome_dinamico)

        data_ref = dados_checkin.get("reference_date", datetime.now().strftime("%Y-%m-%d"))
        arq_tel = os.path.join(self.pasta_telemetria, f"telemetria_{data_ref}.json")
        if not os.path.exists(arq_tel):
            arqs_tel = sorted(glob.glob(os.path.join(self.pasta_telemetria, "telemetria_*.json")))
            arq_tel = arqs_tel[-1] if arqs_tel else None

        dados_tel = {}
        if arq_tel and os.path.exists(arq_tel):
            self._validar_nao_eh_log_bruto(arq_tel)
            with open(arq_tel, "r", encoding="utf-8") as f:
                dados_tel = json.load(f)

        consolidado = {
            "contract_version": "1.1",
            "event_type": "chat_consolidated_input",
            "reference_date": data_ref,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": perfil_base["user_id"],
            "user_data": {
                "profile": perfil_base["profile"],
                "goals": perfil_base["goals"],
                "checkin_payload": dados_checkin["user_data"]["checkin_payload"],
                "telemetry_summary_ref": dados_tel.get("summary", {})
            }
        }

        arq_saida = os.path.join(self.pasta_contratos_chat, f"chat_input_consolidado_{data_ref}.json")
        with open(arq_saida, "w", encoding="utf-8") as f:
            json.dump(consolidado, f, indent=2, ensure_ascii=False)

        print("=================================================================")
        print("   #3 AGENTE CHAT — ENTRADAS CONSOLIDADAS (ETAPAS #1 + #2)       ")
        print("=================================================================")
        print(f"• Usuário sincronizado: {perfil_base['profile']['name']} (ID: {perfil_base['user_id']}) | Data: {data_ref}")
        print(f"✅ Consolidado salvo em: '{arq_saida}'\n")
        return consolidado

    def _gerar_resposta_dialogo_llm(self, nome_usuario: str, mensagem_validada: str, feedback_usuario: str) -> str:
        """
        Usa o LLM local (Ollama/Qwen) apenas para encerrar o diálogo de forma empática
        após o usuário responder ao feedback, proibido de criar novas prescrições.
        """
        system_prompt = (
            "Você é o Agente Chat do FluIA, um assistente acolhedor de bem-estar digital. "
            "Responda em português do Brasil em no máximo 2 frases curtas. "
            "REGRAS ESTRITAS: apenas agradeça e valide o comentário do usuário com empatia. "
            "NUNCA crie novas recomendações médicas/comportamentais além da mensagem já validada."
        )
        user_prompt = (
            f"Nome do usuário: {nome_usuario}\n"
            f"Orientação validada entregue: {mensagem_validada}\n"
            f"Comentário/reação do usuário: {feedback_usuario}\n"
            "Escreva uma resposta empática curta de encerramento:"
        )
        resposta_llm = self.llm_client.gerar_resposta(system_prompt, user_prompt)
        if resposta_llm:
            return resposta_llm
        return f"Obrigado pelo retorno, {nome_usuario}! Registrei sua percepção para ajustarmos suas próximas metas com equilíbrio."

    def apresentar_sugestao_validada_e_coletar_feedback(
        self,
        contrato_4: Dict[str, Any],
        interativo: bool = True
    ) -> Optional[Dict[str, Any]]:
        perfil_atual = self.perfil_tool.ler_perfil()
        nome_usuario = perfil_atual.get("profile", {}).get("name", "Usuário")
        user_id_atual = perfil_atual.get("user_id", "usr_padrao_01")

        print("=================================================================")
        print("   #3 AGENTE CHAT — ENTREGA VALIDADA & DIÁLOGO (OLLAMA/QWEN)     ")
        print("=================================================================")

        if contrato_4.get("delivery_status") != "ready_to_deliver" or not contrato_4.get("validated_user_message"):
            print(f"🔇 Silêncio intencional respeitado para {nome_usuario}. Nenhuma sugestão enviada.")
            return None

        msg_validada = contrato_4["validated_user_message"]
        motor_redacao = contrato_4.get("generation_engine", "RAG_Deterministico")

        print(f"\n💬 Sugestão Validada pelo Juiz (Chunk #{contrato_4.get('source_chunk_id')} | Motor: {motor_redacao}):")
        print(f"\"{msg_validada}\"\n")
        print("-" * 65)

        if interativo:
            while True:
                u = input(f"{nome_usuario}, esta sugestão foi útil para você? (sim/não): ").strip().lower()
                if u in ("sim", "s", "não", "nao", "n"):
                    was_helpful = u in ("sim", "s")
                    break
            while True:
                r = input("Nota de 1 a 5 para esta orientação: ").strip()
                if r.isdigit() and 1 <= int(r) <= 5:
                    rating = int(r)
                    break
            comentario = input("Algum comentário ou dúvida rápida sobre essa sugestão? (opcional): ").strip()
        else:
            was_helpful = True
            rating = 5
            comentario = "Faz sentido para a minha rotina noturna hoje."

        # Resposta conversacional empática via LLM local (sem alterar a prescrição)
        resposta_chat = self._gerar_resposta_dialogo_llm(
            nome_usuario=nome_usuario,
            mensagem_validada=msg_validada,
            feedback_usuario=comentario or ("Útil" if was_helpful else "Não aplicável hoje")
        )
        print(f"\n🤖 Agente Chat: {resposta_chat}\n")

        data_ref = contrato_4.get("reference_date", datetime.now().strftime("%Y-%m-%d"))
        contract_1b = {
            "contract_version": "1.1",
            "event_type": "user_feedback",
            "reference_date": data_ref,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id_atual,
            "user_name": nome_usuario,
            "feedback_payload": {
                "intervention_id": contrato_4.get("intervention_id"),
                "was_helpful": was_helpful,
                "rating": rating,
                "user_comment": comentario,
                "chat_closing_reply": resposta_chat
            }
        }

        arq_fb = os.path.join(self.pasta_contratos_chat, f"feedback_contract_1b_{data_ref}.json")
        with open(arq_fb, "w", encoding="utf-8") as f:
            json.dump(contract_1b, f, indent=2, ensure_ascii=False)

        print(f"✅ Feedback registrado em: '{arq_fb}'\n")
        return contract_1b


# ==============================================================================
# ETAPA #4 — AGENTE ANALISTA V2 (SOMENTE LEITURA + ML CALIBRADO + JUIZ PoLP)
# ==============================================================================

class AgenteAnalistaFluIA:
    """
    ETAPA #4 — AGENTE ANALISTA & JUIZ:
      • Lê bases em modo Somente Leitura e calcula o Risco ML Calibrado (VIF <= 5)
      • Gera Contrato 2 para o Agente Ação
      • Audita a saída redigida pelo LLM do Agente Ação (Contrato 3 -> Contrato 4)
    """
    def __init__(
        self,
        caminho_perfil: str = "/content/base_perfil_usuario.json",
        pasta_telemetria: str = "/content/historico_telemetria",
        pasta_checkins: str = "/content/historico_checkins",
        pasta_contratos_chat: str = "/content/contratos_chat",
        pasta_saida_analista: str = "/content/contratos_analista"
    ):
        self.db_readonly = ReadOnlyDataAccessTool(
            caminho_perfil=caminho_perfil,
            pasta_telemetria=pasta_telemetria,
            pasta_checkins=pasta_checkins,
            pasta_contratos_chat=pasta_contratos_chat
        )
        self.pasta_saida_analista = pasta_saida_analista
        os.makedirs(self.pasta_saida_analista, exist_ok=True)
        self.modelo_calibrado = self.db_readonly.ler_artefatos_modelo_calibrado()
        self.taxonomia_apps = self.db_readonly.ler_taxonomia_apps()

    def _inferir_risco_ml_calibrado(self, data_ref: str, uso_lazer_min: float, uso_noturno_min: float, apps_ranked: List[Dict[str, Any]]) -> float:
        try:
            weekday = datetime.strptime(data_ref, "%Y-%m-%d").weekday()
        except ValueError:
            weekday = datetime.now().weekday()

        hora_eval = 22 if uso_noturno_min >= 30.0 else 15
        feature_map = {
            "esm_hour": float(hora_eval),
            "hour_sin": math.sin(2 * math.pi * hora_eval / 24.0),
            "hour_cos": math.cos(2 * math.pi * hora_eval / 24.0),
            "esm_weekday": float(weekday),
            "esm_is_weekend": 1.0 if weekday >= 5 else 0.0,
            "is_late_night_sleep_risk": 1.0 if hora_eval >= 22 else 0.0,
            "screen_time_minutes": float(uso_lazer_min),
            "unique_apps_today": float(len([a for a in apps_ranked if a.get("foreground_minutes", 0) > 0])),
            "is_high_engagement_app": 1.0,
            "is_work_or_study_app": 0.0,
            "is_messaging_app": 0.0,
            "is_high_daily_screen_load": 1.0 if uso_lazer_min > 180.0 else 0.0
        }
        feats = self.modelo_calibrado["selected_features"]
        means = self.modelo_calibrado["scaler_mean"]
        scales = self.modelo_calibrado["scaler_scale"]
        coefs = self.modelo_calibrado["coefficients"]
        logit = self.modelo_calibrado["intercept"]
        for i, fname in enumerate(feats):
            z = (feature_map.get(fname, 0.0) - means[i]) / (scales[i] if scales[i] != 0 else 1.0)
            logit += coefs[i] * z
        platt = self.modelo_calibrado.get("platt_calibration", {"a": -0.833029, "b": 0.175704})
        cal_logit = -(platt["a"] * logit + platt["b"])
        return round(1.0 / (1.0 + math.exp(-max(-20.0, min(20.0, cal_logit)))), 4)

    def gerar_contexto_enriquecido(self, data_referencia: Optional[str] = None) -> Dict[str, Any]:
        perfil = self.db_readonly.ler_perfil_somente_leitura()
        hist_tel = self.db_readonly.ler_historico_telemetria(limite_dias=7)
        hist_chk = self.db_readonly.ler_historico_checkins(limite_dias=7)

        if not hist_tel or not hist_chk:
            raise FileNotFoundError("Histórico de telemetria ou check-in ausente.")

        tel_atual = next((t for t in hist_tel if t.get("reference_date") == data_referencia), hist_tel[-1]) if data_referencia else hist_tel[-1]
        chk_atual = next((c for c in hist_chk if c.get("reference_date") == data_referencia), hist_chk[-1]) if data_referencia else hist_chk[-1]

        data_ref = chk_atual.get("reference_date", tel_atual.get("reference_date"))
        chk_payload = chk_atual["user_data"]["checkin_payload"]
        resumo_tel = tel_atual["summary"]

        distress = bool(chk_payload.get("persistent_emotional_distress", False))
        energia = int(chk_payload.get("energy_level", 3))
        uso_noturno = float(resumo_tel.get("night_window_19h_23h_minutes", 0.0))
        uso_lazer = float(resumo_tel.get("total_leisure_screen_minutes", 0.0))
        notificacoes = int(resumo_tel.get("total_notifications", 0))
        desbloqueios = int(resumo_tel.get("unlock_count", 0))
        risco_ml = self._inferir_risco_ml_calibrado(data_ref, uso_lazer, uso_noturno, tel_atual.get("apps_ranked", []))

        if distress:
            decisao = {
                "intervention_needed": True,
                "severity": "alta",
                "target_category": "Segurança",
                "rag_query_intent": "sofrimento emocional persistente encaminhamento UBS CAPS CVV 188",
                "diagnostic_reasoning": "Relato de sofrimento emocional persistente no check-in (Prioridade Máxima Chunk 87)."
            }
        elif uso_noturno >= 45.0 or (uso_noturno >= 30.0 and energia <= 2):
            decisao = {
                "intervention_needed": True,
                "severity": "alta" if uso_noturno >= 75.0 else "media",
                "target_category": "Uso noturno",
                "rag_query_intent": "higiene do sono uso noturno de telas antes de dormir transicao noturna",
                "diagnostic_reasoning": f"Uso recreativo noturno (19h–23h) de {uso_noturno} min (Risco ML calibrado: {risco_ml:.1%})."
            }
        elif notificacoes >= 80 or desbloqueios >= 55:
            decisao = {
                "intervention_needed": True,
                "severity": "media",
                "target_category": "Notificações",
                "rag_query_intent": "reducao de notificacoes interrupcoes foco digital",
                "diagnostic_reasoning": f"Sobrecarga de {notificacoes} notificações e {desbloqueios} desbloqueios (Risco ML: {risco_ml:.1%})."
            }
        elif (risco_ml >= 0.30 and uso_lazer >= 109.21 and energia <= 3) or (uso_lazer >= 120.0 and energia <= 3):
            decisao = {
                "intervention_needed": True,
                "severity": "media",
                "target_category": "Uso automático",
                "rag_query_intent": "uso automatico excessivo de tela pausas ativas caminhada",
                "diagnostic_reasoning": f"Risco ML calibrado de {risco_ml:.1%} com {uso_lazer} min recreativos e energia {energia}/5."
            }
        else:
            decisao = {
                "intervention_needed": False,
                "severity": "baixa",
                "target_category": "Nenhuma",
                "rag_query_intent": None,
                "diagnostic_reasoning": f"Uso equilibrado dentro das metas (Risco ML calibrado: {risco_ml:.1%}). Silêncio intencional."
            }

        decisao["metrics_snapshot"] = {
            "leisure_min": uso_lazer,
            "night_19h_23h_min": uso_noturno,
            "unlocks": desbloqueios,
            "notifications": notificacoes,
            "energy_level": energia,
            "calibrated_risk_probability": risco_ml
        }

        contrato_2 = {
            "contract_version": "1.1",
            "event_type": "analyst_enriched_context",
            "reference_date": data_ref,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": perfil["user_id"],
            "user_context": {
                "name": perfil["profile"]["name"],
                "communication_tone": perfil["profile"]["preferences"]["communication_tone"],
                "hard_constraints": perfil["profile"]["accessibility_or_work_needs"],
                "checkin_notes": chk_payload.get("free_text_notes", "")
            },
            "analysis_decision": decisao
        }

        arq_c2 = os.path.join(self.pasta_saida_analista, f"analyst_context_contract_2_{data_ref}.json")
        with open(arq_c2, "w", encoding="utf-8") as f:
            json.dump(contrato_2, f, indent=2, ensure_ascii=False)

        print("=================================================================")
        print("   #4 AGENTE ANALISTA — CONTEXTO ENRIQUECIDO (CONTRATO 2)        ")
        print("=================================================================")
        print(f"• Usuário: {perfil['profile']['name']} | Data: {data_ref} | Risco ML: {risco_ml:.1%}")
        print(f"• Intervir?: {decisao['intervention_needed']} | Categoria: {decisao['target_category']}")
        print(f"✅ Contrato 2 salvo em: '{arq_c2}'\n")
        return contrato_2

    def validar_proposta_como_juiz(self, contrato_2: Dict[str, Any], proposta_acao: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audita a proposta redigida pelo LLM do Agente Ação (Contrato 3) para garantir
        que o modelo local não alucinou violações de restrições nem ignorou o Chunk 87.
        """
        decisao = contrato_2["analysis_decision"]
        user_ctx = contrato_2["user_context"]
        restricoes = user_ctx["hard_constraints"]
        data_ref = contrato_2["reference_date"]

        if not decisao["intervention_needed"]:
            contrato_4 = {
                "contract_version": "1.1",
                "event_type": "validated_action_for_chat",
                "reference_date": data_ref,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": contrato_2["user_id"],
                "user_name": user_ctx["name"],
                "intervention_id": f"int_{data_ref.replace('-', '')}_silent",
                "judge_verdict": "approved_silence",
                "delivery_status": "silent_no_action",
                "validated_user_message": None,
                "audit_notes": ["Silêncio intencional validado."]
            }
        else:
            msg = (proposta_acao.get("proposed_message") or "").strip()
            chunk_id = proposta_acao.get("source_chunk_id")
            falhas = []

            if not msg or not chunk_id:
                falhas.append("Mensagem vazia ou sem chunk científico de origem.")
            if restricoes.get("needs_color_screen") and any(t in msg.lower() for t in ["escala de cinza", "preto e branco", "tela cinza"]):
                falhas.append("Violação: LLM sugeriu escala de cinza para usuário que requer tela colorida.")
            if restricoes.get("needs_phone_reachable_for_care_or_work") and any(t in msg.lower() for t in ["modo avião", "desligar o celular", "desligue o telefone"]):
                falhas.append("Violação: LLM sugeriu desligar/modo avião para usuário que precisa estar acessível.")
            if decisao["target_category"] == "Segurança":
                if str(chunk_id) != "87":
                    falhas.append("Violação: caso de Segurança exige obrigatoriamente Chunk 87.")
                if not any(k in msg.lower() for k in ["188", "cvv", "ubs", "caps"]):
                    falhas.append("Violação: proposta de Segurança gerada pelo LLM omitiu UBS/CAPS ou CVV 188.")

            aprovado = len(falhas) == 0
            contrato_4 = {
                "contract_version": "1.1",
                "event_type": "validated_action_for_chat",
                "reference_date": data_ref,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_id": contrato_2["user_id"],
                "user_name": user_ctx["name"],
                "intervention_id": proposta_acao.get("intervention_id", f"int_{data_ref.replace('-', '')}_01"),
                "judge_verdict": "approved" if aprovado else "rejected_for_revision",
                "delivery_status": "ready_to_deliver" if aprovado else "blocked_by_judge",
                "source_chunk_id": chunk_id,
                "generation_engine": proposta_acao.get("generation_engine", "Ollama_LLM"),
                "validated_user_message": msg if aprovado else None,
                "audit_notes": ["Proposta redigida por LLM aprovada pelo Juiz."] if aprovado else falhas
            }

        arq_c4 = os.path.join(self.pasta_saida_analista, f"validated_for_chat_contract_4_{data_ref}.json")
        with open(arq_c4, "w", encoding="utf-8") as f:
            json.dump(contrato_4, f, indent=2, ensure_ascii=False)

        print("=================================================================")
        print("   #4 AGENTE ANALISTA (JUIZ) — AUDITORIA DA SAÍDA LLM (CONTRATO 4)")
        print("=================================================================")
        print(f"• Veredito: {contrato_4['judge_verdict'].upper()} | Status: {contrato_4['delivery_status']}")
        print(f"• Notas:    {contrato_4['audit_notes']}")
        print(f"✅ Contrato 4 salvo em: '{arq_c4}'\n")
        return contrato_4


# ==============================================================================
# ETAPA #5 — AGENTE AÇÃO (RAG CHUNKS 44–87 + REDAÇÃO VIA OLLAMA/QWEN)
# ==============================================================================

class AgenteAcaoPrescricaoFluIA:
    """
    ETAPA #5 — AGENTE AÇÃO (Prescrição com LLM Local Ollama/Qwen):
      • Único agente autorizado a consultar a Tool RAG (Somente Leitura, Chunks 44–87)
      • Invoca o LLM local (Ollama/Qwen) para redigir uma proposta personalizada,
        empática e restrita estritamente ao trecho científico recuperado e às
        restrições rígidas do Contrato 2
      • Caso o Ollama esteja offline ou a saída falhe, aplica fallback determinístico seguro
      • Devolve o Contrato 3 exclusivamente ao Agente Analista (Juiz)
    """
    def __init__(self, llm_client: Optional[OllamaLocalLLMClient] = None):
        self.rag_tool = KnowledgeBaseRAGReadOnlyTool()
        self.llm_client = llm_client or OllamaLocalLLMClient(model_name="qwen2.5:7b")

    def _redigir_fallback_deterministico(
        self,
        nome: str,
        categoria: str,
        restricoes: Dict[str, Any],
        snap: Dict[str, Any]
    ) -> str:
        if categoria == "Segurança":
            return (
                f"{nome}, percebi pelo seu relato que os últimos dias têm sido emocionalmente pesados. "
                "Você não precisa passar por isso sozinho: considere buscar apoio com um profissional de saúde "
                "na UBS ou CAPS mais próximo, ou conversar gratuitamente com o CVV pelo telefone 188 (24h)."
            )
        if categoria == "Uso noturno":
            return (
                f"Olá, {nome}! Notei {snap.get('night_19h_23h_min', 0)} min de uso recreativo entre 19h e 23h. "
                f"Para proteger sua meta de dormir perto das {restricoes.get('bedtime_target', '22:30')} mantendo seu celular acessível para trabalho, "
                "experimente silenciar apenas alertas recreativos 45 minutos antes de deitar."
            )
        if categoria == "Notificações":
            return (
                f"Olá, {nome}! Seu aparelho recebeu {snap.get('notifications', 0)} notificações no período. "
                "Silenciar alertas promocionais de navegadores e apps não essenciais reduz interrupções sem perder chamadas importantes."
            )
        if restricoes.get("needs_color_screen"):
            return (
                f"Olá, {nome}! Mantendo a tela colorida para suas atividades, experimente definir um temporizador de 20 minutos "
                "seguido de uma pausa breve de alongamento ou caminhada leve."
            )
        return (
            f"Olá, {nome}! Para quebrar o ciclo de uso automático de telas, experimente ativar a escala de cinza "
            "no descanso e fazer uma caminhada leve de 15 a 20 minutos hoje."
        )

    def prescrever_proposta_para_analista(self, contrato_2: Dict[str, Any]) -> Dict[str, Any]:
        if contrato_2.get("event_type") != "analyst_enriched_context":
            raise PermissionError("[VIOLAÇÃO PoLP] Agente Ação aceita apenas Contrato 2 do Analista.")

        decisao = contrato_2["analysis_decision"]
        user_ctx = contrato_2["user_context"]
        data_ref = contrato_2["reference_date"]

        if not decisao["intervention_needed"]:
            return {
                "contract_version": "1.1",
                "event_type": "action_proposed_intervention",
                "recipient_agent": "AgenteAnalista",
                "reference_date": data_ref,
                "intervention_id": f"int_{data_ref.replace('-', '')}_silent",
                "source_chunk_id": None,
                "proposed_message": None
            }

        categoria = decisao["target_category"]
        trecho_rag = self.rag_tool.buscar_trecho(categoria)
        chunk_id = trecho_rag["chunk_id"]
        nome = user_ctx["name"]
        restricoes = user_ctx["hard_constraints"]
        snap = decisao.get("metrics_snapshot", {})

        # Monta prompt restrito ao chunk científico recuperado e às restrições rígidas
        system_prompt = (
            "Você é o Agente de Prescrição do FluIA. Redija UMA mensagem curta (máximo 3 frases), "
            "empática e prática em português do Brasil para o usuário, baseada EXCLUSIVAMENTE na diretriz "
            "científica fornecida.\n"
            "REGRAS INEGOCIÁVEIS:\n"
            "1. Nunca faça diagnóstico médico nem use tom culpabilizador.\n"
            "2. Se needs_color_screen=True, PROIBIDO sugerir escala de cinza ou tela preto e branco.\n"
            "3. Se needs_phone_reachable_for_care_or_work=True, PROIBIDO sugerir desligar o celular ou modo avião.\n"
            "4. Se a categoria for 'Segurança', mencione obrigatoriamente apoio profissional na UBS/CAPS e o CVV (telefone 188)."
        )

        user_prompt = (
            f"Nome do usuário: {nome}\n"
            f"Categoria diagnosticada: {categoria}\n"
            f"Chunk Científico #{chunk_id} ({trecho_rag['title']}): {trecho_rag['clinical_guideline']}\n"
            f"Métricas observadas: Lazer={snap.get('leisure_min')} min, Noturno(19h-23h)={snap.get('night_19h_23h_min')} min, "
            f"Notificações={snap.get('notifications')}, Energia={snap.get('energy_level')}/5\n"
            f"Restrições rígidas: needs_color_screen={restricoes.get('needs_color_screen')}, "
            f"needs_phone_reachable_for_care_or_work={restricoes.get('needs_phone_reachable_for_care_or_work')}, "
            f"bedtime_target={restricoes.get('bedtime_target')}\n"
            "Redija agora apenas o texto final da mensagem para o usuário:"
        )

        texto_llm = self.llm_client.gerar_resposta(system_prompt, user_prompt)
        if texto_llm:
            mensagem_final = texto_llm.strip('"').strip()
            motor_utilizado = f"Ollama_{self.llm_client.model_name}"
        else:
            mensagem_final = self._redigir_fallback_deterministico(nome, categoria, restricoes, snap)
            motor_utilizado = "Fallback_Deterministico_RAG"

        contrato_3 = {
            "contract_version": "1.1",
            "event_type": "action_proposed_intervention",
            "recipient_agent": "AgenteAnalista",
            "reference_date": data_ref,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": contrato_2["user_id"],
            "intervention_id": f"int_{data_ref.replace('-', '')}_01",
            "target_category": categoria,
            "source_chunk_id": chunk_id,
            "generation_engine": motor_utilizado,
            "proposed_message": mensagem_final
        }

        print("=================================================================")
        print("   #5 AGENTE AÇÃO — PRESCRIÇÃO GERADA (RAG + OLLAMA/QWEN)        ")
        print("=================================================================")
        print(f"• Motor de redação: {motor_utilizado}")
        print(f"• Chunk RAG usado:  #{chunk_id} — {trecho_rag['title']}")
        print("• Proposta devolvida em memória ao Juiz (#4 Agente Analista)\n")
        return contrato_3


# ==============================================================================
# ORQUESTRADOR PRINCIPAL (EXECUÇÃO COMPLETA DO MVP 01 COM LLM LOCAL)
# ==============================================================================

def executar_mvp_fluia_com_llm(
    modelo_ollama: str = "qwen2.5:7b",
    executar_checkin_interativo: bool = True
):
    print(f"\n🚀 INICIANDO MVP FluIA 01 (PoLP + RAG + LLM Local: {modelo_ollama})...\n")
    llm_local = OllamaLocalLLMClient(model_name=modelo_ollama)

    # ETAPA #1: Coleta e parse dos dumps ADB por data
    telemetrias = executar_etapa_1_telemetria()
    data_mais_recente = telemetrias[-1]["reference_date"]

    # ETAPA #2: Check-in interativo (nome dinâmico + 08 perguntas)
    if executar_checkin_interativo:
        executar_etapa_2_checkin_8_perguntas(data_referencia=data_mais_recente)
    else:
        os.makedirs("/content/historico_checkins", exist_ok=True)
        chk_demo = {
            "contract_version": "1.1",
            "event_type": "daily_checkin",
            "reference_date": data_mais_recente,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": "usr_participante_01",
            "user_data": {
                "profile": {
                    "name": "Participante",
                    "preferences": {"notification_window": "19:00-22:00", "communication_tone": "empatico"},
                    "accessibility_or_work_needs": {
                        "needs_color_screen": False,
                        "needs_phone_reachable_for_care_or_work": True,
                        "bedtime_target": "22:30"
                    }
                },
                "checkin_payload": {
                    "mood": "cansado",
                    "energy_level": 3,
                    "persistent_emotional_distress": False,
                    "free_text_notes": "Sono: Larguei o celular às 21h25 | Atividade: Sem caminhada hoje"
                }
            }
        }
        with open(f"/content/historico_checkins/checkin_contract_1a_{data_mais_recente}.json", "w", encoding="utf-8") as f:
            json.dump(chk_demo, f, indent=2, ensure_ascii=False)

    # ETAPA #3 (Parte A): Agente Chat consolida entradas e sincroniza nome na Base de Perfil
    chat = AgenteChatFluIA(llm_client=llm_local)
    chat.ler_e_consolidar_entradas(data_referencia=data_mais_recente)

    # ETAPA #4 (Parte A): Agente Analista lê bases (Somente Leitura) e calcula Risco ML
    analista = AgenteAnalistaFluIA()
    contrato_2 = analista.gerar_contexto_enriquecido(data_referencia=data_mais_recente)

    # ETAPA #5: Agente Ação consulta RAG (Chunks 44–87) e redige proposta via Ollama/Qwen
    acao = AgenteAcaoPrescricaoFluIA(llm_client=llm_local)
    contrato_3 = acao.prescrever_proposta_para_analista(contrato_2)

    # ETAPA #4 (Parte B): Agente Analista (Juiz) audita a saída do LLM antes de liberar ao Chat
    contrato_4 = analista.validar_proposta_como_juiz(contrato_2, contrato_3)

    # ETAPA #3 (Parte B): Agente Chat apresenta a proposta aprovada e conduz encerramento empático via LLM
    chat.apresentar_sugestao_validada_e_coletar_feedback(contrato_4, interativo=executar_checkin_interativo)

    print("🏁 CICLO MVP FluIA 01 (LLM LOCAL + PoLP) CONCLUÍDO COM SUCESSO!")


if __name__ == "__main__":
    executar_mvp_fluia_com_llm(modelo_ollama="qwen2.5:7b", executar_checkin_interativo=True)
