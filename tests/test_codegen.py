"""Testes do gerador de código YAML (codegen.py)."""
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from lexer import tokenize
from parser import Parser
from codegen import CodeGenerator


# ── Helpers ─────────────────────────────────────────────────────────

def _generate(source: str) -> list[dict]:
    """Faz lex/parse e codegen, retorna o YAML parseado como lista de dicts."""
    parser = Parser(tokenize(source))
    ast = parser.parse()
    cg = CodeGenerator(ast)
    raw = cg.generate()
    return yaml.safe_load(raw)


def _first(source: str) -> dict:
    """Retorna a primeira automação do YAML gerado."""
    return _generate(source)[0]


# ══════════════════════════════════════════════════════════════════════
# Estrutura geral
# ══════════════════════════════════════════════════════════════════════

def test_output_is_valid_yaml():
    result = _generate('''
        automacao "test" {
            quando hora = 10:00
            entao { ligar luz.sala }
        }
    ''')
    assert isinstance(result, list)
    assert len(result) == 1
    assert 'alias' in result[0]


def test_mode_is_single():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            entao { ligar luz.sala }
        }
    ''')
    assert a.get('mode') == 'single'


def test_alias_correct():
    a = _first('''
        automacao "Nome da Automação" {
            quando hora = 10:00
            entao { ligar luz.sala }
        }
    ''')
    assert a['alias'] == 'Nome da Automação'


def test_multiple_automations():
    result = _generate('''
        automacao "A1" {
            quando hora = 10:00
            entao { ligar luz.sala }
        }
        automacao "A2" {
            quando hora = 20:00
            entao { desligar luz.sala }
        }
    ''')
    assert len(result) == 2
    assert result[0]['alias'] == 'A1'
    assert result[1]['alias'] == 'A2'


# ══════════════════════════════════════════════════════════════════════
# Triggers
# ══════════════════════════════════════════════════════════════════════

def test_trigger_estado_ligado():
    a = _first('''
        automacao "test" {
            quando luz.sala muda para ligado
            entao { ligar luz.sala }
        }
    ''')
    t = a['triggers'][0]
    assert t['trigger'] == 'state'
    assert t['entity_id'] == 'luz.sala'
    assert t['to'] == 'on'


def test_trigger_estado_desligado():
    a = _first('''
        automacao "test" {
            quando luz.sala muda para desligado
            entao { ligar luz.sala }
        }
    ''')
    assert a['triggers'][0]['to'] == 'off'


def test_trigger_estado_armado():
    a = _first('''
        automacao "test" {
            quando alarm_control_panel.alarmo muda para armado
            entao { ligar luz.sala }
        }
    ''')
    assert a['triggers'][0]['to'] == 'armed'


def test_trigger_estado_desarmado():
    a = _first('''
        automacao "test" {
            quando alarm_control_panel.alarmo muda para desarmado
            entao { ligar luz.sala }
        }
    ''')
    assert a['triggers'][0]['to'] == 'disarmed'


def test_trigger_estado_string_literal():
    a = _first('''
        automacao "test" {
            quando sensor.status muda para "online"
            entao { ligar luz.sala }
        }
    ''')
    assert a['triggers'][0]['to'] == 'online'


def test_trigger_hora():
    a = _first('''
        automacao "test" {
            quando hora = 22:30
            entao { ligar luz.sala }
        }
    ''')
    t = a['triggers'][0]
    assert t['trigger'] == 'time'
    assert t['at'] == '22:30:00'


def test_trigger_hora_with_seconds():
    a = _first('''
        automacao "test" {
            quando hora = 05:00:00
            entao { ligar luz.sala }
        }
    ''')
    assert a['triggers'][0]['at'] == '05:00:00'


def test_trigger_hora_normalizes_single_digit():
    a = _first('''
        automacao "test" {
            quando hora = 5:00
            entao { ligar luz.sala }
        }
    ''')
    assert a['triggers'][0]['at'] == '05:00:00'


def test_trigger_movimento():
    a = _first('''
        automacao "test" {
            quando binary_sensor.corredor movimento
            entao { ligar luz.sala }
        }
    ''')
    t = a['triggers'][0]
    assert t['trigger'] == 'state'
    assert t['entity_id'] == 'binary_sensor.corredor'
    assert t['to'] == 'on'


def test_trigger_bateria_abaixo():
    a = _first('''
        automacao "test" {
            quando sensor.bateria bateria abaixo 20%
            entao { ligar luz.sala }
        }
    ''')
    t = a['triggers'][0]
    assert t['trigger'] == 'numeric_state'
    assert t['entity_id'] == 'sensor.bateria'
    assert t['attribute'] == 'battery_level'
    assert t['below'] == 20
    assert 'above' not in t


def test_trigger_bateria_acima():
    a = _first('''
        automacao "test" {
            quando sensor.bateria bateria acima 30
            entao { ligar luz.sala }
        }
    ''')
    t = a['triggers'][0]
    assert t['above'] == 30
    assert 'below' not in t


# ══════════════════════════════════════════════════════════════════════
# Conditions
# ══════════════════════════════════════════════════════════════════════

def test_condition_estado():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            se alarm_control_panel.alarmo esta desarmado
            entao { ligar luz.sala }
        }
    ''')
    c = a['conditions'][0]
    assert c['condition'] == 'state'
    assert c['entity_id'] == 'alarm_control_panel.alarmo'
    assert c['state'] == 'disarmed'


