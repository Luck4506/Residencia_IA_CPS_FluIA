from consulta import ConsultorRAG
import ollama

MODELO_LLM = "qwen2.5:3b"

TOP_K = 5


SYSTEM_PROMPT = """
Você é um agente de ação especializado em bem-estar digital.

Sua responsabilidade é analisar o diagnóstico ou relato apresentado
pelo usuário e propor estratégias práticas para melhorar seus hábitos
digitais.

Você receberá:
- O diagnóstico apresentado pelo usuário.
- Uma coleção de chunks sobre bem-estar digital, indicando diagnósticos e estratégias de intervenção.

REGRAS IMPORTANTES:

1. Utilize os chunks fornecidos como fundamentação principal
   das suas recomendações.

2. Não invente evidências científicas, estudos, referências
   ou informações que não estejam presentes no contexto.

3. Analise as estratégias, evidências, adequações e restrições
   descritas nos chunks antes de recomendar uma ação.

4. Escolha estratégias que sejam compatíveis com a situação
   apresentada pelo usuário.

5. Não precisa utilizar todos os chunks. Selecione aqueles
   que realmente contribuem para a recomendação.

6. Se os conhecimentos recuperados forem insuficientes,
   informe essa limitação. Não invente uma solução.

7. Não trate o relato como um diagnóstico médico ou psicológico.
   Não atribua transtornos ou condições clínicas ao usuário.

8. Evite recomendações genéricas. Priorize ações concretas,
   simples e possíveis de executar.

FORMATO DA RESPOSTA:

## Análise da situação
Explique brevemente o problema identificado no relato.

## Estratégia recomendada
Apresente a estratégia mais adequada e explique por que
ela foi escolhida com base nos conhecimentos recuperados.

## Plano de ação
Apresente passos práticos que o usuário pode executar.

## Fundamentação
Indique os IDs dos chunks utilizados e explique brevemente
como eles fundamentam a recomendação.

## Cuidados e limitações
Apresente restrições ou cuidados relevantes identificados
nos documentos.
"""

class AgenteAcao:

    def __init__(self):

        print("\nInicializando Agente de Ação...")

        # Inicializa o mecanismo de recuperação
        self.consultor = ConsultorRAG()

        # Verifica a disponibilidade do modelo
        ollama.show(MODELO_LLM)

        print(f"Modelo LLM: {MODELO_LLM}")
        print("Agente inicializado com sucesso!\n")

    def recuperar_conhecimento(self, diagnostico):

        resultados = self.consultor.buscar(
            diagnostico,
            top_k=TOP_K
        )

        return resultados

    def exibir_chunks(self, chunks):

        print("\n" + "=" * 60)
        print("CHUNKS RECUPERADOS")
        print("=" * 60)

        if not chunks:
            print("Nenhum chunk encontrado.")
            return

        for i, chunk in enumerate(chunks, start=1):

            metadados = chunk["metadados"]

            situacao = metadados.get(
                "situação", "Não informado"
            )

            estrategia = metadados.get(
                "estratégia", "Não informado"
            )

            print(f"\n[{i}] {chunk['id']}")

            print(f"Situação: {situacao}")

            print(f"Estratégia: {estrategia}")

            print("-" * 60)


    def gerar_recomendacao(self, diagnostico, chunks):

        if not chunks:
            return (
                "Não foram encontrados conhecimentos "
                "para fundamentar uma recomendação."
            )

        # Monta o contexto completo para o LLM
        contexto = ""

        for chunk in chunks:

            contexto += (
                f"\n\n### {chunk['id']}\n"
                f"{chunk['texto']}\n"
            )

        # Monta a mensagem do usuário
        mensagem_usuario = f"""
        DIAGNÓSTICO DO USUÁRIO: {diagnostico}

        CONHECIMENTOS RECUPERADOS: {contexto}

        Com base no diagnóstico e nos conhecimentos fornecidos,
        elabore uma recomendação prática e fundamentada.
        """

        print("\nGerando recomendação com o Qwen...\n")

        resposta = ollama.chat(
            model=MODELO_LLM,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": mensagem_usuario
                }
            ],
            options={
                "temperature": 0.3
            }
        )

        return resposta.message.content

    def executar(self, diagnostico):

        # 1. Recuperação
        chunks = self.recuperar_conhecimento(diagnostico)

        # 2. Exibição dos resultados
        self.exibir_chunks(chunks)

        # 3. Geração da recomendação
        recomendacao = self.gerar_recomendacao(
            diagnostico,
            chunks
        )

        # 4. Exibição da resposta
        print("\n" + "=" * 60)
        print("RECOMENDAÇÃO DO AGENTE DE AÇÃO")
        print("=" * 60)

        print(recomendacao)

        print("\n" + "=" * 60)

        return recomendacao

def main():

    agente = AgenteAcao()

    print("AGENTE DE BEM-ESTAR DIGITAL")
    print("Digite 'sair' para encerrar.\n")

    while True:

        diagnostico = input(
            "\nDescreva sua situação: "
        ).strip()

        if diagnostico.lower() in ["sair", "exit", "quit"]:
            break

        if not diagnostico:
            print("Por favor, informe uma situação.")
            continue

        try:

            agente.executar(diagnostico)

        except Exception as erro:

            print(f"\nErro durante a execução: {erro}")

    print("\nAgente encerrado.")


if __name__ == "__main__":
    main()
