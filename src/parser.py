"""
Analisador Sintático (Parser) LL(1) da linguagem Homi.

Parser descendente recursivo com tabela preditiva manual.
Cada não-terminal da gramática é implementado como um método _parse_<nome>().
Implementa modo pânico: ao encontrar erro, sincroniza em ';' e '}'.

Interface:
    Parser(tokens).parse() → ProgramNode
    Parser.errors → list[ParseError] (erros coletados, nunca aborta)
"""

from dataclasses import dataclass, field
from lexer import Token


# ══════════════════════════════════════════════════════════════════════
# Nós da AST
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
    """Trigger: entity bateria abaixo/acima N%."""
    entity_id: str
    operador: str
    valor: str
    line: int = 0


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


@dataclass
class ActionLigarNode:
    """Ação: ligar entity."""
    entity_id: str
    line: int = 0


@dataclass
class ActionDesligarNode:
    """Ação: desligar entity."""
    entity_id: str
    line: int = 0


@dataclass
class ActionEsperarNode:
    """Ação: esperar duration."""
    duration: str
    line: int = 0


@dataclass
class ActionNotificarNode:
    """Ação: notificar mensagem."""
    message: str
    line: int = 0


@dataclass
class ActionSeNode:
    """Ação condicional: se cond então { ... } [senão { ... }]."""
    condition: 'ConditionNode'
    then_actions: list = field(default_factory=list)
    else_actions: list = field(default_factory=list)
    line: int = 0


# Union type alias para facilitar uso externo
ConditionNode = ConditionEstadoNode | ConditionHoraNode
TriggerNode = (
    TriggerEstadoNode | TriggerHoraNode
    | TriggerMovimentoNode | TriggerBateriaNode
)
ActionNode = (
    ActionLigarNode | ActionDesligarNode | ActionEsperarNode
    | ActionNotificarNode | ActionSeNode
)


# ══════════════════════════════════════════════════════════════════════
# Erro e Parser
# ══════════════════════════════════════════════════════════════════════

class ParseError(Exception):
    """Erro sintático com localização precisa."""

    def __init__(self, message: str, line: int, token: Token):
        self.message = message
        self.line = line
        self.token = token
        super().__init__(f"linha {line}: {message}")