def test_condition_estado_ligado():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            se luz.sala esta ligado
            entao { ligar luz.sala }
        }
    ''')
    assert a['conditions'][0]['state'] == 'on'


def test_condition_estado_string():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            se sensor.status esta "ok"
            entao { ligar luz.sala }
        }
    ''')
    assert a['conditions'][0]['state'] == 'ok'


def test_condition_hora_abaixo():
    a = _first('''
        automacao "test" {
            quando binary_sensor.corredor movimento
            se hora abaixo 23:00
            entao { ligar luz.sala }
        }
    ''')
    c = a['conditions'][0]
    assert c['condition'] == 'time'
    assert c['before'] == '23:00:00'
    assert 'after' not in c


def test_condition_hora_acima():
    a = _first('''
        automacao "test" {
            quando binary_sensor.corredor movimento
            se hora acima 06:00:00
            entao { ligar luz.sala }
        }
    ''')
    c = a['conditions'][0]
    assert c['condition'] == 'time'
    assert c['after'] == '06:00:00'
    assert 'before' not in c


# ══════════════════════════════════════════════════════════════════════
# Actions
# ══════════════════════════════════════════════════════════════════════

def test_action_ligar_luz():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            entao { ligar luz.sala }
        }
    ''')
    act = a['actions'][0]
    assert act['action'] == 'light.turn_on'
    assert act['target']['entity_id'] == 'luz.sala'


def test_action_desligar_luz():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            entao { desligar luz.sala }
        }
    ''')
    act = a['actions'][0]
    assert act['action'] == 'light.turn_off'
    assert act['target']['entity_id'] == 'luz.sala'


def test_action_ligar_switch():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            entao { ligar switch.tv }
        }
    ''')
    act = a['actions'][0]
    assert act['action'] == 'switch.turn_on'
    assert act['target']['entity_id'] == 'switch.tv'


def test_action_desligar_switch():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            entao { desligar switch.tv }
        }
    ''')
    act = a['actions'][0]
    assert act['action'] == 'switch.turn_off'


def test_action_ligar_media_player():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            entao { ligar media_player.som }
        }
    ''')
    act = a['actions'][0]
    assert act['action'] == 'media_player.turn_on'


def test_action_desligar_media_player():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            entao { desligar media_player.som }
        }
    ''')
    act = a['actions'][0]
    assert act['action'] == 'media_player.turn_off'


# ── ActionEsperar ──────────────────────────────────────────────────

def test_action_esperar_seconds():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            entao { esperar 45s }
        }
    ''')
    delay = a['actions'][0]['delay']
    assert delay['seconds'] == 45


def test_action_esperar_minutes_min():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            entao { esperar 5min }
        }
    ''')
    delay = a['actions'][0]['delay']
    assert delay['minutes'] == 5


def test_action_esperar_minutes_m():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            entao { esperar 10m }
        }
    ''')
    delay = a['actions'][0]['delay']
    assert delay['minutes'] == 10


def test_action_esperar_hours():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            entao { esperar 2h }
        }
    ''')
    delay = a['actions'][0]['delay']
    assert delay['hours'] == 2


# ── ActionNotificar ────────────────────────────────────────────────

def test_action_notificar():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            entao { notificar "Mensagem de teste" }
        }
    ''')
    act = a['actions'][0]
    assert act['action'] == 'notify.mobile_app'
    assert act['data']['message'] == 'Mensagem de teste'


# ── ActionSe ───────────────────────────────────────────────────────

def test_action_se_without_senao():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            entao {
                se luz.sala esta ligado entao {
                    desligar luz.sala
                }
            }
        }
    ''')
    choose = a['actions'][0]['choose']
    assert len(choose) == 1
    assert choose[0]['conditions'][0]['condition'] == 'state'
    assert choose[0]['conditions'][0]['entity_id'] == 'luz.sala'
    assert len(choose[0]['sequence']) == 1


