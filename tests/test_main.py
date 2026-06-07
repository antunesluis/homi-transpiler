"""Testes do entry point (main.py)."""
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from main import compile_homi

_EXAMPLES = Path(__file__).parent.parent / 'examples' / 'valid'
_MAIN = Path(__file__).parent.parent / 'src' / 'main.py'
_PYTHON = Path(sys.executable)


# ── compile_homi ────────────────────────────────────────────────────

def test_compile_valid_script():
    yaml_str, errors = compile_homi('''
        automacao "test" {
            quando hora = 10:00
            entao { ligar luz.sala }
        }
    ''')
    assert yaml_str is not None
    assert errors == []
    yaml.safe_load(yaml_str)


def test_compile_returns_yaml_none_on_lex_error():
    yaml_str, errors = compile_homi('@')
    assert yaml_str is None
    assert len(errors) == 1
    assert '[LÉXICO]' in errors[0]


def test_compile_returns_yaml_none_on_syntax_error():
    yaml_str, errors = compile_homi('''
        automacao "test" {
            quando xyz
            entao { ligar luz.sala }
        }
    ''')
    assert yaml_str is None
    assert len(errors) >= 1
    assert any('[SINTÁTICO]' in e for e in errors)


def test_compile_returns_yaml_on_semantic_error():
    yaml_str, errors = compile_homi('''
        automacao "test" {
            quando hora = 10:00
            entao { ligar sensor.temperatura }
        }
    ''')
    assert yaml_str is not None
    assert len(errors) >= 1
    assert any('[SEMÂNTICO]' in e for e in errors)
    yaml.safe_load(yaml_str)


def test_compile_multiple_errors_collected():
    yaml_str, errors = compile_homi('''
        automacao "test" {
            quando sensor.porta movimento
            se luz.sala esta armado
            entao {
                ligar binary_sensor.corredor
                desligar sensor.umidade
            }
        }
    ''')
    assert yaml_str is not None
    assert len(errors) >= 3


def test_compile_error_format():
    _, errors = compile_homi('@')
    err = errors[0]
    assert err.startswith('[LÉXICO]')
    assert 'linha' in err


# ── compile_homi com scripts de exemplo ─────────────────────────────

def test_compile_movimento():
    src = (_EXAMPLES / 'movimento.homi').read_text()
    yaml_str, errors = compile_homi(src)
    assert errors == []
    assert yaml_str is not None
    data = yaml.safe_load(yaml_str)
    assert len(data) == 1
    assert data[0]['alias'] == 'Corredor - movimento'


def test_compile_horario():
    src = (_EXAMPLES / 'horario.homi').read_text()
    yaml_str, errors = compile_homi(src)
    assert errors == []
    assert yaml_str is not None


def test_compile_bateria():
    src = (_EXAMPLES / 'bateria.homi').read_text()
    yaml_str, errors = compile_homi(src)
    assert errors == []
    assert yaml_str is not None


# ── YAML gerado é parseável por PyYAML ──────────────────────────────

def test_yaml_output_is_valid():
    src = '''
        automacao "test" {
            quando binary_sensor.corredor muda para ligado
            quando hora = 05:00
            se alarm_control_panel.alarmo esta desarmado
            se hora abaixo 23:00
            entao {
                ligar luz.sala
                desligar switch.tv
                esperar 30s
                notificar "teste"
                se luz.sala esta ligado entao {
                    ligar media_player.som
                } senao {
                    desligar media_player.som
                }
            }
        }
    '''
    yaml_str, errors = compile_homi(src)
    assert errors == []
    parsed = yaml.safe_load(yaml_str)
    assert isinstance(parsed, list)
    assert len(parsed) == 1


# ── CLI: exit codes ─────────────────────────────────────────────────

def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_PYTHON, str(_MAIN), *args],
        capture_output=True,
        text=True,
    )


def test_cli_exit_0_valid_script():
    result = run_cli(str(_EXAMPLES / 'movimento.homi'))
    assert result.returncode == 0
    assert 'alias: Corredor' in result.stdout


def test_cli_exit_1_nonexistent_file():
    result = run_cli('nao_existe.homi')
    assert result.returncode == 1
    assert 'não encontrado' in result.stderr


def test_cli_exit_1_syntax_error():
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.homi', delete=False
    ) as f:
        f.write('automacao "test" {\n    quando hora = 10:00\n'
                '    entao {\n        invalid_token xyz\n    }\n}\n')
        tmp_path = f.name
    try:
        result = run_cli(tmp_path)
        assert result.returncode == 1
        assert '[SINTÁTICO]' in result.stderr
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_cli_exit_1_semantic_error():
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.homi', delete=False
    ) as f:
        f.write('automacao "test" {\n    quando luz.sala movimento\n'
                '    entao {\n        ligar sensor.temperatura\n    }\n}\n')
        tmp_path = f.name
    try:
        result = run_cli(tmp_path)
        assert result.returncode == 1
        assert '[SEMÂNTICO]' in result.stderr
        assert 'alias' in result.stdout
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_cli_errors_on_stderr_only():
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.homi', delete=False
    ) as f:
        f.write('automacao "test" {\n    quando luz.sala movimento\n'
                '    entao {\n        ligar sensor.temperatura\n    }\n}\n')
        tmp_path = f.name
    try:
        result = run_cli(tmp_path)
        assert '[SEMÂNTICO]' in result.stderr
        assert '[SEMÂNTICO]' not in result.stdout
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_cli_yaml_on_stdout_only():
    result = run_cli(str(_EXAMPLES / 'movimento.homi'))
    assert 'alias:' in result.stdout
    assert result.stderr == ''


def test_cli_check_flag_no_output():
    result = run_cli(str(_EXAMPLES / 'movimento.homi'), '--check')
    assert result.returncode == 0
    assert result.stdout == ''


def test_cli_output_flag():
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
        out_path = f.name
    try:
        result = run_cli(str(_EXAMPLES / 'movimento.homi'), '--output', out_path)
        assert result.returncode == 0
        content = Path(out_path).read_text()
        assert 'alias: Corredor' in content
    finally:
        Path(out_path).unlink(missing_ok=True)


# ── CLI: erro léxico ────────────────────────────────────────────────

def test_cli_exit_1_lex_error():
    # Criar arquivo com erro léxico
    import tempfile
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.homi', delete=False
    ) as f:
        f.write('automacao "test" { @ }')
        tmp_path = f.name
    try:
        result = run_cli(tmp_path)
        assert result.returncode == 1
        assert '[LÉXICO]' in result.stderr
    finally:
        Path(tmp_path).unlink(missing_ok=True)
