"""Testes do analisador semântico (semantic.py)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from lexer import tokenize
from parser import Parser
from semantic import SemanticAnalyzer, SemanticError, SymbolTable


# ── Helpers ─────────────────────────────────────────────────────────

def _analyze(source: str) -> tuple[SemanticAnalyzer, Parser]:
    """Faz parsing e análise semântica, retornando (analyzer, parser)."""
    parser = Parser(tokenize(source))
    ast = parser.parse()
    sa = SemanticAnalyzer(ast)
    sa.analyze()
    return sa, parser


def _error_count(source: str) -> int:
    """Retorna o número de erros semânticos."""
    sa, _ = _analyze(source)
    return len(sa.errors)


def _error_messages(source: str) -> list[str]:
    """Retorna as mensagens dos erros semânticos."""
    sa, _ = _analyze(source)
    return [e.message for e in sa.errors]


# ── SemanticError ───────────────────────────────────────────────────

def test_semantic_error_format():
    e = SemanticError("erro de teste", 42)
    assert e.line == 42
    assert "[SEMÂNTICO]" in str(e)
    assert "linha 42" in str(e)


# ── SymbolTable ─────────────────────────────────────────────────────

def test_symbol_table_declare_and_lookup():
    st = SymbolTable()
    st.declare('luz.sala', 'luz', 1)
    assert st.lookup('luz.sala') == 'luz'
    assert st.lookup('inexistente.x') is None


def test_symbol_table_multiple_entities():
    st = SymbolTable()
    st.declare('luz.sala', 'luz', 1)
    st.declare('switch.tv', 'switch', 2)
    st.declare('sensor.temperatura', 'sensor', 3)
    assert st.lookup('luz.sala') == 'luz'
    assert st.lookup('switch.tv') == 'switch'
    assert st.lookup('sensor.temperatura') == 'sensor'


# ── Scripts válidos (sem erros) ────────────────────────────────────

def test_movimento_example_no_semantic_errors():
    src = (Path(__file__).parent.parent / 'examples' / 'movimento.homi').read_text()
    assert _error_count(src) == 0


def test_horario_example_no_semantic_errors():
    src = (Path(__file__).parent.parent / 'examples' / 'horario.homi').read_text()
    assert _error_count(src) == 0


def test_bateria_example_no_semantic_errors():
    src = (Path(__file__).parent.parent / 'examples' / 'bateria.homi').read_text()
    assert _error_count(src) == 0


# ── ligar/desligar em sensor.* → erro ──────────────────────────────

def test_ligar_sensor_error():
    src = '''
        automacao "test" {
            quando hora = 10:00
            entao { ligar sensor.temperatura }
        }
    '''
    assert _error_count(src) == 1
    msg = _error_messages(src)[0]
    assert 'sensor.temperatura' in msg
    assert 'sensor' in msg


def test_desligar_sensor_error():
    src = '''
        automacao "test" {
            quando hora = 10:00
            entao { desligar sensor.umidade }
        }
    '''
    assert _error_count(src) == 1
    msg = _error_messages(src)[0]
    assert 'sensor.umidade' in msg
    assert 'sensor' in msg


# ── ligar/desligar em binary_sensor.* → erro ───────────────────────

def test_ligar_binary_sensor_error():
    src = '''
        automacao "test" {
            quando hora = 10:00
            entao { ligar binary_sensor.porta }
        }
    '''
    assert _error_count(src) == 1
    msg = _error_messages(src)[0]
    assert 'binary_sensor.porta' in msg


def test_desligar_binary_sensor_error():
    src = '''
        automacao "test" {
            quando hora = 10:00
            entao { desligar binary_sensor.movimento }
        }
    '''
    assert _error_count(src) == 1


# ── trigger de movimento em luz.* → erro ───────────────────────────

def test_trigger_movimento_luz_error():
    src = '''
        automacao "test" {
            quando luz.sala movimento
            entao { ligar luz.sala }
        }
    '''
    assert _error_count(src) == 1
    msg = _error_messages(src)[0]
    assert 'movimento' in msg
    assert 'binary_sensor' in msg
    assert 'luz' in msg


def test_trigger_movimento_switch_error():
    src = '''
        automacao "test" {
            quando switch.tv movimento
            entao { desligar switch.tv }
        }
    '''
    assert _error_count(src) == 1
    msg = _error_messages(src)[0]
    assert 'switch' in msg


# ── trigger de bateria em switch.* → erro ──────────────────────────

def test_trigger_bateria_switch_error():
    src = '''
        automacao "test" {
            quando switch.carregador bateria abaixo 20%
            entao { ligar switch.carregador }
        }
    '''
    assert _error_count(src) == 1
    msg = _error_messages(src)[0]
    assert 'bateria' in msg
    assert 'sensor' in msg
    assert 'switch' in msg


def test_trigger_bateria_luz_error():
    src = '''
        automacao "test" {
            quando luz.sala bateria acima 50
            entao { ligar luz.sala }
        }
    '''
    assert _error_count(src) == 1
    msg = _error_messages(src)[0]
    assert 'luz' in msg


# ── estado armado/desarmado em luz.* → erro ────────────────────────

def test_estado_armado_luz_error():
    src = '''
        automacao "test" {
            quando luz.sala muda para armado
            entao { ligar luz.sala }
        }
    '''
    assert _error_count(src) == 1
    msg = _error_messages(src)[0]
    assert 'armado' in msg
    assert 'alarm_control_panel' in msg


def test_estado_desarmado_luz_error():
    src = '''
        automacao "test" {
            quando luz.sala muda para desarmado
            entao { ligar luz.sala }
        }
    '''
    assert _error_count(src) == 1
    msg = _error_messages(src)[0]
    assert 'desarmado' in msg


def test_estado_armado_switch_error():
    src = '''
        automacao "test" {
            quando switch.tv muda para armado
            entao { desligar switch.tv }
        }
    '''
    assert _error_count(src) == 1


def test_estado_desarmado_sensor_error():
    src = '''
        automacao "test" {
            quando sensor.porta muda para desarmado
            entao { ligar luz.sala }
        }
    '''
    assert _error_count(src) == 1


# ── estado armado/desarmado em condição → erro ─────────────────────

def test_condition_estado_armado_luz_error():
    src = '''
        automacao "test" {
            quando hora = 10:00
            se luz.sala esta armado
            entao { ligar luz.quarto }
        }
    '''
    assert _error_count(src) == 1
    msg = _error_messages(src)[0]
    assert 'armado' in msg


def test_condition_estado_desarmado_switch_error():
    src = '''
        automacao "test" {
            quando hora = 10:00
            se switch.tv esta desarmado
            entao { ligar luz.sala }
        }
    '''
    assert _error_count(src) == 1


# ── Múltiplos erros coletados sem abortar ──────────────────────────

def test_multiple_errors_collected():
    src = '''
        automacao "test" {
            quando sensor.porta movimento
            se luz.sala esta armado
            entao {
                ligar binary_sensor.corredor
                desligar sensor.umidade
            }
        }
    '''
    count = _error_count(src)
    assert count >= 3  # movimento sensor, armado luz, ligar binary_sensor
    msgs = _error_messages(src)
    assert any('movimento' in m for m in msgs)
    assert any('armado' in m for m in msgs)
    assert any('ligado' in m or 'desligado' in m for m in msgs)


def test_analyze_returns_ast():
    src = '''
        automacao "test" {
            quando hora = 10:00
            entao { ligar luz.sala }
        }
    '''
    sa, _ = _analyze(src)
    result = sa.analyze()
    assert len(result.automacoes) == 1


# ── SymbolTable após análise ────────────────────────────────────────

def test_symbol_table_after_analysis():
    src = '''
        automacao "t1" {
            quando binary_sensor.corredor muda para ligado
            se alarm_control_panel.alarmo esta desarmado
            entao {
                ligar luz.corredor
                desligar switch.tv
                notificar "teste"
                esperar 45s
            }
        }
    '''
    sa, _ = _analyze(src)
    st = sa.symbol_table
    assert st.lookup('binary_sensor.corredor') == 'binary_sensor'
    assert st.lookup('alarm_control_panel.alarmo') == 'alarm_control_panel'
    assert st.lookup('luz.corredor') == 'luz'
    assert st.lookup('switch.tv') == 'switch'
    assert st.lookup('inexistente.xyz') is None


# ── action_se valida internos ──────────────────────────────────────

def test_action_se_validates_condition():
    src = '''
        automacao "test" {
            quando hora = 10:00
            entao {
                se luz.sala esta armado entao {
                    ligar luz.quarto
                }
            }
        }
    '''
    assert _error_count(src) == 1  # armado em luz
    msg = _error_messages(src)[0]
    assert 'armado' in msg


def test_action_se_validates_nested_actions():
    src = '''
        automacao "test" {
            quando hora = 10:00
            entao {
                se hora abaixo 18:00 entao {
                    ligar sensor.temperatura
                } senao {
                    desligar binary_sensor.corredor
                }
            }
        }
    '''
    assert _error_count(src) == 2
    msgs = _error_messages(src)
    assert any('sensor.temperatura' in m for m in msgs)
    assert any('binary_sensor.corredor' in m for m in msgs)


def test_action_se_deep_nested():
    src = '''
        automacao "test" {
            quando hora = 10:00
            entao {
                se luz.sala esta ligado entao {
                    se switch.tv esta armado entao {
                        ligar sensor.erro
                    }
                }
            }
        }
    '''
    assert _error_count(src) == 2  # armado switch + ligar sensor


# ── Sem erros com todas as construções ─────────────────────────────

def test_all_actions_valid():
    src = '''
        automacao "completa" {
            quando binary_sensor.corredor muda para ligado
            quando hora = 10:00
            quando binary_sensor.sala movimento
            quando sensor.bateria bateria abaixo 20%
            se alarm_control_panel.alarmo esta desarmado
            se luz.sala esta desligado
            se hora abaixo 23:00
            entao {
                ligar luz.sala
                desligar switch.tv
                esperar 30s
                notificar "ok"
                se luz.sala esta ligado entao {
                    ligar media_player.som
                } senao {
                    desligar media_player.som
                }
            }
        }
    '''
    assert _error_count(src) == 0


# ── Caso: alarm_control_panel com armado/desarmado válido ──────────

def test_alarm_control_panel_armado_valid():
    src = '''
        automacao "test" {
            quando alarm_control_panel.alarmo muda para armado
            entao { ligar luz.sala }
        }
    '''
    assert _error_count(src) == 0


def test_alarm_control_panel_desarmado_valid():
    src = '''
        automacao "test" {
            se alarm_control_panel.alarmo esta desarmado
            entao { ligar luz.sala }
        }
    '''
    p = Parser(tokenize(src))
    ast = p.parse()
    # This will have a parser error because entao without trigger
    # Let's fix the test
    src2 = '''
        automacao "test" {
            quando hora = 10:00
            se alarm_control_panel.alarmo esta desarmado
            entao { ligar luz.sala }
        }
    '''
    assert _error_count(src2) == 0
