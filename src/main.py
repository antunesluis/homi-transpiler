"""
Entry point do compilador Homi.

CLI:
    python src/main.py <arquivo.homi>               # emite YAML no stdout
    python src/main.py <arquivo.homi> --output <f>  # salva YAML em arquivo
    python src/main.py <arquivo.homi> --check        # só valida, não emite YAML

API programática:
    compile_homi(source) → tuple[str | None, list[str]]
"""

import sys
from pathlib import Path

# Adiciona src/ ao path para importar módulos irmãos
sys.path.insert(0, str(Path(__file__).parent))

from lexer import tokenize, LexError
from parser import Parser, ParseError
from semantic import SemanticAnalyzer, SemanticError
from codegen import CodeGenerator


def compile_homi(source: str) -> tuple[str | None, list[str]]:
    """
    Compila código-fonte Homi e retorna YAML e lista de erros.

    Args:
        source: String contendo o código-fonte .homi.

    Returns:
        Tuple (yaml_string, lista_de_erros).
        yaml_string é None se houver erros léxicos ou sintáticos.
        Se houver apenas erros semânticos, o YAML ainda é retornado.
        lista_de_erros contém strings formatadas '[FASE] linha N: mensagem'.
    """
    errors: list[str] = []

    # ── 1. Análise Léxica ──────────────────────────────────────────
    try:
        tokens = tokenize(source)
    except LexError as e:
        errors.append(f"[LÉXICO]    linha {e.line}: {e.message}")
        return None, errors

    # ── 2. Análise Sintática ───────────────────────────────────────
    parser = Parser(tokens)
    ast = parser.parse()

    for err in parser.errors:
        errors.append(
            f"[SINTÁTICO] linha {err.line}: {err.message}"
        )

    if parser.errors:
        return None, errors

    # ── 3. Análise Semântica ───────────────────────────────────────
    analyzer = SemanticAnalyzer(ast)
    analyzer.analyze()

    for err in analyzer.errors:
        errors.append(
            f"[SEMÂNTICO] linha {err.line}: {err.message}"
        )

    # ── 4. Geração de Código ───────────────────────────────────────
    yaml_output = CodeGenerator(ast).generate()

    return yaml_output, errors


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

def _parse_args(argv: list[str]) -> tuple[str, str | None, bool]:
    """
    Analisa argumentos da linha de comando.

    Returns:
        (input_path, output_path | None, check_only)
    """
    if len(argv) < 2:
        print("Uso: python src/main.py <arquivo.homi> [--output <saida.yaml>] [--check]",
              file=sys.stderr)
        sys.exit(1)

    input_path = argv[1]
    output_path = None
    check_only = False

    i = 2
    while i < len(argv):
        if argv[i] == '--output':
            if i + 1 < len(argv):
                output_path = argv[i + 1]
                i += 2
            else:
                print("Erro: --output requer um caminho de arquivo.",
                      file=sys.stderr)
                sys.exit(1)
        elif argv[i] == '--check':
            check_only = True
            i += 1
        else:
            print(f"Erro: argumento desconhecido '{argv[i]}'.", file=sys.stderr)
            sys.exit(1)

    return input_path, output_path, check_only


def main():
    """Entry point da CLI. Lê arquivo, compila, exibe resultado."""
    input_path, output_path, check_only = _parse_args(sys.argv)

    # Verifica se o arquivo existe
    if not Path(input_path).is_file():
        print(f"Erro: arquivo '{input_path}' não encontrado.", file=sys.stderr)
        sys.exit(1)

    # Lê o arquivo fonte
    source = Path(input_path).read_text(encoding='utf-8')

    # Compila
    yaml_output, errors = compile_homi(source)

    # Exibe erros no stderr
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        # Se há erros fatais (léxicos ou sintáticos), YAML é None
        if yaml_output is None:
            sys.exit(1)

    # Exibe YAML
    if check_only:
        if output_path is not None:
            print("Aviso: --check ignora --output", file=sys.stderr)
    elif yaml_output is not None:
        if output_path:
            Path(output_path).write_text(yaml_output, encoding='utf-8')
        else:
            # Remove última quebra de linha extra do yaml.dump para
            # manter a saída limpa, sem linha vazia final indesejada
            out = yaml_output.rstrip('\n')
            print(out)

    sys.exit(0 if not errors else 1)


if __name__ == '__main__':
    main()