def test_action_se_with_senao():
    a = _first('''
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
    choose = a['actions'][0]['choose']
    assert len(choose) == 2
    # Segundo bloco é o senao (conditions vazio)
    assert choose[1]['conditions'] == []
    assert len(choose[1]['sequence']) == 1


def test_action_se_time_condition():
    a = _first('''
        automacao "test" {
            quando hora = 10:00
            entao {
                se hora abaixo 18:00 entao {
                    ligar luz.sala
                } senao {
                    desligar luz.sala
                }
            }
        }
    ''')
    choose = a['actions'][0]['choose']
    assert choose[0]['conditions'][0]['condition'] == 'time'
    assert choose[0]['conditions'][0]['before'] == '18:00:00'


# ══════════════════════════════════════════════════════════════════════
# Scripts de exemplo
# ══════════════════════════════════════════════════════════════════════

def test_movimento_example_parses():
    src = (Path(__file__).parent.parent / 'examples' / 'movimento.homi').read_text()
    result = _generate(src)
    assert len(result) == 1
    a = result[0]
    assert a['alias'] == 'Corredor - movimento'
    assert len(a['triggers']) == 1
    assert len(a['conditions']) == 2
    assert len(a['actions']) == 3


def test_horario_example_parses():
    src = (Path(__file__).parent.parent / 'examples' / 'horario.homi').read_text()
    result = _generate(src)
    a = result[0]
    assert a['triggers'][0]['trigger'] == 'time'
    assert len(a['actions']) == 3


def test_bateria_example_parses():
    src = (Path(__file__).parent.parent / 'examples' / 'bateria.homi').read_text()
    result = _generate(src)
    a = result[0]
    assert a['triggers'][0]['trigger'] == 'numeric_state'
    assert a['triggers'][0]['below'] == 20
    assert a['actions'][0]['action'] == 'switch.turn_on'
    assert a['actions'][1]['data']['message'] == 'Tablet carregando'


# ══════════════════════════════════════════════════════════════════════
# Caso completo
# ══════════════════════════════════════════════════════════════════════

def test_full_automation():
    result = _generate('''
        automacao "Completa" {
            quando binary_sensor.corredor muda para ligado
            quando hora = 22:00
            se alarm_control_panel.alarmo esta desarmado
            se luz.sala esta desligado
            entao {
                ligar luz.sala
                esperar 30s
                desligar luz.sala
                se hora abaixo 23:00 entao {
                    notificar "ainda cedo"
                } senao {
                    notificar "tarde"
                }
            }
        }
    ''')
    a = result[0]

    # Triggers
    assert a['triggers'][0]['trigger'] == 'state'
    assert a['triggers'][0]['to'] == 'on'
    assert a['triggers'][1]['trigger'] == 'time'
    assert a['triggers'][1]['at'] == '22:00:00'

    # Conditions
    assert a['conditions'][0]['state'] == 'disarmed'
    assert a['conditions'][1]['state'] == 'off'

    # Actions
    assert a['actions'][0]['action'] == 'light.turn_on'
    assert a['actions'][1]['delay']['seconds'] == 30
    assert a['actions'][2]['action'] == 'light.turn_off'
    choose = a['actions'][3]['choose']
    assert len(choose) == 2
    assert choose[1]['sequence'][0]['data']['message'] == 'tarde'


# ══════════════════════════════════════════════════════════════════════
# PyYAML round-trip
# ══════════════════════════════════════════════════════════════════════

def test_output_is_roundtrippable():
    """O YAML gerado pode ser parseado novamente pelo PyYAML."""
    src = '''
        automacao "test" {
            quando binary_sensor.corredor muda para ligado
            quando hora = 05:00
            quando binary_sensor.sala movimento
            quando sensor.bateria bateria abaixo 20%
            se alarm_control_panel.alarmo esta desarmado
            se luz.sala esta desligado
            se hora abaixo 23:00
            entao {
                ligar luz.sala
                desligar switch.tv
                esperar 45s
                notificar "teste"
                se luz.sala esta ligado entao {
                    ligar media_player.som
                } senao {
                    desligar media_player.som
                }
            }
        }
    '''
    parser = Parser(tokenize(src))
    ast = parser.parse()
    cg = CodeGenerator(ast)
    raw = cg.generate()

    parsed = yaml.safe_load(raw)
    assert isinstance(parsed, list)
    assert len(parsed) == 1


# ── CLOCK_TIME com single-digit seconds ──────────────────────────

def test_clock_time_single_digit_seconds():
    a = _first('''
        automacao "test" {
            quando hora = 5:00:00
            entao { ligar luz.sala }
        }
    ''')
    assert a['triggers'][0]['at'] == '05:00:00'
