# Homi Compiler

Compilador para a linguagem **Homi** — uma DSL em português para automações do [Home Assistant](https://www.home-assistant.io/).

Transforma scripts `.homi` legíveis por leigos em arquivos YAML compatíveis com o Home Assistant.

Trabalho final da disciplina de Compiladores (ELC1067) — Universidade Federal de Santa Maria (UFSM), 2026.

## Instalação

```bash
git clone https://github.com/antunesluis/homi-transpiler
cd homi-transpiler
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Requer Python 3.11+. Dependências: `pytest`, `pyyaml`.

## Uso

```bash
# Compilar e imprimir YAML no stdout
python src/main.py examples/valid/movimento.homi

# Salvar em arquivo
python src/main.py examples/valid/movimento.homi --output saida.yaml

# Apenas validar (sem emitir YAML)
python src/main.py examples/valid/movimento.homi --check

# Verificar erros — erros no stderr, exit code 1
python src/main.py examples/invalid/erro_semantico.homi
```

Saída de erro típica (múltiplos erros coletados, nunca aborta no primeiro):

```
[SEMÂNTICO] linha 8: estado 'armado' só é válido para domínio 'alarm_control_panel', encontrado 'luz'
[SEMÂNTICO] linha 10: 'sensor.temperatura' não pode ser ligado: domínio 'sensor' não suporta esta ação
```

## Exemplo

**Entrada** (`examples/valid/movimento.homi`):

```homi
# Acende luz do corredor ao detectar movimento
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
```

**Saída** (YAML compatível com Home Assistant):

```yaml
- alias: Corredor - movimento
  triggers:
    - trigger: state
      entity_id: binary_sensor.corredor_suite
      to: 'on'
  conditions:
    - condition: state
      entity_id: alarm_control_panel.alarmo
      state: disarmed
    - condition: state
      entity_id: luz.corda_led_corredor
      state: 'off'
  actions:
    - action: light.turn_on
      target:
        entity_id: luz.corda_led_corredor
    - delay:
        seconds: 45
    - action: light.turn_off
      target:
        entity_id: luz.corda_led_corredor
  mode: single
```

## Testes

```bash
make test          # ou: python -m pytest tests/ -v
```

208 testes cobrindo todas as fases: 71 léxicos + 46 sintáticos + 32 semânticos + 40 codegen + 19 main.

## Arquitetura

```
                  arquivo.homi
                       │
              ┌────────┴────────┐
              │   src/lexer.py  │  DFA manual → lista de Token
              └────────┬────────┘
                       │
              ┌────────┴────────┐
              │  src/parser.py  │  LL(1) descendente recursivo → AST
              └────────┬────────┘       com modo pânico (sync em ; e })
                       │
              ┌────────┴────────┐
              │ src/semantic.py │  Tabela de símbolos + validação
              └────────┬────────┘       de domínio e tipos
                       │
              ┌────────┴────────┐
              │ src/codegen.py  │  PyYAML → Home Assistant YAML
              └────────┬────────┘
                       │
                  arquivo.yaml
```

- `src/nodes.py` — dataclasses da AST (12 nós + type aliases)
- `src/main.py` — entry point: CLI + API programática `compile_homi()`
- Implementação manual sem PLY, ANTLR ou bibliotecas de parsing

## Estrutura

```
src/
  main.py          Entry point (CLI + compile_homi)
  lexer.py         Analisador léxico (DFA manual)
  nodes.py         Nós da AST (dataclasses)
  parser.py        Analisador sintático (LL(1) recursivo)
  semantic.py      Analisador semântico (tabela de símbolos)
  codegen.py       Gerador de código YAML (PyYAML)
tests/
  test_lexer.py    71 testes
  test_parser.py   46 testes
  test_semantic.py 32 testes
  test_codegen.py  40 testes
  test_main.py     19 testes
  fixtures/        Scripts .homi auxiliares
examples/
  valid/           6 scripts que compilam sem erros
  invalid/         3 scripts demonstrando erros (léxico, sintático, semântico)
docs/
  SPEC.md          Gramática completa, tokens, conjuntos FIRST/FOLLOW
  ARCHITECTURE.md  Interfaces dos módulos, fluxo de compilação
  relatorio.md     Relatório técnico (entregável acadêmico)
```

## Documentação

- [docs/SPEC.md](docs/SPEC.md) — Especificação da linguagem: GLC, tokens, gramática LL(1)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Arquitetura do compilador: interfaces, fluxo, decisões de design
- [docs/relatorio.md](docs/relatorio.md) — Relatório técnico completo: descrição da GLC, analisador léxico, sintático (com modo pânico), semântico (tabela de símbolos e regras de validação), geração de código YAML e exemplos de entrada/saída
- [automations_homi.yaml](automations_homi.yaml) — Automações HA reais usadas como referência para o mapeamento Homi→YAML

## Comandos rápidos

```bash
make run         # compila examples/valid/movimento.homi
make test        # roda todos os testes (208)
make check       # valida todos os exemplos (valid e invalid)
make clean       # remove __pycache__ e .pyc
```
