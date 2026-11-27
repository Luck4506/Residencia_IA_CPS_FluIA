from agente.agente import AgenteAcao

agente = AgenteAcao(top_k=3)

# Exemplo de diagnóstico direto em dicionário
meu_diagnostico = {
      "diagnostico_id": "TESTE",
            "diagnostico": "O usuário costuma utilizar o smartphone enquanto está deitado na cama, próximo ao horário habitual de dormir. Ele relata dificuldade em encerrar a utilização e gostaria de evitar que o aparelho permaneça disponível durante sua rotina de descanso.",
            "evento_detectado": {
                "aplicativos": [
                    "Instagram",
                    "YouTube"
                ],
                "ocorrencia": "Foram registrados aproximadamente 50 minutos de utilização antes do horário habitual de dormir.",
                "frequencia": "O comportamento ocorreu em 6 dos últimos 7 dias."
            },
            "objetivos_usuario": [
                "Reduzir a utilização do smartphone antes de dormir.",
                "Manter uma rotina noturna com menos distrações.",
                "Evitar verificações frequentes do dispositivo na cama."
            ],
            "divergencias": [
                "A utilização do smartphone ocorre durante o período reservado ao descanso.",
                "O usuário relata dificuldade em encerrar o uso antes de dormir."
            ],

}

resposta = agente.executar(meu_diagnostico)

# Exibe o JSON final
import json
print(json.dumps(resposta.to_dict(), indent=2, ensure_ascii=False))