class Parser:
    """
    Parser descendente recursivo LL(1) com modo pânico.

    Attributes:
        errors: Lista de ParseError coletados durante o parsing.
    """

    # Tokens que iniciam ações (para o loop de actions)
    _ACTION_FIRST = {
        'KW_LIGAR', 'KW_DESLIGAR', 'KW_ESPERAR',
        'KW_NOTIFICAR', 'KW_SE',
    }

    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos = 0
        self.errors: list[ParseError] = []

    # ── Helpers ───────────────────────────────────────────────────

    def _peek(self) -> Token:
        """Retorna o token atual sem consumi-lo."""
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        """Consome e retorna o token atual."""
        token = self._tokens[self._pos]
        self._pos += 1
        return token

    def _check(self, *types: str) -> bool:
        """Verifica se o token atual é de algum dos tipos dados."""
        return self._peek().type in types

    def _match(self, expected_type: str) -> Token | None:
        """
        Consome o token se o tipo coincidir; senão reporta erro e sincroniza.
        Retorna o token consumido ou None em caso de erro.
        """
        token = self._peek()
        if token.type == expected_type:
            return self._advance()
        self._error(
            f"esperado '{expected_type}', encontrado '{token.value}'",
        )
        self._sync()
        return None

    def _error(self, message: str):
        """Registra um ParseError com o token atual."""
        token = self._peek()
        self.errors.append(ParseError(message, token.line, token))

    def _sync(self):
        """
        Modo pânico: descarta tokens até encontrar um ponto de sincronização
        (SEMICOLON, RBRACE ou EOF). Consome SEMICOLON e RBRACE para
        permitir progresso do parser; EOF é apenas parada sem consumo.
        """
        while True:
            token = self._peek()
            if token.type in ('SEMICOLON', 'RBRACE'):
                self._advance()  # consome para que o chamador não trave
                break
            if token.type == 'EOF':
                break
            self._pos += 1

    def _optional_semicolon(self):
        """Consome um SEMICOLON opcional, se presente."""
        if self._check('SEMICOLON'):
            self._advance()

    # ── program → automacao* ─────────────────────────────────────

    def parse(self) -> ProgramNode:
        """
        Analisa a lista de tokens e retorna a AST completa.

        Continua após erros (modo pânico). Todos os erros
        são coletados em self.errors.
        """
        automacoes: list[AutomacaoNode] = []
        while self._check('KW_AUTOMACAO'):
            automacao = self._parse_automacao()
            if automacao is not None:
                automacoes.append(automacao)

        # Erro se sobraram tokens não processados após todas automações
        if not self._check('EOF'):
            self._error(f"token inesperado '{self._peek().value}'")
            self._sync()
            # descarta o que sobrou após o ponto de sincronização
            while not self._check('EOF'):
                self._pos += 1

        return ProgramNode(automacoes=automacoes)

    # ── automacao → KW_AUTOMACAO STRING LBRACE
    #                trigger+ condition* action_block RBRACE ───────

    def _parse_automacao(self) -> AutomacaoNode | None:
        """
        Analisa uma declaração de automação.

        Retorna AutomacaoNode ou None se o cabeçalho for inválido.
        """
        line = self._peek().line

        # Cabeçalho: automacao "Nome" {
        if not self._check('KW_AUTOMACAO'):
            return None
        self._advance()

        name_token = self._match('STRING')
        if name_token is None:
            return None
        nome = name_token.value[1:-1]  # remove aspas

        if self._match('LBRACE') is None:
            return None

        # Corpo
        triggers: list = []
        conditions: list = []
        actions: list = []

        # triggers (um ou mais): enquanto encontrar KW_QUANDO
        while self._check('KW_QUANDO'):
            trigger = self._parse_trigger()
            if trigger is not None:
                triggers.append(trigger)

        # conditions (zero ou mais): enquanto encontrar KW_SE
        while self._check('KW_SE'):
            # Precisa verificar se o próximo KW_SE é realmente uma
            # condition e não uma action_se (que está dentro do bloco entao).
            # A gramática resolve isso: conditions vêm ANTES do entao,
            # actions_se estão DENTRO do bloco entao.
            condition = self._parse_condition()
            if condition is not None:
                conditions.append(condition)

        # action_block: entao { action+ }
        actions = self._parse_action_block()

        # Fechamento
        if self._check('RBRACE'):
            self._advance()
        else:
            self._error(f"esperado '}}' para fechar automação, "
                        f"encontrado '{self._peek().value}'")
            self._sync()

        return AutomacaoNode(
            nome=nome,
            triggers=triggers,
            conditions=conditions,
            actions=actions,
            line=line,
        )

    # ── trigger → KW_QUANDO trigger_body SEMICOLON? ──────────────

    def _parse_trigger(self) -> TriggerNode | None:
        """
        Analisa um trigger.

        Retorna um TriggerNode ou None em caso de erro.
        """
        if not self._check('KW_QUANDO'):
            return None
        self._advance()

        trigger = self._parse_trigger_body()
        self._optional_semicolon()
        return trigger

    # ── trigger_body → alternativas ───────────────────────────────

    def _parse_trigger_body(self) -> TriggerNode | None:
        """
        Analisa o corpo de um trigger:
          - ENTITY_ID KW_MUDA KW_PARA estado       → TriggerEstadoNode
          - KW_HORA EQUALS CLOCK_TIME               → TriggerHoraNode
          - ENTITY_ID KW_MOVIMENTO                  → TriggerMovimentoNode
          - ENTITY_ID KW_BATERIA KW_ABAIXO|KW_ACIMA NUMBER|PERCENT
                                                    → TriggerBateriaNode
        """
        # Caso 1: trigger por hora
        if self._check('KW_HORA'):
            line = self._peek().line
            self._advance()
            if self._match('EQUALS') is None:
                return None
            time_token = self._match('CLOCK_TIME')
            if time_token is None:
                return None
            return TriggerHoraNode(clock_time=time_token.value, line=line)

        # Caso 2: trigger por ENTITY_ID (muda para / movimento / bateria)
        if self._check('ENTITY_ID'):
            entity_token = self._advance()
            entity_id = entity_token.value
            line = entity_token.line

            # trigger_estado: entity muda para estado
            if self._check('KW_MUDA'):
                self._advance()
                if self._match('KW_PARA') is None:
                    return None
                estado = self._parse_estado()
                if estado is None:
                    return None
                return TriggerEstadoNode(
                    entity_id=entity_id, estado=estado, line=line,
                )

            # trigger_movimento: entity movimento
            elif self._check('KW_MOVIMENTO'):
                self._advance()
                return TriggerMovimentoNode(
                    entity_id=entity_id, line=line,
                )

            # trigger_bateria: entity bateria abaixo/acima valor
            elif self._check('KW_BATERIA'):
                self._advance()
                if not self._check('KW_ABAIXO', 'KW_ACIMA'):
                    self._error(
                        f"esperado 'abaixo' ou 'acima', "
                        f"encontrado '{self._peek().value}'",
                    )
                    self._sync()
                    return None
                operador = self._advance().value
                if not self._check('NUMBER', 'PERCENT'):
                    self._error(
                        f"esperado número ou porcentagem, "
                        f"encontrado '{self._peek().value}'",
                    )
                    self._sync()
                    return None
                valor = self._advance().value
                return TriggerBateriaNode(
                    entity_id=entity_id,
                    operador=operador,
                    valor=valor,
                    line=line,
                )

            # ENTITY_ID seguido de token inesperado
            self._error(
                f"após entity_id, esperado 'muda', 'movimento' ou 'bateria', "
                f"encontrado '{self._peek().value}'",
            )
            self._sync()
            return None

        # Nenhum iniciador de trigger_body reconhecido
        self._error(
            f"esperado entity_id ou 'hora' em trigger, "
            f"encontrado '{self._peek().value}'",
        )
        self._sync()
        return None

    # ── estado → KW_LIGADO | KW_DESLIGADO | KW_ARMADO |
    #             KW_DESARMADO | STRING ─────────────────────────────

    def _parse_estado(self) -> str | None:
        """Analisa um valor de estado e retorna a string correspondente."""
        if self._check(
            'KW_LIGADO', 'KW_DESLIGADO', 'KW_ARMADO',
            'KW_DESARMADO', 'STRING',
        ):
            token = self._advance()
            # STRING do lexer inclui as aspas; removê-las
            if token.type == 'STRING':
                return token.value[1:-1]
            return token.value

        self._error(
            f"esperado estado (ligado, desligado, armado, desarmado ou string), "
            f"encontrado '{self._peek().value}'",
        )
        self._sync()
        return None

    # ── condition → KW_SE condition_body SEMICOLON? ───────────────

    def _parse_condition(self) -> ConditionNode | None:
        """Analisa uma condição (se ...)."""
        if not self._check('KW_SE'):
            return None
        self._advance()

        condition = self._parse_condition_body()
        self._optional_semicolon()
        return condition

    # ── condition_body → alternativas ─────────────────────────────

    def _parse_condition_body(self) -> ConditionNode | None:
        """
        Analisa o corpo de uma condição:
          - ENTITY_ID KW_ESTA estado               → ConditionEstadoNode
          - KW_HORA KW_ABAIXO|KW_ACIMA CLOCK_TIME   → ConditionHoraNode
        """
        # condition_hora: hora abaixo/acima HH:MM
        if self._check('KW_HORA'):
            line = self._peek().line
            self._advance()
            if not self._check('KW_ABAIXO', 'KW_ACIMA'):
                self._error(
                    f"esperado 'abaixo' ou 'acima', "
                    f"encontrado '{self._peek().value}'",
                )
                self._sync()
                return None
            operador = self._advance().value
            time_token = self._match('CLOCK_TIME')
            if time_token is None:
                return None
            return ConditionHoraNode(
                operador=operador,
                clock_time=time_token.value,
                line=line,
            )

        # condition_estado: entity esta estado
        if self._check('ENTITY_ID'):
            entity_token = self._advance()
            entity_id = entity_token.value
            line = entity_token.line

            if self._match('KW_ESTA') is None:
                return None

            estado = self._parse_estado()
            if estado is None:
                return None
            return ConditionEstadoNode(
                entity_id=entity_id, estado=estado, line=line,
            )

        self._error(
            f"esperado entity_id ou 'hora' em condição, "
            f"encontrado '{self._peek().value}'",
        )
        self._sync()
        return None

    # ── action_block → KW_ENTAO LBRACE action+ RBRACE ────────────

    def _parse_action_block(self) -> list[ActionNode]:
        """Analisa o bloco de ações (entao { ... })."""
        actions: list[ActionNode] = []

        if not self._check('KW_ENTAO'):
            self._error(
                f"esperado 'entao' para iniciar bloco de ações, "
                f"encontrado '{self._peek().value}'",
            )
            self._sync()
            return actions

        self._advance()  # 'entao'

        if self._match('LBRACE') is None:
            # tenta sincronizar para reduzir cascata de erros
            self._sync()
            return actions

        while self._check(*self._ACTION_FIRST):
            action = self._parse_action()
            if action is not None:
                actions.append(action)
            # Se um erro fez sync até RBRACE, o loop para naturalmente
            # porque _check não inclui RBRACE

        if self._check('RBRACE'):
            self._advance()
        else:
            self._error(
                f"esperado '}}' para fechar bloco de ações, "
                f"encontrado '{self._peek().value}'",
            )
            self._sync()

        return actions

    # ── action → KW_LIGAR ENTITY_ID
    #           | KW_DESLIGAR ENTITY_ID
    #           | KW_ESPERAR TIME_UNIT
    #           | KW_NOTIFICAR STRING
    #           | KW_SE condition_body KW_ENTAO LBRACE action+ RBRACE
    #               (KW_SENAO LBRACE action+ RBRACE)? ──────────────

    def _parse_action(self) -> ActionNode | None:
        """Analisa uma ação individual."""
        token = self._peek()

        # Ação: ligar entity_id
        if token.type == 'KW_LIGAR':
            line = token.line
            self._advance()
            entity_token = self._match('ENTITY_ID')
            if entity_token is None:
                return None
            self._optional_semicolon()
            return ActionLigarNode(entity_id=entity_token.value, line=line)

        # Ação: desligar entity_id
        if token.type == 'KW_DESLIGAR':
            line = token.line
            self._advance()
            entity_token = self._match('ENTITY_ID')
            if entity_token is None:
                return None
            self._optional_semicolon()
            return ActionDesligarNode(entity_id=entity_token.value, line=line)

        # Ação: esperar TIME_UNIT
        if token.type == 'KW_ESPERAR':
            line = token.line
            self._advance()
            time_token = self._match('TIME_UNIT')
            if time_token is None:
                return None
            self._optional_semicolon()
            return ActionEsperarNode(duration=time_token.value, line=line)

        # Ação: notificar STRING
        if token.type == 'KW_NOTIFICAR':
            line = token.line
            self._advance()
            msg_token = self._match('STRING')
            if msg_token is None:
                return None
            self._optional_semicolon()
            return ActionNotificarNode(
                message=msg_token.value[1:-1], line=line,
            )

        # Ação: se ... entao { ... } [senao { ... }]
        if token.type == 'KW_SE':
            line = token.line
            self._advance()

            condition = self._parse_condition_body()
            if condition is None:
                return None

            # entao { action+ }
            if self._match('KW_ENTAO') is None:
                return None
            if self._match('LBRACE') is None:
                return None

            then_actions: list[ActionNode] = []
            while self._check(*self._ACTION_FIRST):
                act = self._parse_action()
                if act is not None:
                    then_actions.append(act)

            if self._check('RBRACE'):
                self._advance()
            else:
                self._error(
                    f"esperado '}}' para fechar bloco entao, "
                    f"encontrado '{self._peek().value}'",
                )
                self._sync()

            # Opcional: senao { action+ }
            else_actions: list[ActionNode] = []
            if self._check('KW_SENAO'):
                self._advance()
                if self._match('LBRACE') is None:
                    return ActionSeNode(
                        condition=condition,
                        then_actions=then_actions,
                        else_actions=else_actions,
                        line=line,
                    )

                while self._check(*self._ACTION_FIRST):
                    act = self._parse_action()
                    if act is not None:
                        else_actions.append(act)

                if self._check('RBRACE'):
                    self._advance()

            return ActionSeNode(
                condition=condition,
                then_actions=then_actions,
                else_actions=else_actions,
                line=line,
            )

        # Token inesperado — não deveria chegar aqui se o chamador
        # filtrou corretamente com _ACTION_FIRST
        self._error(
            f"ação inesperada: '{token.value}'",
        )
        self._sync()
        return None
