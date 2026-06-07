# AGENTS.md — Homi Compiler

## O que é

Compilador para a linguagem **Homi** — uma DSL em português para automações do Home Assistant.
Transforma scripts `.homi` em YAML compatível com o Home Assistant.

Escrito em Python puro (sem PLY, ANTLR, ou bibliotecas de parsing — requisito acadêmico).
Fases: Léxica (lexer.py) → Sintática LL(1) (parser.py) → Semântica (semantic.py) → Codegen YAML (codegen.py).

Documentação de referência:
- `SPEC.md` — gramática, tokens, exemplos
- `ARCHITECTURE.md` — fluxo de compilação, interfaces dos módulos
- `automations_homi.yaml` — automações HA reais para basear o mapeamento Homi→YAML

## Comandos

```bash
make run           # compila examples/movimento.homi e imprime YAML
make test          # roda pytest tests/ -v
python src/main.py examples/movimento.homi --output saida.yaml   # salva em arquivo
```

## Restrições Técnicas

- **Python 3.11+**, apenas `pytest` e `pyyaml` como dependências
- Lexer e parser implementados manualmente (requisito acadêmico)
- Parser LL(1) com tabela preditiva
- Modo pânico no parser: nunca abortar no primeiro erro; sincronizar em `;` e `}`
- Todos os erros coletados e exibidos ao final no formato `[FASE] linha N: mensagem`
- Não usar `eval()` ou `exec()`
- Não deletar testes existentes

## Estrutura dos Módulos

```
src/
  main.py       — entry point: lê .homi, orquestra fases, imprime YAML ou erros
  lexer.py      — tokenize(source) → list[Token(type, value, line)]; DFA manual
  parser.py     — Parser(tokens).parse() → ProgramNode; descendente recursivo LL(1)
  semantic.py   — SemanticAnalyzer(ast).analyze(); tabela de símbolos + validação de tipos
  codegen.py    — CodeGenerator(ast).generate() → string YAML
tests/
  fixtures/     — scripts .homi de teste
```

## Convenções de Código

- Classes de erro: `LexError(message, line)`, `ParseError(message, line, token)`, `SemanticError(message, line)`
- Nós da AST: classes com sufixo `Node` (ex: `AutomacaoNode`, `TriggerNode`)
- Tokens: constantes `UPPER_SNAKE_CASE` (ex: `KW_QUANDO`, `ENTITY_ID`)
- Visitors do codegen: métodos `visit_<NomeDaClasse>`
- Cada classe/função pública com docstring — código será avaliado por professor

## Validações Semânticas Obrigatórias

1. `ligar`/`desligar` só para `luz.*`, `switch.*`, `media_player.*`
2. `sensor.*` e `binary_sensor.*` só em triggers e condições
3. Trigger de movimento exige prefixo `binary_sensor.*`
4. Trigger de bateria exige prefixo `sensor.*`
5. Estado `desarmado`/`armado` só para `alarm_control_panel.*`

## Ordem de Reconhecimento no Lexer

1. Whitespace e comentários (`#`) → ignorar
2. Strings (`"..."`)
3. CLOCK_TIME (`HH:MM` ou `HH:MM:SS`) — antes de NUMBER
4. TIME_UNIT (`Ns`, `Nmin`, `Nh`) — antes de NUMBER
5. PERCENT (`N%`) — antes de NUMBER
6. NUMBER
7. ENTITY_ID (`palavra.palavra`) e palavras-chave — via prefixo de letra
8. Símbolos: `{`, `}`, `;`, `=`

## Fluxo para Adicionar Nova Construção

1. Adicionar token em SPEC.md
2. Implementar reconhecimento em `lexer.py`
3. Adicionar produção em SPEC.md (Gramática)
4. Implementar parsing em `parser.py` e retornar nó AST correto
5. Validação semântica em `semantic.py` se necessário
6. Emissão YAML em `codegen.py`
7. Criar fixture em `tests/fixtures/` e teste em `tests/`
