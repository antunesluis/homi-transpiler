# AGENTS.md — Homi Compiler

Este arquivo instrui agentes de IA (Claude Code, Cursor, Copilot, etc.) sobre como trabalhar neste projeto.

## O que é este projeto

Um compilador para a linguagem **Homi**, escrito em Python puro (sem PLY, sem ANTLR).
Transforma scripts `.homi` em arquivos YAML compatíveis com o Home Assistant.

Fases implementadas manualmente:

1. Análise Léxica (lexer.py)
2. Análise Sintática LL(1) com modo pânico (parser.py)
3. Análise Semântica + tabela de símbolos (semantic.py)
4. Geração de código YAML (codegen.py)

## Restrições Técnicas

- **Python 3.11+**, sem dependências externas além de `pytest` e `pyyaml`
- Sem PLY, ANTLR, lark, ou qualquer biblioteca de parsing
- Lexer e parser implementados manualmente (requisito acadêmico)
- Código deve ser legível e comentado — será avaliado pelo professor

## Estrutura dos Módulos

```
src/
  main.py       — entry point: lê .homi, imprime YAML ou erros
  lexer.py      — tokenizador: retorna lista de Token(type, value, line)
  parser.py     — parser LL(1) com tabela preditiva; gera AST
  semantic.py   — análise semântica; popula tabela de símbolos; valida tipos
  codegen.py    — percorre AST e emite YAML
```

Ver ARCHITECTURE.md para o fluxo detalhado entre os módulos.
Ver SPEC.md para a gramática completa e tokens definidos.

## Convenções de Código

- Cada classe/função pública deve ter docstring
- Erros léxicos: `LexError(message, line)`
- Erros sintáticos: `ParseError(message, line, token)`
- Erros semânticos: `SemanticError(message, line)`
- Nunca abortar no primeiro erro sintático — usar modo pânico (sync em `;` e `}`)
- Todos os erros coletados numa lista e exibidos ao final

## Como Rodar

```bash
python src/main.py examples/movimento.homi
python src/main.py examples/movimento.homi --output saida.yaml
python -m pytest tests/
```

## Convenções de Nomenclatura

- Tokens: constantes em UPPER_SNAKE_CASE (ex: `KW_QUANDO`, `ENTITY_ID`, `TIME_UNIT`)
- Nós da AST: classes com sufixo `Node` (ex: `AutomacaoNode`, `TriggerNode`)
- Visitors do codegen: métodos `visit_<NomeDaClasse>`

## O que NÃO fazer

- Não usar `eval()` ou `exec()`
- Não reescrever a gramática sem atualizar SPEC.md
- Não mudar a interface pública de `lexer.py` ou `parser.py` sem atualizar ARCHITECTURE.md
- Não deletar testes existentes

## Fluxo de Desenvolvimento

Ao adicionar uma nova construção da linguagem:

1. Adicionar token em SPEC.md (seção Tokens)
2. Implementar reconhecimento em `lexer.py`
3. Adicionar produção em SPEC.md (seção Gramática)
4. Implementar no `parser.py` e retornar o nó AST correto
5. Adicionar validação semântica em `semantic.py` se necessário
6. Adicionar emissão YAML em `codegen.py`
7. Criar fixture em `tests/fixtures/` e teste em `tests/`
