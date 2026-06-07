"""
Gerador de Código YAML da linguagem Homi.

Percorre a AST produzida pelo parser (e validada pelo semantic) e emite
YAML compatível com o Home Assistant. Usa PyYAML para serialização.

Interface:
    CodeGenerator(ast).generate() → str (YAML)
"""

from typing import Any

import yaml

from nodes import (
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


# ── Tabelas de mapeamento ──────────────────────────────────────────

# Domínio Homi → domínio Home Assistant
_DOMAIN_TO_HA: dict[str, str] = {
    'luz':           'light',
    'switch':        'switch',
    'media_player':  'media_player',
}

# Estado Homi → estado HA (string com aspas no YAML)
_ESTADO_TO_HA: dict[str, str] = {
    'ligado':    'on',
    'desligado': 'off',
    'armado':    'armed',
    'desarmado': 'disarmed',
}


# ══════════════════════════════════════════════════════════════════════
# Gerador de Código
# ══════════════════════════════════════════════════════════════════════

class CodeGenerator:
    """
    Gerador de código YAML para o Home Assistant.

    Recebe a AST e produz YAML válido com triggers, conditions,
    actions e mode: single para cada automação.
    """

    def __init__(self, ast: ProgramNode):
        self._ast = ast

    # ── Entry point ───────────────────────────────────────────────

    def generate(self) -> str:
        """
        Percorre a AST e retorna a string YAML completa.

        Returns:
            String YAML com todas as automações.
        """
        automations: list[dict[str, Any]] = []
        for automacao in self._ast.automacoes:
            automations.append(self._generate_automacao(automacao))

        # Serializar com PyYAML
        return yaml.dump(
            automations,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )

    # ── Automação ─────────────────────────────────────────────────

    def _generate_automacao(self, node: AutomacaoNode) -> dict[str, Any]:
        """Gera o dict YAML de uma automação completa."""
        return {
            'alias': node.nome,
            'triggers': [self._generate_trigger(t) for t in node.triggers],
            'conditions': [self._generate_condition(c) for c in node.conditions],
            'actions': [self._generate_action(a) for a in node.actions],
            'mode': 'single',
        }

    # ── Triggers ──────────────────────────────────────────────────

    def _generate_trigger(self, node) -> dict[str, Any]:
        """Gera o dict YAML de um trigger."""
        if isinstance(node, TriggerEstadoNode):
            return {
                'trigger': 'state',
                'entity_id': node.entity_id,
                'to': _ESTADO_TO_HA.get(node.estado, node.estado),
            }

        if isinstance(node, TriggerHoraNode):
            return {
                'trigger': 'time',
                'at': _normalize_clock_time(node.clock_time),
            }

        if isinstance(node, TriggerMovimentoNode):
            return {
                'trigger': 'state',
                'entity_id': node.entity_id,
                'to': 'on',
            }

        if isinstance(node, TriggerBateriaNode):
            key = 'below' if node.operador == 'abaixo' else 'above'
            valor_num = _parse_numeric_value(node.valor)
            return {
                'trigger': 'numeric_state',
                'entity_id': node.entity_id,
                'attribute': 'battery_level',
                key: valor_num,
            }

        raise NotImplementedError(f"nó de trigger não suportado: {type(node)}")

    # ── Conditions ────────────────────────────────────────────────

    def _generate_condition(self, node) -> dict[str, Any]:
        """Gera o dict YAML de uma condição."""
        if isinstance(node, ConditionEstadoNode):
            return {
                'condition': 'state',
                'entity_id': node.entity_id,
                'state': _ESTADO_TO_HA.get(node.estado, node.estado),
            }

        if isinstance(node, ConditionHoraNode):
            key = 'before' if node.operador == 'abaixo' else 'after'
            return {
                'condition': 'time',
                key: _normalize_clock_time(node.clock_time),
            }

        raise NotImplementedError(
            f"nó de condition não suportado: {type(node)}",
        )

    # ── Actions ───────────────────────────────────────────────────

    def _generate_action(self, node) -> dict[str, Any]:
        """Gera o dict YAML de uma ação."""
        if isinstance(node, ActionLigarNode):
            return self._make_turn_action(node.entity_id, 'turn_on')

        if isinstance(node, ActionDesligarNode):
            return self._make_turn_action(node.entity_id, 'turn_off')

        if isinstance(node, ActionEsperarNode):
            return self._make_delay(node.duration)

        if isinstance(node, ActionNotificarNode):
            return {
                'action': 'notify.mobile_app',
                'data': {
                    'message': node.message,
                },
            }

        if isinstance(node, ActionSeNode):
            return self._generate_action_se(node)

        raise NotImplementedError(
            f"nó de action não suportado: {type(node)}",
        )

    # ── Helpers de actions ────────────────────────────────────────

    def _make_turn_action(self, entity_id: str,
                          operation: str) -> dict[str, Any]:
        """
        Constrói uma ação de turn_on / turn_off.

        Ex: ligar luz.sala → action: light.turn_on, target: { entity_id: luz.sala }
        """
        domain_raw = entity_id.split('.')[0]
        ha_domain = _DOMAIN_TO_HA.get(domain_raw, domain_raw)
        return {
            'action': f'{ha_domain}.{operation}',
            'target': {
                'entity_id': entity_id,
            },
        }

    def _make_delay(self, duration: str) -> dict[str, Any]:
        """
        Constrói uma ação de delay.

        Ex: esperar 45s → delay: { seconds: 45 }
            esperar 5min → delay: { minutes: 5 }
            esperar 2h → delay: { hours: 2 }
        """
        delay: dict[str, Any] = {}
        try:
            if duration.endswith('s'):
                delay['seconds'] = int(duration[:-1])
            elif duration.endswith('min'):
                delay['minutes'] = int(duration[:-3])
            elif duration.endswith('m'):
                delay['minutes'] = int(duration[:-1])
            elif duration.endswith('h'):
                delay['hours'] = int(duration[:-1])
        except (ValueError, IndexError):
            raise ValueError(
                f"duração inválida '{duration}': "
                f"formato esperado: Ns, Nmin, Nm ou Nh"
            ) from None
        return {'delay': delay}

    def _generate_action_se(self, node: ActionSeNode) -> dict[str, Any]:
        """
        Constrói uma ação choose (if/else).

        se CONDITION entao { ... }  →
          choose:
            - conditions: [<condition>]
              sequence: [<actions>]

        se CONDITION entao { ... } senao { ... }  →
          choose:
            - conditions: [<condition>]
              sequence: [<actions>]
            - conditions: []
              sequence: [<else_actions>]
        """
        choices: list[dict[str, Any]] = []

        # Bloco then
        choices.append({
            'conditions': [self._generate_condition(node.condition)],
            'sequence': [self._generate_action(a) for a in node.then_actions],
        })

        # Bloco else (opcional)
        if node.else_actions:
            choices.append({
                'conditions': [],
                'sequence': [
                    self._generate_action(a) for a in node.else_actions
                ],
            })

        return {'choose': choices}


# ── Funções auxiliares de normalização ─────────────────────────────────

def _normalize_clock_time(time_str: str) -> str:
    """
    Normaliza CLOCK_TIME para HH:MM:SS.

    '22:30'    → '22:30:00'
    '22:30:00' → '22:30:00' (sem alteração)
    '5:00'     → '05:00:00'
    """
    parts = time_str.split(':')
    if len(parts) == 2:
        hh = parts[0].zfill(2)
        mm = parts[1].zfill(2)
        return f'{hh}:{mm}:00'
    if len(parts) == 3:
        hh = parts[0].zfill(2)
        mm = parts[1].zfill(2)
        ss = parts[2].zfill(2)
        return f'{hh}:{mm}:{ss}'
    raise ValueError(
        f"formato de horário inválido: '{time_str}' "
        f"(esperado: HH:MM ou HH:MM:SS)"
    )


def _parse_numeric_value(value: str) -> int | float:
    """
    Converte valor (possivelmente com '%') para número.

    '20%' → 20
    '30'  → 30
    '3.5' → 3.5
    """
    clean = value.rstrip('%')
    if '.' in clean:
        return float(clean)
    return int(clean)
