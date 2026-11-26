"""
Modelos de dados e contratos do Agente de Ação.
Utiliza apenas dataclasses padrão do Python para manter a didática e simplicidade.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


@dataclass
class DiagnosticoEntrada:
    """
    Representa o diagnóstico estruturado recebido do Agente Analista.
    """
    diagnostico_id: str
    diagnostico: str
    evento_detectado: Dict[str, Any] = field(default_factory=dict)
    objetivos_usuario: List[str] = field(default_factory=list)
    restricoes: List[str] = field(default_factory=list)
    historico_intervencoes: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, dados: Dict[str, Any]) -> "DiagnosticoEntrada":
        """
        Cria a instância tratando compatibilidade (ex: divergencias -> restricoes).
        """
        restricoes = dados.get("restricoes") or dados.get("divergencias") or []
        return cls(
            diagnostico_id=dados.get("diagnostico_id", "DESCONHECIDO"),
            diagnostico=dados.get("diagnostico", ""),
            evento_detectado=dados.get("evento_detectado", {}),
            objetivos_usuario=dados.get("objetivos_usuario", []),
            restricoes=restricoes,
            historico_intervencoes=dados.get("historico_intervencoes", [])
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChunkRecuperado:
    """
    Representa um chunk de conhecimento retornado pela busca do RAG.
    """
    id: str
    texto: str
    metadados: Dict[str, Any] = field(default_factory=dict)
    score_hibrido: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DefinicaoFerramenta:
    """
    Especificação de uma ferramenta disponível para ser enviada no prompt da LLM.
    """
    nome: str
    descricao: str
    parametros: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DecisaoAgente:
    """
    Decisão estruturada gerada pelo raciocínio da LLM (ReAct simplificado).
    """
    pensamento: str
    estrategia_selecionada: Optional[str] = None
    chunk_referencia: Optional[str] = None
    justificativa: str = ""
    ferramenta_solicitada: Optional[str] = None
    parametros_ferramenta: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, dados: Dict[str, Any]) -> "DecisaoAgente":
        return cls(
            pensamento=dados.get("pensamento", ""),
            estrategia_selecionada=dados.get("estrategia_selecionada"),
            chunk_referencia=dados.get("chunk_referencia"),
            justificativa=dados.get("justificativa", ""),
            ferramenta_solicitada=dados.get("ferramenta_solicitada"),
            parametros_ferramenta=dados.get("parametros_ferramenta", {})
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResultadoExecucao:
    """
    Resultado retornado após a execução da ferramenta em Python.
    """
    sucesso: bool
    resultado: Any = None
    erro: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RespostaFinal:
    """
    Contrato final de saída do Agente de Ação.
    Estados possíveis de status: 'executado', 'sem_acao', 'falha', 'aguardando_aprovacao'.
    """
    diagnostico_id: str
    status: str
    decisao: Dict[str, Any]
    acao: Optional[Dict[str, Any]] = None
    execucao: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
