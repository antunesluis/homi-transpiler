"""
Analisador Léxico (Scanner) da linguagem Homi.

Implementa um DFA manual (sem bibliotecas de parsing) que converte
o código-fonte .homi em uma lista de tokens.

Cada token é uma instância de Token(type, value, line) onde:
  - type  : string constante (ex: "KW_QUANDO", "ENTITY_ID", "STRING")
  - value : lexema original (ex: "ligar", "luz.sala", '"olá"')
  - line  : número da linha (1-indexed)

A função principal é tokenize(source) que retorna list[Token]
com um Token("EOF", "", last_line) ao final.
"""

from dataclasses import dataclass


@dataclass
class Token:
    """
    Representa um token léxico.

    Attributes:
        type: Tipo do token (ex: "KW_QUANDO", "ENTITY_ID", "NUMBER").
        value: Lexema original do código-fonte.
        line: Número da linha onde o token se inicia (1-indexed).
    """
    type: str
    value: str
    line: int


class LexError(Exception):
    """
    Erro léxico levantado ao encontrar caractere inválido.

    Attributes:
        message: Descrição do erro.
        line: Linha onde o erro ocorreu (1-indexed).
    """
    def __init__(self, message: str, line: int):
        self.message = message
        self.line = line
        super().__init__(f"linha {line}: {message}")


# Mapeamento de palavras reservadas → tipo de token
_KEYWORDS: dict[str, str] = {
    'automacao': 'KW_AUTOMACAO',
    'quando':    'KW_QUANDO',
    'se':        'KW_SE',
    'entao':     'KW_ENTAO',
    'senao':     'KW_SENAO',
    'ligar':     'KW_LIGAR',
    'desligar':  'KW_DESLIGAR',
    'esperar':   'KW_ESPERAR',
    'notificar': 'KW_NOTIFICAR',
    'muda':      'KW_MUDA',
    'para':      'KW_PARA',
    'hora':      'KW_HORA',
    'esta':      'KW_ESTA',
    'ligado':    'KW_LIGADO',
    'desligado': 'KW_DESLIGADO',
    'armado':    'KW_ARMADO',
    'desarmado': 'KW_DESARMADO',
    'movimento': 'KW_MOVIMENTO',
    'bateria':   'KW_BATERIA',
    'abaixo':    'KW_ABAIXO',
    'acima':     'KW_ACIMA',
    'de':        'KW_DE',
    'e':         'KW_E',
    'ou':        'KW_OU',
}


