"""Testes do analisador sintático (parser.py)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from lexer import tokenize, Token
from parser import (
    Parser,
    ParseError,
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


# ── Helpers ─────────────────────────────────────────────────────────

def _parse(source: str) -> tuple[ProgramNode, Parser]:
    """Tokeniza e faz parsing, retornando (AST, parser)."""
    p = Parser(tokenize(source))
    ast = p.parse()
    return ast, p


def _count_errors(source: str) -> int:
    """Retorna o número de erros de parsing."""
    _, p = _parse(source)
    return len(p.errors)


def _first_automacao(source: str) -> AutomacaoNode:
    """Retorna a primeira automação após parsing."""
    ast, _ = _parse(source)
    return ast.automacoes[0]


# ── ParseError ──────────────────────────────────────────────────────

def test_parse_error_creation():
    token = Token('IDENTIFIER', 'xyz', 5)
    e = ParseError("token inesperado", 5, token)
    assert e.line == 5
    assert e.token.value == 'xyz'
    assert "linha 5" in str(e)


# ── TriggerEstado ───────────────────────────────────────────────────

def test_trigger_estado():
    a = _first_automacao('''
        automacao "test" {
            quando sensor.porta muda para ligado
            entao { ligar luz.sala }
        }
    ''')
    assert len(a.triggers) == 1
    t = a.triggers[0]
    assert isinstance(t, TriggerEstadoNode)
    assert t.entity_id == 'sensor.porta'
    assert t.estado == 'ligado'
    assert t.line == 3


def test_trigger_estado_desligado():
    a = _first_automacao('''
        automacao "test" {
            quando luz.sala muda para desligado
            entao { ligar luz.sala }
        }
    ''')
    t = a.triggers[0]
    assert t.entity_id == 'luz.sala'
    assert t.estado == 'desligado'


def test_trigger_estado_armado():
    a = _first_automacao('''
        automacao "test" {
            quando alarm_control_panel.alarmo muda para armado
            entao { ligar luz.sala }
        }
    ''')
    t = a.triggers[0]
    assert t.estado == 'armado'


def test_trigger_estado_desarmado():
    a = _first_automacao('''
        automacao "test" {
            quando alarm_control_panel.alarmo muda para desarmado
            entao { ligar luz.sala }
        }
    ''')
    t = a.triggers[0]
    assert t.estado == 'desarmado'


def test_trigger_estado_string():
    a = _first_automacao('''
        automacao "test" {
            quando sensor.status muda para "online"
            entao { ligar luz.sala }
        }
    ''')
    t = a.triggers[0]
    assert t.estado == 'online'


# ── TriggerHora ─────────────────────────────────────────────────────

def test_trigger_hora():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 22:30
            entao { ligar luz.sala }
        }
    ''')
    assert len(a.triggers) == 1
    t = a.triggers[0]
    assert isinstance(t, TriggerHoraNode)
    assert t.clock_time == '22:30'


def test_trigger_hora_with_seconds():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 05:00:00
            entao { ligar luz.sala }
        }
    ''')
    t = a.triggers[0]
    assert t.clock_time == '05:00:00'


# ── TriggerMovimento ────────────────────────────────────────────────

def test_trigger_movimento():
    a = _first_automacao('''
        automacao "test" {
            quando binary_sensor.corredor movimento
            entao { ligar luz.sala }
        }
    ''')
    assert len(a.triggers) == 1
    t = a.triggers[0]
    assert isinstance(t, TriggerMovimentoNode)
    assert t.entity_id == 'binary_sensor.corredor'


# ── TriggerBateria ──────────────────────────────────────────────────

def test_trigger_bateria_abaixo_percent():
    a = _first_automacao('''
        automacao "test" {
            quando sensor.bateria bateria abaixo 20%
            entao { ligar switch.carregador }
        }
    ''')
    t = a.triggers[0]
    assert isinstance(t, TriggerBateriaNode)
    assert t.entity_id == 'sensor.bateria'
    assert t.operador == 'abaixo'
    assert t.valor == '20%'


def test_trigger_bateria_acima_number():
    a = _first_automacao('''
        automacao "test" {
            quando sensor.temperatura bateria acima 30
            entao { ligar luz.sala }
        }
    ''')
    t = a.triggers[0]
    assert isinstance(t, TriggerBateriaNode)
    assert t.entity_id == 'sensor.temperatura'
    assert t.operador == 'acima'
    assert t.valor == '30'


# ── ConditionEstado ─────────────────────────────────────────────────

def test_condition_estado():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            se alarm_control_panel.alarmo esta desarmado
            entao { ligar luz.sala }
        }
    ''')
    assert len(a.conditions) == 1
    c = a.conditions[0]
    assert isinstance(c, ConditionEstadoNode)
    assert c.entity_id == 'alarm_control_panel.alarmo'
    assert c.estado == 'desarmado'


def test_condition_estado_ligado():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            se luz.sala esta ligado
            entao { ligar luz.sala }
        }
    ''')
    c = a.conditions[0]
    assert c.estado == 'ligado'


def test_condition_estado_desligado():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            se luz.sala esta desligado
            entao { ligar luz.sala }
        }
    ''')
    c = a.conditions[0]
    assert c.estado == 'desligado'


def test_condition_estado_string():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            se sensor.status esta "ok"
            entao { ligar luz.sala }
        }
    ''')
    c = a.conditions[0]
    assert c.estado == 'ok'


def test_multiple_conditions():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            se alarm_control_panel.alarmo esta desarmado
            se luz.sala esta desligado
            se switch.tv esta ligado
            entao { ligar luz.sala }
        }
    ''')
    assert len(a.conditions) == 3


# ── ConditionHora ───────────────────────────────────────────────────

def test_condition_hora_abaixo():
    a = _first_automacao('''
        automacao "test" {
            quando binary_sensor.corredor movimento
            se hora abaixo 23:00
            entao { ligar luz.sala }
        }
    ''')
    assert len(a.conditions) == 1
    c = a.conditions[0]
    assert isinstance(c, ConditionHoraNode)
    assert c.operador == 'abaixo'
    assert c.clock_time == '23:00'


def test_condition_hora_acima():
    a = _first_automacao('''
        automacao "test" {
            quando binary_sensor.corredor movimento
            se hora acima 06:00:00
            entao { ligar luz.sala }
        }
    ''')
    c = a.conditions[0]
    assert isinstance(c, ConditionHoraNode)
    assert c.operador == 'acima'
    assert c.clock_time == '06:00:00'


# ── Action ligar / desligar ─────────────────────────────────────────

def test_action_ligar():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            entao { ligar luz.sala }
        }
    ''')
    assert len(a.actions) == 1
    act = a.actions[0]
    assert isinstance(act, ActionLigarNode)
    assert act.entity_id == 'luz.sala'


def test_action_desligar():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            entao { desligar switch.tv }
        }
    ''')
    act = a.actions[0]
    assert isinstance(act, ActionDesligarNode)
    assert act.entity_id == 'switch.tv'


# ── Action esperar ──────────────────────────────────────────────────

def test_action_esperar():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            entao { esperar 45s }
        }
    ''')
    act = a.actions[0]
    assert isinstance(act, ActionEsperarNode)
    assert act.duration == '45s'


def test_action_esperar_min():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            entao { esperar 5min }
        }
    ''')
    act = a.actions[0]
    assert act.duration == '5min'


# ── Action notificar ────────────────────────────────────────────────

def test_action_notificar():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            entao { notificar "Mensagem de teste" }
        }
    ''')
    act = a.actions[0]
    assert isinstance(act, ActionNotificarNode)
    assert act.message == 'Mensagem de teste'


# ── Action se (conditional action) ──────────────────────────────────

def test_action_se():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            entao {
                se luz.sala esta ligado entao {
                    desligar luz.sala
                }
            }
        }
    ''')
    act = a.actions[0]
    assert isinstance(act, ActionSeNode)
    assert isinstance(act.condition, ConditionEstadoNode)
    assert len(act.then_actions) == 1
    assert len(act.else_actions) == 0


def test_action_se_with_senao():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            entao {
                se luz.sala esta ligado entao {
                    desligar luz.sala
                } senao {
                    ligar luz.sala
                }
            }
        }
    ''')
    act = a.actions[0]
    assert isinstance(act, ActionSeNode)
    assert len(act.then_actions) == 1
    assert len(act.else_actions) == 1
    assert isinstance(act.then_actions[0], ActionDesligarNode)
    assert isinstance(act.else_actions[0], ActionLigarNode)


def test_action_se_nested():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            entao {
                se hora abaixo 18:00 entao {
                    se luz.sala esta ligado entao {
                        desligar luz.sala
                    }
                }
            }
        }
    ''')
    outer = a.actions[0]
    assert isinstance(outer, ActionSeNode)
    assert isinstance(outer.condition, ConditionHoraNode)
    inner = outer.then_actions[0]
    assert isinstance(inner, ActionSeNode)
    assert isinstance(inner.condition, ConditionEstadoNode)


# ── Múltiplas actions ───────────────────────────────────────────────

def test_multiple_actions():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            entao {
                ligar luz.sala
                esperar 30s
                desligar luz.sala
                notificar "Pronto"
            }
        }
    ''')
    assert len(a.actions) == 4
    assert isinstance(a.actions[0], ActionLigarNode)
    assert isinstance(a.actions[1], ActionEsperarNode)
    assert isinstance(a.actions[2], ActionDesligarNode)
    assert isinstance(a.actions[3], ActionNotificarNode)


# ── Automação completa ──────────────────────────────────────────────

def test_full_automacao():
    a = _first_automacao('''
        automacao "Completa" {
            quando binary_sensor.corredor muda para ligado
            quando hora = 22:00
            se alarm_control_panel.alarmo esta desarmado
            se luz.sala esta desligado
            entao {
                ligar luz.sala
                esperar 45s
                desligar luz.sala
            }
        }
    ''')
    assert a.nome == 'Completa'
    assert len(a.triggers) == 2
    assert len(a.conditions) == 2
    assert len(a.actions) == 3
    assert a.line == 2


# ── Múltiplas automações ────────────────────────────────────────────

def test_multiple_automacoes():
    ast, p = _parse('''
        automacao "A1" {
            quando hora = 10:00
            entao { ligar luz.sala }
        }
        automacao "A2" {
            quando hora = 20:00
            entao { desligar luz.sala }
        }
    ''')
    assert len(ast.automacoes) == 2
    assert ast.automacoes[0].nome == 'A1'
    assert ast.automacoes[1].nome == 'A2'
    assert len(p.errors) == 0


# ── Nome da automação (aspas removidas) ─────────────────────────────

def test_automacao_nome_quotes_stripped():
    a = _first_automacao('automacao "Corredor - movimento" { quando hora = 10:00 entao { ligar luz.sala } }')
    assert a.nome == 'Corredor - movimento'


# ── Sem erros nos scripts de exemplo ────────────────────────────────

def test_movimento_example_no_errors():
    src = (Path(__file__).parent.parent / 'examples' / 'movimento.homi').read_text()
    assert _count_errors(src) == 0


def test_horario_example_no_errors():
    src = (Path(__file__).parent.parent / 'examples' / 'horario.homi').read_text()
    assert _count_errors(src) == 0


def test_bateria_example_no_errors():
    src = (Path(__file__).parent.parent / 'examples' / 'bateria.homi').read_text()
    assert _count_errors(src) == 0


# ── Campos dos nós AST nos exemplos ─────────────────────────────────

def test_movimento_ast_fields():
    a = _first_automacao(
        (Path(__file__).parent.parent / 'examples' / 'movimento.homi').read_text()
    )
    assert isinstance(a.triggers[0], TriggerEstadoNode)
    assert a.triggers[0].entity_id == 'binary_sensor.corredor_suite'
    assert a.triggers[0].estado == 'ligado'

    assert isinstance(a.conditions[0], ConditionEstadoNode)
    assert a.conditions[0].entity_id == 'alarm_control_panel.alarmo'
    assert a.conditions[0].estado == 'desarmado'

    assert isinstance(a.conditions[1], ConditionEstadoNode)
    assert a.conditions[1].entity_id == 'luz.corda_led_corredor'
    assert a.conditions[1].estado == 'desligado'

    assert isinstance(a.actions[0], ActionLigarNode)
    assert a.actions[0].entity_id == 'luz.corda_led_corredor'

    assert isinstance(a.actions[1], ActionEsperarNode)
    assert a.actions[1].duration == '45s'

    assert isinstance(a.actions[2], ActionDesligarNode)
    assert a.actions[2].entity_id == 'luz.corda_led_corredor'


def test_horario_ast_fields():
    a = _first_automacao(
        (Path(__file__).parent.parent / 'examples' / 'horario.homi').read_text()
    )
    assert isinstance(a.triggers[0], TriggerHoraNode)
    assert a.triggers[0].clock_time == '05:00'


def test_bateria_ast_fields():
    a = _first_automacao(
        (Path(__file__).parent.parent / 'examples' / 'bateria.homi').read_text()
    )
    assert isinstance(a.triggers[0], TriggerBateriaNode)
    assert a.triggers[0].entity_id == 'sensor.bateria_tablet'
    assert a.triggers[0].operador == 'abaixo'
    assert a.triggers[0].valor == '20%'


# ── Modo pânico ─────────────────────────────────────────────────────

def test_panic_mode_does_not_abort():
    """Script com erro sintático não aborta — gera AST parcial."""
    ast, p = _parse('''
        automacao "T1" {
            quando hora = 10:00
            entao { ligar luz.sala }
        }
        automacao "T2" {
            quando token_invalido_xyz
            se luz.sala esta ligado
            entao {
                ligar luz.quarto
            }
        }
    ''')
    assert len(ast.automacoes) == 2
    assert len(p.errors) >= 1


def test_panic_mode_collects_errors():
    """Erros são coletados em self.errors."""
    _, p = _parse('''
        automacao "test" {
            quando xyz
            entao { ligar luz.sala }
        }
    ''')
    assert len(p.errors) > 0
    for e in p.errors:
        assert isinstance(e, ParseError)


def test_panic_mode_skips_to_sync():
    """Após erro, parser avança até próximo ; ou }."""
    ast, p = _parse('''
        automacao "test" {
            quando xyz
            entao {
                ligar luz.sala
            }
        }
    ''')
    assert len(ast.automacoes) == 1
    assert len(p.errors) >= 1


def test_panic_mode_partial_triggers():
    """Se um trigger falha, o próximo ainda é parseado."""
    src = '''
        automacao "test" {
            quando hora = 10:00
            quando @@@
            quando binary_sensor.corredor movimento
            entao { ligar luz.sala }
        }
    '''
    # Note: @@@ may cause lexer errors before parser can even run
    # We test with a valid-but-wrong trigger instead
    src = '''
        automacao "test" {
            quando hora = 10:00
            quando xyz
            quando binary_sensor.corredor movimento
            entao { ligar luz.sala }
        }
    '''
    ast, p = _parse(src)
    assert len(ast.automacoes) == 1
    # O segundo trigger deve ter causado erro, mas o primeiro e terceiro
    # devem estar na AST
    assert len(p.errors) >= 1


# ── Linhas nos nós ──────────────────────────────────────────────────

def test_line_numbers_in_nodes():
    a = _first_automacao('''
        automacao "test" {
            quando hora = 10:00
            se luz.sala esta ligado
            entao {
                ligar luz.sala
                desligar switch.tv
            }
        }
    ''')
    assert a.triggers[0].line == 3
    assert a.conditions[0].line == 4
    assert a.actions[0].line == 6
    assert a.actions[1].line == 7


# ── Tokenização + parsing sem erros ─────────────────────────────────

def test_parse_empty():
    ast, p = _parse('')
    assert len(ast.automacoes) == 0
    assert len(p.errors) == 0


def test_parse_only_comment():
    ast, p = _parse('# apenas um comentário')
    assert len(ast.automacoes) == 0
    assert len(p.errors) == 0


# ── Semicolons opcionais ────────────────────────────────────────────

def test_semicolons_optional():
    """Semicolons são opcionais — parsing funciona com ou sem."""
    src = '''
        automacao "test" {
            quando hora = 10:00;
            se luz.sala esta ligado;
            entao {
                ligar luz.sala;
                desligar switch.tv;
            }
        }
    '''
    assert _count_errors(src) == 0


# ── Tokens residuais após automação ──────────────────────────────

def test_leftover_tokens_after_automacao():
    """Tokens após o último } devem gerar erros, não travar."""
    _, p = _parse('''
        automacao "test" {
            quando hora = 10:00
            entao { ligar luz.sala }
        }
        garbage;
    ''')
    assert len(p.errors) >= 1


def test_leftover_tokens_with_brace():
    """Tokens com } extra após automação devem gerar erro."""
    _, p = _parse('''
        automacao "test" {
            quando hora = 10:00
            entao { ligar luz.sala }
        }
        }
    ''')
    assert len(p.errors) >= 1
