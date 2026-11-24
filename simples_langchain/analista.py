"""Contrato e ponto de entrada dos alertas no Agente Analista."""

from datetime import datetime
from typing import Annotated

from pydantic import (
    AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field, FiniteFloat,
    StringConstraints, ValidationError, ValidationInfo, field_validator,
)
from pydantic_core import PydanticCustomError


def ler_horario(valor: object) -> datetime:
    if isinstance(valor, str):
        try:
            return datetime.fromisoformat(valor)
        except ValueError:
            pass
    raise PydanticCustomError('horario_invalido', 'Informe um horário ISO 8601 com fuso.')


Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Horario = Annotated[AwareDatetime, BeforeValidator(ler_horario)]


class PeriodoUso(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    inicio: Horario
    fim: Horario

    @field_validator('fim')
    @classmethod
    def validar_ordem(cls, fim: datetime, info: ValidationInfo) -> datetime:
        inicio = info.data.get('inicio')
        if inicio is not None and fim <= inicio:
            raise PydanticCustomError('periodo_invalido', 'O fim deve ser posterior ao início.')
        return fim


class AlertaUso(BaseModel):
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
    """Prepara o contexto que a etapa de consulta ao perfil e às metas receberá."""
    return {'etapa': 'consulta_contexto', **alerta.model_dump(mode='json')}


def receber_alerta(dados: object) -> dict:
    """Valida o objeto enviado pelo script antes de iniciar a análise."""
    try:
        alerta = AlertaUso.model_validate(dados)
    except ValidationError as erro:
        return {
            'status': 'rejeitado',
            'erros': [
                {
                    'campo': '.'.join(map(str, item['loc'])) or 'alerta',
                    'codigo': item['type'],
                    'mensagem': MENSAGENS_VALIDACAO.get(item['type'], item['msg']),
                }
                for item in erro.errors(include_url=False, include_input=False, include_context=False)
            ],
        }

    return {'status': 'analise_iniciada', 'analise': iniciar_analise(alerta)}