def tokenize(source: str) -> list[Token]:
    """
    Converte código-fonte Homi em uma lista de tokens.

    A ordem de reconhecimento é determinística e resolve ambiguidades:
      1. Whitespace e comentários → ignorados
      2. Strings ("...")
      3. CLOCK_TIME  — antes de NUMBER (ex: "22:30")
      4. TIME_UNIT   — antes de NUMBER (ex: "45s", "5min")
      5. PERCENT     — antes de NUMBER (ex: "20%")
      6. NUMBER      — dígitos isolados
      7. Palavras    — keyword, ENTITY_ID ou identificador simples
      8. Símbolos    — { } ; =

    Args:
        source: String contendo o código-fonte .homi.

    Returns:
        Lista de Token, com EOF ao final.

    Raises:
        LexError: Em caractere inválido ou string não fechada.
    """
    tokens: list[Token] = []
    i = 0
    line = 1
    n = len(source)

    while i < n:
        ch = source[i]

        # ── 1. Whitespace ────────────────────────────────────────────
        if ch in ' \t\r':
            i += 1
            continue

        if ch == '\n':
            line += 1
            i += 1
            continue

        # ── 2. Comentários  ──────────────────────────────────────────
        # Comentário de linha: # até o final da linha (ou EOF).
        # O \n não é consumido — será tratado na próxima iteração.
        if ch == '#':
            i += 1
            while i < n and source[i] != '\n':
                i += 1
            continue

        # ── 3. Strings  ──────────────────────────────────────────────
        if ch == '"':
            start_line = line
            start = i
            i += 1  # pula aspa de abertura
            while i < n and source[i] != '"':
                if source[i] == '\n':
                    line += 1
                i += 1
            if i >= n:
                raise LexError("string não fechada", start_line)
            i += 1  # pula aspa de fechamento
            tokens.append(Token('STRING', source[start:i], start_line))
            continue

        # ── 4. CLOCK_TIME, TIME_UNIT, PERCENT, NUMBER ─────────────────
        # Todos começam com dígito. A ordem de verificação resolve
        # a ambiguidade NUMBER vs TIME_UNIT vs PERCENT vs CLOCK_TIME.
        if ch.isdigit():
            start = i
            # consome todos os dígitos consecutivos
            while i < n and source[i].isdigit():
                i += 1

            # 4a. CLOCK_TIME: dígitos + ':' + dígitos [+ ':' + dígitos]
            if i < n and source[i] == ':':
                i += 1  # pula ':'
                if i >= n or not source[i].isdigit():
                    raise LexError(
                        "horário inválido: dígitos esperados após ':'",
                        line,
                    )
                while i < n and source[i].isdigit():
                    i += 1
                # segundos opcionais
                if i < n and source[i] == ':':
                    i += 1
                    if i >= n or not source[i].isdigit():
                        raise LexError(
                            "horário inválido: dígitos esperados após ':'",
                            line,
                        )
                    while i < n and source[i].isdigit():
                        i += 1
                tokens.append(Token('CLOCK_TIME', source[start:i], line))
                continue

            # 4b. PERCENT: dígitos + '%'
            if i < n and source[i] == '%':
                i += 1
                tokens.append(Token('PERCENT', source[start:i], line))
                continue

            # 4c. TIME_UNIT: dígitos + sufixo de tempo (s, min, m, h)
            if i < n and source[i] in 'smh':
                if source[i] == 'm':
                    # 'min' tem precedência sobre 'm' isolado
                    if i + 2 < n and source[i:i+3] == 'min':
                        i += 3
                    else:
                        i += 1  # apenas 'm'
                else:
                    i += 1  # 's' ou 'h'
                tokens.append(Token('TIME_UNIT', source[start:i], line))
                continue

            # 4d. NUMBER: apenas dígitos (já consumidos)
            tokens.append(Token('NUMBER', source[start:i], line))
            continue

        # ── 5. Palavras (keywords, ENTITY_ID, identificadores) ────────
        if ch.isalpha() or ch == '_':
            start = i
            start_line = line
            # consome [a-zA-Z_][a-zA-Z0-9_]*
            while i < n and (source[i].isalnum() or source[i] == '_'):
                i += 1

            # 5a. ENTITY_ID: palavra seguida de '.' + outra palavra
            if i < n and source[i] == '.':
                i += 1  # pula '.'
                if i >= n or not (source[i].isalpha() or source[i] == '_'):
                    raise LexError(
                        "entity_id inválido: identificador esperado após '.'",
                        line,
                    )
                while i < n and (source[i].isalnum() or source[i] == '_'):
                    i += 1
                tokens.append(Token('ENTITY_ID', source[start:i], start_line))
                continue

            # 5b. Palavra-chave ou identificador simples
            word = source[start:i]
            token_type = _KEYWORDS.get(word, 'IDENTIFIER')
            tokens.append(Token(token_type, word, start_line))
            continue

        # ── 6. Símbolos ───────────────────────────────────────────────
        if ch == '{':
            tokens.append(Token('LBRACE', '{', line))
            i += 1
            continue
        if ch == '}':
            tokens.append(Token('RBRACE', '}', line))
            i += 1
            continue
        if ch == ';':
            tokens.append(Token('SEMICOLON', ';', line))
            i += 1
            continue
        if ch == '=':
            tokens.append(Token('EQUALS', '=', line))
            i += 1
            continue

        # ── 7. Caractere inválido ─────────────────────────────────────
        raise LexError(f"caractere inválido '{ch}'", line)

    # ── EOF ───────────────────────────────────────────────────────
    tokens.append(Token('EOF', '', line))
    return tokens
