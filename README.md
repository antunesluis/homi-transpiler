# Homi Compiler

Compilador para a linguagem **Homi** — uma DSL em português para automações do [Home Assistant](https://www.home-assistant.io/).

Transforma scripts `.homi` legíveis por leigos em arquivos YAML compatíveis com o HA.

## Instalação

```bash
git clone https://github.com/<seu-usuario>/homi-compiler
cd homi-compiler
pip install -r requirements.txt
```

Requer Python 3.11+.

## Uso

```bash
# Compilar e imprimir YAML no stdout
python src/main.py examples/movimento.homi

# Salvar em arquivo
python src/main.py examples/movimento.homi --output saida.yaml

# Ver erros de um script inválido
python src/main.py tests/fixtures/invalid/erro_semantico.homi
```

## Exemplo

**Entrada** (`movimento.homi`):

```homi
# Liga a luz do corredor quando detectar movimento
automacao "Corredor - movimento" {
    quando binary_sensor.corredor muda para ligado
    se alarm_control_panel.alarmo esta desarmado
    se luz.corredor esta desligado
    entao {
        ligar luz.corredor
        esperar 45s
        desligar luz.corredor
    }
}
```

**Saída** (`movimento.yaml`):

```yaml
- alias: "Corredor - movimento"
  triggers:
    - trigger: state
      entity_id: binary_sensor.corredor
      to: "on"
  conditions:
    - condition: state
      entity_id: alarm_control_panel.alarmo
      state: disarmed
    - condition: state
      entity_id: luz.corredor
      state: "off"
  actions:
    - action: light.turn_on
      target:
        entity_id: luz.corredor
    - delay:
        seconds: 45
    - action: light.turn_off
      target:
        entity_id: luz.corredor
  mode: single
```

## Testes

```bash
python -m pytest tests/ -v
```

## Documentação

- [SPEC.md](SPEC.md) — Gramática, tokens, exemplos
- [ARCHITECTURE.md](ARCHITECTURE.md) — Fluxo de compilação, interfaces dos módulos
- [AGENTS.md](AGENTS.md) — Guia para agentes de IA colaborando no projeto
- [docs/relatorio.md](docs/relatorio.md) — Relatório técnico (entregável acadêmico)

## Estrutura

```
src/          Código-fonte do compilador
tests/        Testes automatizados
examples/     Scripts .homi e YAMLs de exemplo
docs/         Relatório técnico
```
