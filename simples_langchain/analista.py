"""Contrato e ponto de entrada dos alertas no Agente Analista."""

from datetime import datetime
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    FiniteFloat,
    StringConstraints,
    ValidationError,
    ValidationInfo,
    field_validator,
)
from pydantic_core import PydanticCustomError


def ler_horario(valor: object) -> datetime:
    mensagem = 'Informe um horário ISO 8601 com fuso.'

    if not isinstance(valor, str):
        raise PydanticCustomError('horario_invalido', mensagem)

    try:
        return datetime.fromisoformat(valor)
    except ValueError as erro:
        raise PydanticCustomError('horario_invalido', mensagem) from erro


Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
# O AwareDatetime exige o fuso depois que ler_horario converte o texto.
Horario = Annotated[AwareDatetime, BeforeValidator(ler_horario)]


class PeriodoUso(BaseModel):
    """Intervalo efetivamente medido pelo script que gerou o alerta."""

    model_config = ConfigDict(extra='forbid', strict=True)

    inicio: Horario
    fim: Horario

    @field_validator('fim')
    @classmethod
    def validar_ordem(cls, fim: datetime, info: ValidationInfo) -> datetime:
        # Se o início falhou na validação, o Pydantic já vai apontar o erro nele.
        inicio = info.data.get('inicio')

        if inicio is not None and fim <= inicio:
            raise PydanticCustomError(
                'periodo_invalido',
                'O fim deve ser posterior ao início.',
            )

        return fim


class AlertaUso(BaseModel):
    """Dados que o Analista espera receber dos scripts de monitoramento."""

    model_config = ConfigDict(extra='forbid', strict=True)

    usuario_id: Texto
    script_origem: Texto
    motivo: Texto
    horario_alerta: Horario
    periodo_uso: PeriodoUso
    indicadores: dict[Texto, FiniteFloat] = Field(default_factory=dict)


MENSAGENS_VALIDACAO = {
    'missing': 'Campo obrigatório ausente.',
    'extra_forbidden': 'Campo fora do contrato.',
    'string_type': 'Informe um texto.',
    'string_too_short': 'Informe um texto não vazio.',
    'timezone_aware': 'Informe o fuso horário com Z ou um deslocamento como -03:00.',
    'model_type': 'Informe um objeto.',
    'dict_type': 'Informe um objeto de indicadores.',
    'float_type': 'Informe um valor numérico.',
    'finite_number': 'Informe um valor numérico finito.',
}


def iniciar_analise(alerta: AlertaUso) -> dict:
    """Prepara os dados para a consulta ao perfil e às metas do usuário."""
    dados_do_alerta = alerta.model_dump(mode='json')

    return {
        'etapa': 'consulta_contexto',
        **dados_do_alerta,
    }


def receber_alerta(dados: object) -> dict:
    """Valida o objeto enviado pelo script antes de iniciar a análise."""
    try:
        alerta = AlertaUso.model_validate(dados)
    except ValidationError as erro:
        # O script recebe o nome do campo e o motivo, sem os valores recusados.
        erros_de_validacao = erro.errors(
            include_url=False,
            include_input=False,
            include_context=False,
        )
        erros = []

        for item in erros_de_validacao:
            campo = '.'.join(map(str, item['loc'])) or 'alerta'
            codigo = item['type']
            mensagem = MENSAGENS_VALIDACAO.get(codigo, item['msg'])

            erros.append({
                'campo': campo,
                'codigo': codigo,
                'mensagem': mensagem,
            })

        return {'status': 'rejeitado', 'erros': erros}

    analise = iniciar_analise(alerta)

    return {'status': 'analise_iniciada', 'analise': analise}
