# ARCHITECTURE.md — Arquitetura do Compilador Homi

## Fluxo de Compilação

```
arquivo.homi
     │
     ▼
┌─────────────┐
│   lexer.py  │  → Lista de Token(type, value, line)
└─────────────┘
     │
     ▼
┌─────────────┐
│  parser.py  │  → AST (árvore de nós *Node)
└─────────────┘
     │
     ▼
┌──────────────┐
│ semantic.py  │  → AST anotada + tabela de símbolos
└──────────────┘
     │
     ▼
┌─────────────┐
│  codegen.py │  → string YAML
└─────────────┘
     │
     ▼
arquivo.yaml
```

Se qualquer fase produz erros, eles são coletados e exibidos ao final.
O compilador não aborta no primeiro erro (modo pânico no parser).

---

## Módulo: lexer.py

### Interface Pública

```python
class Token:
    type: str    # ex: "KW_QUANDO", "ENTITY_ID", "STRING"
    value: str   # lexema original
    line: int    # número da linha (1-indexed)

class LexError(Exception):
    message: str
    line: int

def tokenize(source: str) -> list[Token]:
    """
    Recebe o conteúdo do arquivo .homi como string.
    Retorna lista de tokens (sem COMMENT, sem NEWLINE).
    Levanta LexError em caractere inválido.
    Sempre inclui Token("EOF", "", last_line) no final.
    """
```

### Estratégia

DFA manual implementado como função de scanning com lookahead de 1 caractere.
Ordem de reconhecimento:

1. Whitespace e comentários (`#`) → ignorar
2. Strings (`"..."`)
3. CLOCK_TIME (`HH:MM` ou `HH:MM:SS`) — antes de NUMBER
4. TIME_UNIT (`Ns`, `Nmin`, `Nh`) — antes de NUMBER
5. PERCENT (`N%`) — antes de NUMBER
6. NUMBER
7. ENTITY_ID (`palavra.palavra`) e palavras-chave — via prefixo de letra
8. Símbolos: `{`, `}`, `;`, `=`

---

## Módulo: parser.py

### Interface Pública

```python
class ParseError(Exception):
    message: str
    line: int
    token: Token

class Parser:
    def __init__(self, tokens: list[Token]): ...

    def parse(self) -> ProgramNode:
        """
        Retorna a AST completa.
        Coleta todos os erros em self.errors (lista de ParseError).
        Usa modo pânico: sincroniza em SEMICOLON e RBRACE.
        """

    errors: list[ParseError]
```

### Nós da AST

```python
@dataclass
class ProgramNode:
    automacoes: list[AutomacaoNode]

@dataclass
class AutomacaoNode:
    nome: str
    triggers: list[TriggerNode]
    conditions: list[ConditionNode]
    actions: list[ActionNode]
    line: int

@dataclass
class TriggerEstadoNode:
    entity_id: str
    estado: str       # "ligado" | "desligado" | ...
    line: int

@dataclass
class TriggerHoraNode:
    clock_time: str   # "22:30:00"
    line: int

@dataclass
class TriggerMovimentoNode:
    entity_id: str
    line: int

@dataclass
class TriggerBateriaNode:
    entity_id: str
    operador: str     # "abaixo" | "acima"
    valor: str        # lexema original: "20%" ou "30"
    line: int

@dataclass
class ConditionEstadoNode:
    entity_id: str
    estado: str
    line: int

@dataclass
class ConditionHoraNode:
    operador: str     # "abaixo" | "acima"
    clock_time: str
    line: int

@dataclass
class ActionLigarNode:
    entity_id: str
    line: int

@dataclass
class ActionDesligarNode:
    entity_id: str
    line: int

@dataclass
class ActionEsperarNode:
    duration: str     # ex: "45s", "2min"
    line: int

@dataclass
class ActionNotificarNode:
    message: str
    line: int

@dataclass
class ActionSeNode:
    condition: ConditionNode
    then_actions: list[ActionNode]
    else_actions: list[ActionNode]   # pode ser vazio
    line: int
```

### Estratégia LL(1)

Parser descendente recursivo. Cada não-terminal tem um método `parse_<nonterminal>()`.
Usa `self.current_token` e `self.advance()`.

Modo pânico: ao detectar token inesperado, chamar `self.sync()` que descarta tokens
até encontrar SEMICOLON, RBRACE, ou EOF.

---

## Módulo: semantic.py

### Interface Pública

```python
class SemanticError(Exception):
    message: str
    line: int

class SymbolTable:
    """Mapeia entity_id → tipo de domínio."""
    def declare(self, entity_id: str, domain: str, line: int): ...
    def lookup(self, entity_id: str) -> str | None: ...  # retorna domínio

class SemanticAnalyzer:
    def __init__(self, ast: ProgramNode): ...

    def analyze(self) -> ProgramNode:
        """
        Percorre a AST, preenche a tabela de símbolos,
        valida tipos e compatibilidade de domínio.
        Retorna a AST anotada.
        Coleta todos os erros em self.errors.
        """

    symbol_table: SymbolTable
    errors: list[SemanticError]
```

### Validações Obrigatórias

1. `ligar` / `desligar` só pode ser aplicado a `luz.*`, `switch.*`, `media_player.*`
2. `sensor.*` e `binary_sensor.*` só podem aparecer em triggers e condições
3. Entidade usada em trigger de movimento deve ter prefixo `binary_sensor.*`
4. Entidade usada em trigger de bateria deve ter prefixo `sensor.*`
5. Estado `desarmado`/`armado` só é válido para `alarm_control_panel.*`

---

## Módulo: codegen.py

### Interface Pública

```python
class CodeGenerator:
    def __init__(self, ast: ProgramNode): ...

    def generate(self) -> str:
        """
        Percorre a AST e emite YAML válido para o Home Assistant.
        Retorna a string YAML completa.
        """
```

### Estrutura YAML Gerada

```yaml
- alias: "Nome da Automação"
  triggers:
    - trigger: state
      entity_id: luz.sala
      to: "on"
  conditions:
    - condition: state
      entity_id: alarm_control_panel.alarmo
      state: disarmed
  actions:
    - action: light.turn_on
      target:
        entity_id: luz.sala
    - delay:
        seconds: 45
  mode: single
```

### Mapeamento de Domínio → Serviço HA

```python
DOMAIN_SERVICE = {
    "luz":          ("light",        "turn_on",  "turn_off"),
    "switch":       ("switch",       "turn_on",  "turn_off"),
    "media_player": ("media_player", "turn_on",  "turn_off"),
}
```

---

## Módulo: main.py

```python
# Uso:
#   python src/main.py input.homi
#   python src/main.py input.homi --output saida.yaml

import sys
from lexer import tokenize, LexError
from parser import Parser, ParseError
from semantic import SemanticAnalyzer, SemanticError
from codegen import CodeGenerator

def compile_homi(source: str) -> tuple[str | None, list[str]]:
    """
    Retorna (yaml_string, lista_de_erros).
    yaml_string é None se houver erros fatais.
    """
```

---

## Tratamento de Erros

Todos os erros são apresentados no formato:

```
[LÉXICO]   linha 3: caractere inválido '@'
[SINTÁTICO] linha 7: esperado 'entao', encontrado '}'
[SEMÂNTICO] linha 12: 'sensor.temperatura' não pode ser ligado (domínio: sensor)
```

O compilador tenta continuar após erros não-fatais para reportar o máximo de erros
possível em uma única execução.
