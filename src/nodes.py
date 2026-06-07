"""
Nós da Árvore Sintática Abstrata (AST) da linguagem Homi.

Contém todos os dataclasses que representam os nós da AST
e os type aliases para os union types (TriggerNode, ConditionNode, ActionNode).

Cada nó é uma dataclass imutável por construção (exceto listas, via field).
"""

from dataclasses import dataclass, field


# ══════════════════════════════════════════════════════════════════════
# Nós de topo
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ProgramNode:
    """Raiz da AST. Contém uma lista de automações."""
    automacoes: list['AutomacaoNode'] = field(default_factory=list)


@dataclass
class AutomacaoNode:
    """Representa uma automação completa."""
    nome: str
    triggers: list = field(default_factory=list)
    conditions: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    line: int = 0


# ══════════════════════════════════════════════════════════════════════
# Triggers
# ══════════════════════════════════════════════════════════════════════

@dataclass
class TriggerEstadoNode:
    """Trigger: entity muda para estado."""
    entity_id: str
    estado: str
    line: int = 0


@dataclass
class TriggerHoraNode:
    """Trigger: hora = HH:MM."""
    clock_time: str
    line: int = 0


@dataclass
class TriggerMovimentoNode:
    """Trigger: entity movimento."""
    entity_id: str
    line: int = 0


@dataclass
class TriggerBateriaNode:
    """Trigger: entity bateria abaixo/acima N%. O valor é o lexema (ex: '20%', '30')."""
    entity_id: str
    operador: str
    valor: str
    line: int = 0


# ══════════════════════════════════════════════════════════════════════
# Conditions
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ConditionEstadoNode:
    """Condição: entity esta estado."""
    entity_id: str
    estado: str
    line: int = 0


@dataclass
class ConditionHoraNode:
    """Condição: hora abaixo/acima HH:MM."""
    operador: str
    clock_time: str
    line: int = 0


# ══════════════════════════════════════════════════════════════════════
# Actions
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ActionLigarNode:
    """Ação: ligar entity_id."""
    entity_id: str
    line: int = 0


@dataclass
class ActionDesligarNode:
    """Ação: desligar entity_id."""
    entity_id: str
    line: int = 0


@dataclass
class ActionEsperarNode:
    """Ação: esperar duration (ex: '45s', '5min', '2h')."""
    duration: str
    line: int = 0


@dataclass
class ActionNotificarNode:
    """Ação: notificar mensagem (já sem as aspas)."""
    message: str
    line: int = 0


@dataclass
class ActionSeNode:
    """Ação condicional: se cond então { ... } [senão { ... }]."""
    condition: 'ConditionNode'
    then_actions: list = field(default_factory=list)
    else_actions: list = field(default_factory=list)
    line: int = 0


# ══════════════════════════════════════════════════════════════════════
# Type aliases
# ══════════════════════════════════════════════════════════════════════

ConditionNode = ConditionEstadoNode | ConditionHoraNode

TriggerNode = (
    TriggerEstadoNode | TriggerHoraNode
    | TriggerMovimentoNode | TriggerBateriaNode
)

ActionNode = (
    ActionLigarNode | ActionDesligarNode | ActionEsperarNode
    | ActionNotificarNode | ActionSeNode
)
