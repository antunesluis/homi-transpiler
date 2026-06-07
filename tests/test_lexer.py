"""
Testes do analisador léxico (lexer.py).
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from lexer import Token, LexError, tokenize


# ── Helpers ─────────────────────────────────────────────────────────

def _types(tokens: list[Token]) -> list[str]:
    """Extrai apenas os tipos de uma lista de tokens (sem EOF)."""
    return [t.type for t in tokens if t.type != 'EOF']


def _values(tokens: list[Token]) -> list[str]:
    """Extrai apenas os valores de uma lista de tokens (sem EOF)."""
    return [t.value for t in tokens if t.type != 'EOF']


def _lines(tokens: list[Token]) -> list[int]:
    """Extrai apenas as linhas de uma lista de tokens (sem EOF)."""
    return [t.line for t in tokens if t.type != 'EOF']


# ── Token e LexError ────────────────────────────────────────────────

def test_token_creation():
    t = Token('KW_LIGAR', 'ligar', 3)
    assert t.type == 'KW_LIGAR'
    assert t.value == 'ligar'
    assert t.line == 3


def test_lexerror_creation():
    e = LexError("caractere inválido '@'", 5)
    assert e.message == "caractere inválido '@'"
    assert e.line == 5
    assert "linha 5" in str(e)


# ── EOF ─────────────────────────────────────────────────────────────

def test_empty_input_returns_eof():
    tokens = tokenize('')
    assert len(tokens) == 1
    assert tokens[0].type == 'EOF'
    assert tokens[0].value == ''


def test_eof_always_last():
    tokens = tokenize('ligar')
    assert tokens[-1].type == 'EOF'


# ── Símbolos ────────────────────────────────────────────────────────

def test_symbols():
    tokens = tokenize('{ } ; =')
    assert _types(tokens) == ['LBRACE', 'RBRACE', 'SEMICOLON', 'EQUALS']
    assert _values(tokens) == ['{', '}', ';', '=']


# ── Palavras-chave ──────────────────────────────────────────────────

@pytest.mark.parametrize('source,expected_type', [
    ('automacao', 'KW_AUTOMACAO'),
    ('quando',    'KW_QUANDO'),
    ('se',        'KW_SE'),
    ('entao',     'KW_ENTAO'),
    ('senao',     'KW_SENAO'),
    ('ligar',     'KW_LIGAR'),
    ('desligar',  'KW_DESLIGAR'),
    ('esperar',   'KW_ESPERAR'),
    ('notificar', 'KW_NOTIFICAR'),
    ('muda',      'KW_MUDA'),
    ('para',      'KW_PARA'),
    ('hora',      'KW_HORA'),
    ('esta',      'KW_ESTA'),
    ('ligado',    'KW_LIGADO'),
    ('desligado', 'KW_DESLIGADO'),
    ('armado',    'KW_ARMADO'),
    ('desarmado', 'KW_DESARMADO'),
    ('movimento', 'KW_MOVIMENTO'),
    ('bateria',   'KW_BATERIA'),
    ('abaixo',    'KW_ABAIXO'),
    ('acima',     'KW_ACIMA'),
])
def test_keywords(source, expected_type):
    tokens = tokenize(source)
    assert _types(tokens) == [expected_type]
    assert _values(tokens) == [source]


# ── ENTITY_ID vs palavra-chave ──────────────────────────────────────

def test_entity_id_basic():
    tokens = tokenize('luz.sala')
    assert _types(tokens) == ['ENTITY_ID']
    assert _values(tokens) == ['luz.sala']


def test_entity_id_with_underscores():
    tokens = tokenize('binary_sensor.corredor_suite_motion')
    assert _types(tokens) == ['ENTITY_ID']
    assert _values(tokens) == ['binary_sensor.corredor_suite_motion']


def test_entity_id_not_keyword():
    """'luz' não é palavra-chave, 'luz.sala' deve ser ENTITY_ID."""
    tokens = tokenize('luz.sala')
    assert len([t for t in tokens if t.type != 'EOF']) == 1
    assert tokens[0].type == 'ENTITY_ID'


def test_entity_id_after_keyword():
    """Keyword seguida de ENTITY_ID: cada um token próprio."""
    tokens = tokenize('ligar luz.sala')
    assert _types(tokens) == ['KW_LIGAR', 'ENTITY_ID']
    assert _values(tokens) == ['ligar', 'luz.sala']


def test_entity_id_invalid_no_part_after_dot():
    with pytest.raises(LexError, match="entity_id"):
        tokenize('luz.')


def test_entity_id_invalid_dot_with_number():
    with pytest.raises(LexError, match="entity_id"):
        tokenize('luz.123')


# ── STRING ──────────────────────────────────────────────────────────

def test_string_simple():
    tokens = tokenize('"olá"')
    assert _types(tokens) == ['STRING']
    assert _values(tokens) == ['"olá"']


def test_string_empty():
    tokens = tokenize('""')
    assert _types(tokens) == ['STRING']
    assert _values(tokens) == ['""']


def test_string_with_spaces():
    tokens = tokenize('"Corredor - movimento"')
    assert _types(tokens) == ['STRING']
    assert _values(tokens) == ['"Corredor - movimento"']


def test_string_unclosed_raises_error():
    with pytest.raises(LexError, match="string não fechada"):
        tokenize('"inicio')


def test_string_line_tracks_start_line():
    tokens = tokenize('a\n"hello"\nb')
    string_tokens = [t for t in tokens if t.type == 'STRING']
    assert len(string_tokens) == 1
    assert string_tokens[0].line == 2


# ── CLOCK_TIME ──────────────────────────────────────────────────────

def test_clock_time_hh_mm():
    tokens = tokenize('22:30')
    assert _types(tokens) == ['CLOCK_TIME']
    assert _values(tokens) == ['22:30']


def test_clock_time_hh_mm_ss():
    tokens = tokenize('05:00:00')
    assert _types(tokens) == ['CLOCK_TIME']
    assert _values(tokens) == ['05:00:00']


def test_clock_time_single_digit_hour():
    tokens = tokenize('5:00')
    assert _types(tokens) == ['CLOCK_TIME']


def test_clock_time_is_single_token_not_numbers():
    """22:30 não deve ser tokenizado como NUMBER + ':' + NUMBER."""
    tokens = tokenize('22:30')
    non_eof = [t for t in tokens if t.type != 'EOF']
    assert len(non_eof) == 1
    assert non_eof[0].type == 'CLOCK_TIME'


def test_clock_time_invalid_no_digits_after_colon():
    with pytest.raises(LexError, match="horário"):
        tokenize('22:')


def test_clock_time_invalid_letters_after_colon():
    with pytest.raises(LexError, match="horário"):
        tokenize('22:ab')


# ── TIME_UNIT ───────────────────────────────────────────────────────

def test_time_unit_seconds():
    tokens = tokenize('45s')
    assert _types(tokens) == ['TIME_UNIT']
    assert _values(tokens) == ['45s']


def test_time_unit_minutes_min():
    tokens = tokenize('5min')
    assert _types(tokens) == ['TIME_UNIT']
    assert _values(tokens) == ['5min']


def test_time_unit_minutes_m():
    tokens = tokenize('10m')
    assert _types(tokens) == ['TIME_UNIT']
    assert _values(tokens) == ['10m']


def test_time_unit_hours():
    tokens = tokenize('2h')
    assert _types(tokens) == ['TIME_UNIT']
    assert _values(tokens) == ['2h']


def test_time_unit_is_single_token():
    """45s é um token único, não NUMBER + IDENTIFIER."""
    tokens = tokenize('45s')
    non_eof = [t for t in tokens if t.type != 'EOF']
    assert len(non_eof) == 1
    assert non_eof[0].type == 'TIME_UNIT'


def test_time_unit_min_precedence():
    """'5min' deve ser TIME_UNIT('5min'), não TIME_UNIT('5m') + IDENTIFIER('in')."""
    tokens = tokenize('5min')
    assert _types(tokens) == ['TIME_UNIT']
    assert _values(tokens) == ['5min']


# ── PERCENT ─────────────────────────────────────────────────────────

def test_percent():
    tokens = tokenize('20%')
    assert _types(tokens) == ['PERCENT']
    assert _values(tokens) == ['20%']


def test_percent_is_single_token():
    tokens = tokenize('20%')
    non_eof = [t for t in tokens if t.type != 'EOF']
    assert len(non_eof) == 1
    assert non_eof[0].type == 'PERCENT'


# ── NUMBER ──────────────────────────────────────────────────────────

def test_number_simple():
    tokens = tokenize('42')
    assert _types(tokens) == ['NUMBER']
    assert _values(tokens) == ['42']


def test_number_multiple():
    tokens = tokenize('1000')
    assert _types(tokens) == ['NUMBER']
    assert _values(tokens) == ['1000']


def test_number_not_confused_with_time():
    """Dígitos seguidos de letra que não é sufixo: NUMBER + IDENTIFIER."""
    tokens = tokenize('5x')
    assert _types(tokens) == ['NUMBER', 'IDENTIFIER']
    assert _values(tokens) == ['5', 'x']


# ── Identificadores ─────────────────────────────────────────────────

def test_identifier_simple():
    tokens = tokenize('variavel')
    assert _types(tokens) == ['IDENTIFIER']
    assert _values(tokens) == ['variavel']


def test_identifier_with_underscore():
    tokens = tokenize('_private')
    assert _types(tokens) == ['IDENTIFIER']


# ── Comentários ─────────────────────────────────────────────────────

def test_comment_ignored():
    tokens = tokenize('# este é um comentário\nligar')
    assert _types(tokens) == ['KW_LIGAR']
    assert _values(tokens) == ['ligar']


def test_comment_at_end_of_file():
    tokens = tokenize('ligar # acender luz')
    assert _types(tokens) == ['KW_LIGAR']


def test_comment_whole_line():
    tokens = tokenize('# apenas comentário\n')
    assert len([t for t in tokens if t.type != 'EOF']) == 0


# ── Whitespace ──────────────────────────────────────────────────────

def test_whitespace_ignored():
    tokens = tokenize('  ligar\t\n  desligar  ')
    assert _types(tokens) == ['KW_LIGAR', 'KW_DESLIGAR']


# ── Contagem de linhas ──────────────────────────────────────────────

def test_line_count_single_line():
    tokens = tokenize('ligar desligar')
    assert all(t.line == 1 for t in tokens if t.type == 'KW_LIGAR'
               or t.type == 'KW_DESLIGAR')


def test_line_count_multiple_lines():
    src = 'automacao\nquando\nse\nentao'
    tokens = tokenize(src)
    types = [t.type for t in tokens if t.type != 'EOF']
    lines = [t.line for t in tokens if t.type != 'EOF']
    assert types == ['KW_AUTOMACAO', 'KW_QUANDO', 'KW_SE', 'KW_ENTAO']
    assert lines == [1, 2, 3, 4]


def test_line_count_with_comments():
    src = '# comentário\nligar\n# outro\ndesligar'
    tokens = tokenize(src)
    types = [t.type for t in tokens if t.type != 'EOF']
    lines = [t.line for t in tokens if t.type != 'EOF']
    assert types == ['KW_LIGAR', 'KW_DESLIGAR']
    assert lines == [2, 4]


# ── LexError ────────────────────────────────────────────────────────

def test_lexerror_invalid_char():
    with pytest.raises(LexError, match="caractere inválido"):
        tokenize('@')


def test_lexerror_invalid_char_dollar():
    with pytest.raises(LexError, match="caractere inválido"):
        tokenize('$')


def test_lexerror_invalid_char_reports_line():
    src = 'ligar\n@\ndesligar'
    with pytest.raises(LexError) as exc_info:
        tokenize(src)
    assert exc_info.value.line == 2


# ── Script completo: movimento.homi ─────────────────────────────────

def test_full_movimento_script():
    src = '''# Liga luz do corredor ao detectar movimento
automacao "Corredor - movimento" {
    quando binary_sensor.corredor_suite muda para ligado
    se alarm_control_panel.alarmo esta desarmado
    se luz.corda_led_corredor esta desligado
    entao {
        ligar luz.corda_led_corredor
        esperar 45s
        desligar luz.corda_led_corredor
    }
}
'''
    tokens = tokenize(src)
    types = _types(tokens)
    expected = [
        'KW_AUTOMACAO', 'STRING', 'LBRACE',
        'KW_QUANDO', 'ENTITY_ID', 'KW_MUDA', 'KW_PARA', 'KW_LIGADO',
        'KW_SE', 'ENTITY_ID', 'KW_ESTA', 'KW_DESARMADO',
        'KW_SE', 'ENTITY_ID', 'KW_ESTA', 'KW_DESLIGADO',
        'KW_ENTAO', 'LBRACE',
        'KW_LIGAR', 'ENTITY_ID',
        'KW_ESPERAR', 'TIME_UNIT',
        'KW_DESLIGAR', 'ENTITY_ID',
        'RBRACE',
        'RBRACE',
    ]
    assert types == expected


# ── Script horario.homi ─────────────────────────────────────────────

def test_horario_script():
    src = '''# Desliga tudo na sala por horário
automacao "Sala - desligar tudo" {
    quando hora = 05:00
    entao {
        desligar switch.luzes_da_sala
        desligar switch.luzes_da_cozinha
        desligar switch.luzes_do_lavabo
    }
}
'''
    types = _types(tokenize(src))
    assert 'CLOCK_TIME' in types
    assert types[types.index('EQUALS') + 1] == 'CLOCK_TIME'


# ── Script bateria.homi ─────────────────────────────────────────────

def test_bateria_script():
    src = '''# Controla carregamento do tablet pela bateria
automacao "Tablet - carregador" {
    quando sensor.bateria_tablet bateria abaixo 20%
    entao {
        ligar switch.carregador_tablet
        notificar "Tablet carregando"
    }
}
'''
    types = _types(tokenize(src))
    assert 'KW_BATERIA' in types
    assert 'KW_ABAIXO' in types
    assert 'PERCENT' in types
    assert 'KW_NOTIFICAR' in types
    assert 'STRING' in types


# ── String com escape ─────────────────────────────────────────────

def test_string_with_backslash_escape():
    """Strings com \\\" são reconhecidas como um único token."""
    tokens = tokenize(r'"hello \"world\""')
    assert _types(tokens) == ['STRING']
    assert '\\' in tokens[0].value  # escape preservado no lexema


def test_string_with_multiple_escapes():
    tokens = tokenize(r'"a\\b\"c"')
    assert _types(tokens) == ['STRING']
