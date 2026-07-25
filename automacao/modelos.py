# -*- coding: utf-8 -*-
"""Contratos de dados do coletor.

Os modelos públicos continuam sendo dicionários JSON. Os ``TypedDict`` tornam
o formato legível sem obrigar uma conversão ampla durante a migração.
"""
from dataclasses import asdict, dataclass, field
from typing import Generic, Literal, TypeVar, TypedDict

T = TypeVar("T")
StatusFonte = Literal[
    "live",
    "vazio_confirmado",
    "parcial",
    "degradado",
    "falhou",
    "nao_aplicavel",
]


@dataclass
class SourceResult(Generic[T]):
    """Resultado normalizado de uma fonte independente."""

    status: StatusFonte
    dados: T
    problemas: list[str] = field(default_factory=list)
    checked_at: str | None = None
    from_cache: bool = False
    truncado: bool = False
    quantidade_atual: int = 0
    last_live_at: str | None = None
    detalhes: dict = field(default_factory=dict)

    def para_status(self) -> dict:
        """Representação compacta e serializável para ``fontes_status``."""
        base = {
            "status": self.status,
            "checked_at": self.checked_at,
            "last_live_at": self.last_live_at,
            "idade_segundos": None,
            "quantidade_atual": self.quantidade_atual,
            "from_cache": self.from_cache,
            "truncado": self.truncado,
            "problemas": list(self.problemas),
        }
        base.update(self.detalhes)
        return base

    def para_dict(self) -> dict:
        return asdict(self)


class Prazo(TypedDict, total=False):
    rotulo: str
    quando: str
    trecho: str
    tipo: str
    hora_certa: bool
    escopo: dict | None
    confianca: str
    frase: str


class Item(TypedDict, total=False):
    cmid: str
    label: str
    type: str
    url: str
    status: str | None
    conta_nota: bool
    aberto: bool | None
    prazo: str | None
    prazo_fonte: str | None


class Secao(TypedDict, total=False):
    id: str
    title: str
    parent: str | None
    locked: str | None
    fase: str
    items: list[Item]


class Curso(TypedDict, total=False):
    id: str
    code: str
    name: str
    modelo: str
    sections: list[Secao]
    avisos: list[dict]
    cronograma: dict | None


class Acao(TypedDict, total=False):
    curso: str
    secao: str
    o_que: str
    prazo: str | None
    prioridade_ate: str | None
    urgencia: str
