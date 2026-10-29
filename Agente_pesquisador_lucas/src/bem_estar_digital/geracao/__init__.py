"""Geração local com Ollama; documentos são dados, não instruções."""
import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SEM_EVIDENCIA = "Não encontrei evidências suficientes na base para responder."

RAIZ = Path(__file__).resolve().parents[3]

class Ollama:
    def __init__(self, servidor="http://localhost:11434"):
        self.servidor = servidor.rstrip("/")
        self.chamadas = 0

    def post(self, rota, dados):
        requisicao = Request(
            self.servidor + rota,
            data=json.dumps(dados).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(requisicao, timeout=300) as resposta:
                resultado = json.load(resposta)
        except HTTPError as erro:
            if erro.code == 404:
                raise RuntimeError(
                    f"Modelo ou rota indisponível. Verifique o Ollama e execute: "
                    f"ollama pull {dados['model']}"
                ) from erro
            raise RuntimeError(f"O Ollama retornou um erro HTTP {erro.code}.") from erro
        except (URLError, TimeoutError, ConnectionError) as erro:
            raise RuntimeError(
                f"Não foi possível consultar o Ollama em {self.servidor}. "
                "Abra o aplicativo Ollama ou execute 'ollama serve' e tente novamente."
            ) from erro
        except (ValueError, UnicodeError) as erro:
            raise RuntimeError("O Ollama retornou uma resposta JSON inválida.") from erro
        if not isinstance(resultado, dict) or resultado.get("error"):
            raise RuntimeError("O Ollama não conseguiu processar a solicitação.")
        return resultado

    def responder(self, mensagens, modelo, esquema=None):
        dados = {
            "model": modelo,
            "messages": mensagens,
            "stream": False,
            "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 1200},
        }
        if esquema is not None:
            dados["format"] = esquema
        self.chamadas += 1
        resultado = self.post("/api/chat", dados)
        texto = resultado.get("message", {}).get("content", "").strip()
        if not texto or resultado.get("done_reason") == "length":
            raise RuntimeError("O Llama retornou uma resposta vazia ou incompleta. Tente uma pergunta menor.")
        return texto


def esquema_resposta(referencias):
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "sem_evidencia": {"type": "boolean"},
            "afirmacoes": {"type": "array", "maxItems": 4, "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "texto": {"type": "string", "minLength": 1},
                    "fontes": {"type": "array", "minItems": 1, "uniqueItems": True,
                               "items": {"type": "string", "enum": referencias}},
                }, "required": ["texto", "fontes"],
            }},
        }, "required": ["sem_evidencia", "afirmacoes"],
    }


def formatar_resposta(texto, referencias):
    dados = json.loads(texto)
    if not isinstance(dados, dict) or type(dados.get("sem_evidencia")) is not bool:
        raise ValueError("Formato da resposta inválido.")
    itens = dados.get("afirmacoes")
    if not isinstance(itens, list) or len(itens) > 4:
        raise ValueError("Lista de afirmações inválida.")
    if dados["sem_evidencia"] and not itens:
        return SEM_EVIDENCIA
    if dados["sem_evidencia"] or not itens:
        raise ValueError("A resposta contradiz a indicação de evidência.")
    linhas = []
    for item in itens:
        if not isinstance(item, dict):
            raise ValueError("Afirmação inválida.")
        fontes, frase = item.get("fontes"), item.get("texto")
        if (not isinstance(fontes, list) or not fontes
                or any(not isinstance(f, str) or f not in referencias for f in fontes)
                or not isinstance(frase, str) or not frase.strip()):
            raise ValueError("Afirmação sem referências válidas.")
        if not set(re.findall(r"\[(T\d+)\]", frase)).issubset(set(fontes)):
            raise ValueError("O texto contém referências não declaradas.")
        frase = re.sub(r"\[T\d+\]", "", frase).strip()
        if not frase:
            raise ValueError("Afirmação sem texto.")
        citacoes = " ".join(f"[{f}]" for f in dict.fromkeys(fontes))
        linhas.append(f"- {frase} {citacoes}")
    return "\n".join(linhas)


def responder(pergunta, trechos, cliente, modelo="llama3.2:3b"):
    if not trechos:
        return SEM_EVIDENCIA
    prompt = (RAIZ / "prompts/resposta.txt").read_text(encoding="utf-8")
    contexto = [{**{k: c[k] for k in ("texto", "titulo", "arquivo", "pagina", "secao") if k in c},
                 "referencia": f"T{i}"} for i, c in enumerate(trechos, 1)]
    referencias = [c["referencia"] for c in contexto]
    esquema = esquema_resposta(referencias)
    mensagens = [
        {"role": "system", "content": prompt + "\nEsquema JSON obrigatório:\n" + json.dumps(esquema)},
        {"role": "user", "content": json.dumps({"pergunta": pergunta, "trechos": contexto}, ensure_ascii=False)},
    ]
    for tentativa in range(2):
        resposta = cliente.responder(mensagens, modelo, esquema=esquema)
        try:
            return formatar_resposta(resposta, referencias)
        except ValueError as erro:
            if tentativa:
                raise ValueError("O modelo não conseguiu organizar a resposta com fontes após duas tentativas. "
                                 "Use o comando 'recuperar' para consultar as evidências.") from erro
            mensagens += [{"role": "assistant", "content": resposta},
                          {"role": "user", "content": "Corrija o formato JSON e as referências, usando somente "
                           + ", ".join(referencias) + ". Se faltar evidência, use sem_evidencia=true e afirmacoes=[]."}]

