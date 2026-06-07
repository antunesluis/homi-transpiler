"""
Analisador Semântico da linguagem Homi.

Percorre a AST produzida pelo parser e valida:
  1. Domínio de ações (ligar/desligar): apenas luz, switch, media_player
  2. Domínio de triggers de movimento: apenas binary_sensor
  3. Domínio de triggers de bateria: apenas sensor
  4. Estado armado/desarmado: apenas alarm_control_panel

Também preenche a tabela de símbolos (entity_id → domínio).
Todos os erros são coletados em self.errors — nunca aborta.
"""

from parser import (
    ProgramNode,
    AutomacaoNode,
    TriggerEstadoNode,
    TriggerHoraNode,
    TriggerMovimentoNode,
    TriggerBateriaNode,
    ConditionEstadoNode,
    ConditionHoraNode,
    ActionLigarNode,
    ActionDesligarNode,
    ActionEsperarNode,
    ActionNotificarNode,
    ActionSeNode,
)


# ══════════════════════════════════════════════════════════════════════
# Erro e Tabela de Símbolos
# ══════════════════════════════════════════════════════════════════════

class SemanticError(Exception):
    """Erro semântico com mensagem e localização."""

    def __init__(self, message: str, line: int):
        self.message = message
        self.line = line
        super().__init__(f"[SEMÂNTICO] linha {line}: {message}")


class SymbolTable:
    """
    Tabela de símbolos que mapeia entity_id → domínio.

    O domínio é o prefixo antes do ponto no entity_id
    (ex: 'luz.sala' → domínio 'luz').
    """

    def __init__(self):
        self._symbols: dict[str, str] = {}

    def declare(self, entity_id: str, domain: str, line: int):
        """
        Registra uma entity_id com seu domínio.

        Se a entidade já foi declarada com o mesmo domínio,
        não faz nada (re-declaração consistente é silenciosa).
        """
        if entity_id not in self._symbols:
            self._symbols[entity_id] = domain

    def lookup(self, entity_id: str) -> str | None:
        """Retorna o domínio registrado para entity_id, ou None."""
        return self._symbols.get(entity_id)


# ══════════════════════════════════════════════════════════════════════
# Analisador Semântico
# ══════════════════════════════════════════════════════════════════════

class SemanticAnalyzer:
    """
    Analisador semântico que percorre a AST validando regras de
    compatibilidade de domínio e preenchendo a tabela de símbolos.

    Attributes:
        symbol_table: Tabela de símbolos preenchida após analyze().
        errors: Lista de SemanticError coletados durante a análise.
    """

    # Domínios que suportam as ações ligar/desligar
    _TURNABLE_DOMAINS = frozenset({'luz', 'switch', 'media_player'})

    def __init__(self, ast: ProgramNode):
        self.ast = ast
        self.symbol_table = SymbolTable()
        self.errors: list[SemanticError] = []

    # ── Entry point ───────────────────────────────────────────────

    def analyze(self) -> ProgramNode:
        """
        Percorre a AST validando regras semânticas.

        Retorna a AST original. Todos os erros são coletados
        em self.errors — nunca aborta.
        """
        for automacao in self.ast.automacoes:
            self._analyze_automacao(automacao)
        return self.ast

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _extract_domain(entity_id: str) -> str:
        """Extrai o domínio de um entity_id (prefixo antes do '.')."""
        return entity_id.split('.')[0]

    def _declare(self, entity_id: str, line: int) -> str:
        """
        Registra uma entity_id na tabela de símbolos e retorna seu domínio.
        """
        domain = self._extract_domain(entity_id)
        self.symbol_table.declare(entity_id, domain, line)
        return domain

    def _error(self, message: str, line: int):
        """Registra um erro semântico."""
        self.errors.append(SemanticError(message, line))

    # ── Visitantes ────────────────────────────────────────────────

    def _analyze_automacao(self, node: AutomacaoNode):
        for trigger in node.triggers:
            self._analyze_trigger(trigger)
        for condition in node.conditions:
            self._analyze_condition(condition)
        for action in node.actions:
            self._analyze_action(action)

    # ── Triggers ──────────────────────────────────────────────────

    def _analyze_trigger(self, node):
        if isinstance(node, TriggerEstadoNode):
            domain = self._declare(node.entity_id, node.line)
            self._check_estado_domain(domain, node.estado, node.line)

        elif isinstance(node, TriggerMovimentoNode):
            domain = self._declare(node.entity_id, node.line)
            if domain != 'binary_sensor':
                self._error(
                    f"trigger de movimento requer domínio "
                    f"'binary_sensor', encontrado '{domain}'",
                    node.line,
                )

        elif isinstance(node, TriggerBateriaNode):
            domain = self._declare(node.entity_id, node.line)
            if domain != 'sensor':
                self._error(
                    f"trigger de bateria requer domínio "
                    f"'sensor', encontrado '{domain}'",
                    node.line,
                )

        # TriggerHoraNode: sem entity_id, nada a validar

    # ── Conditions ────────────────────────────────────────────────

    def _analyze_condition(self, node):
        if isinstance(node, ConditionEstadoNode):
            domain = self._declare(node.entity_id, node.line)
            self._check_estado_domain(domain, node.estado, node.line)

        elif isinstance(node, ConditionHoraNode):
            # sem entity_id, nada a validar
            pass

    # ── Actions ───────────────────────────────────────────────────

    def _analyze_action(self, node):
        if isinstance(node, ActionLigarNode):
            domain = self._declare(node.entity_id, node.line)
            self._check_turnable(domain, node.entity_id, node.line, 'ligado')

        elif isinstance(node, ActionDesligarNode):
            domain = self._declare(node.entity_id, node.line)
            self._check_turnable(domain, node.entity_id, node.line, 'desligado')

        elif isinstance(node, ActionSeNode):
            # Valida a condição do action_se recursivamente
            self._analyze_condition(node.condition)
            for action in node.then_actions:
                self._analyze_action(action)
            for action in node.else_actions:
                self._analyze_action(action)

        # ActionEsperarNode, ActionNotificarNode: sem entity_id

    # ── Validações de domínio ────────────────────────────────────

    def _check_turnable(self, domain: str, entity_id: str,
                        line: int, action: str):
        """Valida que o domínio suporta a ação ligar/desligar."""
        if domain not in self._TURNABLE_DOMAINS:
            self._error(
                f"'{entity_id}' não pode ser {action}: "
                f"domínio '{domain}' não suporta esta ação",
                line,
            )

    def _check_estado_domain(self, domain: str, estado: str, line: int):
        """Valida que armado/desarmado só aparece com alarm_control_panel."""
        if estado in ('armado', 'desarmado'):
            if domain != 'alarm_control_panel':
                self._error(
                    f"estado '{estado}' só é válido para domínio "
                    f"'alarm_control_panel', encontrado '{domain}'",
                    line,
                )
