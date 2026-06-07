# Relatório Técnico — Compilador Homi

**Disciplina:** Compiladores — ELC1067  
**Universidade Federal de Santa Maria — UFSM**  
**Ano:** 2026

---

## 1. Descrição da Linguagem e da GLC

### 1.1 Visão Geral

Homi é uma linguagem de domínio específico (DSL) projetada para usuários leigos descreverem automações residenciais em português. Um script `.homi` é compilado para um arquivo YAML compatível com o Home Assistant.

A filosofia de design prioriza legibilidade: palavras-chave em português, identificadores de entidades escritos diretamente (`luz.sala`, `sensor.temperatura`), e estrutura de blocos simples com `{` e `}`.

**Exemplo de script Homi:**

```homi
# Liga luz ao detectar movimento
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

**YAML gerado:**

```yaml
- alias: Corredor - movimento
  triggers:
    - trigger: state
      entity_id: binary_sensor.corredor_suite
      to: "on"
  conditions:
    - condition: state
      entity_id: alarm_control_panel.alarmo
      state: disarmed
    - condition: state
      entity_id: luz.corda_led_corredor
      state: "off"
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

---

### 1.2 Terminais (Tokens)

#### Palavras-chave

| Token          | Lexema      | Papel na gramática                 |
| -------------- | ----------- | ---------------------------------- |
| `KW_AUTOMACAO` | `automacao` | Inicia bloco de automação          |
| `KW_QUANDO`    | `quando`    | Inicia trigger                     |
| `KW_SE`        | `se`        | Inicia condition ou action_se      |
| `KW_ENTAO`     | `entao`     | Inicia bloco de ações              |
| `KW_SENAO`     | `senao`     | Bloco alternativo do action_se     |
| `KW_LIGAR`     | `ligar`     | Ação de ligar dispositivo          |
| `KW_DESLIGAR`  | `desligar`  | Ação de desligar dispositivo       |
| `KW_ESPERAR`   | `esperar`   | Ação de delay                      |
| `KW_NOTIFICAR` | `notificar` | Ação de notificação                |
| `KW_MUDA`      | `muda`      | Indica mudança de estado (trigger) |
| `KW_PARA`      | `para`      | Preposição de valor alvo           |
| `KW_HORA`      | `hora`      | Trigger/condição por horário       |
| `KW_ESTA`      | `esta`      | Indica estado atual (condição)     |
| `KW_LIGADO`    | `ligado`    | Estado: on                         |
| `KW_DESLIGADO` | `desligado` | Estado: off                        |
| `KW_ARMADO`    | `armado`    | Estado: armed                      |
| `KW_DESARMADO` | `desarmado` | Estado: disarmed                   |
| `KW_MOVIMENTO` | `movimento` | Trigger de detecção de movimento   |
| `KW_BATERIA`   | `bateria`   | Trigger de nível de bateria        |
| `KW_ABAIXO`    | `abaixo`    | Operador de comparação "menor que" |
| `KW_ACIMA`     | `acima`     | Operador de comparação "maior que" |

#### Tokens de Valor

| Token        | Padrão                                  | Exemplo                              |
| ------------ | --------------------------------------- | ------------------------------------ |
| `ENTITY_ID`  | `[a-zA-Z_]+\.[a-zA-Z0-9_]+`             | `luz.sala`, `binary_sensor.corredor` |
| `TIME_UNIT`  | `[0-9]+(s\|min\|m\|h)`                  | `45s`, `5min`, `2h`                  |
| `CLOCK_TIME` | `[0-9]+:[0-9]+(:[0-9]+)?`               | `22:30`, `08:00:00`                  |
| `NUMBER`     | `[0-9]+`                                | `42`, `100`                          |
| `STRING`     | `"(\\\\.\|[^"\\])*"`                     | `"Porta aberta!"`                    |
| `PERCENT`    | `[0-9]+%`                               | `20%`, `75%`                         |

#### Símbolos e Ignorados

| Token       | Lexema            | Observação                                  |
| ----------- | ----------------- | ------------------------------------------- |
| `LBRACE`    | `{`               | Abre bloco                                  |
| `RBRACE`    | `}`               | Fecha bloco / token de sincronização        |
| `SEMICOLON` | `;`               | Separador opcional / token de sincronização |
| `EQUALS`    | `=`               | Atribuição em trigger de hora               |
| `EOF`       | —                 | Fim do arquivo                              |
| —           | `# texto`         | Comentário de linha, ignorado pelo lexer    |
| —           | espaço, tab, `\n` | Whitespace, ignorado pelo lexer             |

---

### 1.3 Não-terminais e Gramática Livre de Contexto

A gramática está na forma LL(1) e é implementada por um parser descendente recursivo.

```
programa       → automacao*

automacao      → KW_AUTOMACAO STRING LBRACE
                   trigger+
                   condition*
                   action_block
                 RBRACE

trigger        → KW_QUANDO trigger_body SEMICOLON?

trigger_body   → ENTITY_ID KW_MUDA KW_PARA estado
               | KW_HORA EQUALS CLOCK_TIME
               | ENTITY_ID KW_MOVIMENTO
               | ENTITY_ID KW_BATERIA (KW_ABAIXO | KW_ACIMA) (NUMBER | PERCENT)

condition      → KW_SE condition_body SEMICOLON?

condition_body → ENTITY_ID KW_ESTA estado
               | KW_HORA (KW_ABAIXO | KW_ACIMA) CLOCK_TIME

action_block   → KW_ENTAO LBRACE action+ RBRACE

action         → KW_LIGAR ENTITY_ID SEMICOLON?
               | KW_DESLIGAR ENTITY_ID SEMICOLON?
               | KW_ESPERAR TIME_UNIT SEMICOLON?
               | KW_NOTIFICAR STRING SEMICOLON?
               | KW_SE condition_body KW_ENTAO LBRACE action+ RBRACE
                   (KW_SENAO LBRACE action+ RBRACE)?

estado         → KW_LIGADO | KW_DESLIGADO | KW_ARMADO | KW_DESARMADO | STRING
```

#### Conjuntos FIRST e FOLLOW relevantes

| Não-terminal     | FIRST                                                              | FOLLOW                                        |
| ---------------- | ------------------------------------------------------------------ | --------------------------------------------- |
| `programa`       | `KW_AUTOMACAO`, ε                                                  | `$`                                           |
| `automacao`      | `KW_AUTOMACAO`                                                     | `KW_AUTOMACAO`, `$`                           |
| `trigger`        | `KW_QUANDO`                                                        | `KW_QUANDO`, `KW_SE`, `KW_ENTAO`              |
| `trigger_body`   | `ENTITY_ID`, `KW_HORA`                                             | `SEMICOLON`, `KW_QUANDO`, `KW_SE`, `KW_ENTAO` |
| `condition`      | `KW_SE`                                                            | `KW_SE`, `KW_ENTAO`                           |
| `condition_body` | `ENTITY_ID`, `KW_HORA`                                             | `SEMICOLON`, `KW_ENTAO`, `RBRACE`             |
| `action_block`   | `KW_ENTAO`                                                         | `RBRACE`                                      |
| `action`         | `KW_LIGAR`, `KW_DESLIGAR`, `KW_ESPERAR`, `KW_NOTIFICAR`, `KW_SE`   | `RBRACE`                                      |
| `estado`         | `KW_LIGADO`, `KW_DESLIGADO`, `KW_ARMADO`, `KW_DESARMADO`, `STRING` | `SEMICOLON`, `KW_ENTAO`, `KW_QUANDO`, `KW_SE` |

A gramática é LL(1) porque para cada não-terminal e cada token de lookahead existe no máximo uma produção aplicável. A distinção entre `trigger_body` e `condition_body` é feita pelo token seguinte ao `ENTITY_ID`: `KW_MUDA`, `KW_MOVIMENTO` e `KW_BATERIA` são exclusivos de triggers; `KW_ESTA` é exclusivo de conditions.

---

## 2. Analisador Léxico

### 2.1 Implementação

O analisador léxico (`src/lexer.py`) implementa um DFA manual sem uso de bibliotecas de parsing (sem PLY, ANTLR, ou módulo `re`). A função principal é `tokenize(source: str) -> list[Token]`.

A varredura do código-fonte é feita caractere a caractere com um índice `i` e uma variável `line` para contagem de linhas (1-indexed). O reconhecimento de tokens segue uma ordem de prioridade determinística para resolver ambiguidades:

1. **Whitespace e comentários** — espaço, tab, `\r`, `\n`, e sequências `#...` são ignorados. O `\n` incrementa `line` antes de ser descartado.
2. **Strings** — ao encontrar `"`, consome tudo até a próxima `"` na mesma linha. Levanta `LexError` se a string não for fechada.
3. **Sequências numéricas** — todos começam com dígito. A ordem de verificação do sufixo resolve as ambiguidades:
   - `:` após dígitos → `CLOCK_TIME` (ex: `22:30`, `08:00:00`)
   - `%` após dígitos → `PERCENT` (ex: `20%`)
   - `s`, `min`, `m`, `h` após dígitos → `TIME_UNIT` (ex: `45s`, `5min`)
   - Sem sufixo → `NUMBER`
4. **Palavras** — consome `[a-zA-Z_][a-zA-Z0-9_]*`. Se seguido de `.` e outro identificador → `ENTITY_ID`. Caso contrário, consulta a tabela `_KEYWORDS`; se não for palavra-chave → `IDENTIFIER`.
5. **Símbolos** — `{`, `}`, `;`, `=` produzem seus tokens correspondentes.
6. **Caractere inválido** — levanta `LexError` com linha e caractere.

A lista retornada sempre termina com `Token("EOF", "", last_line)`.

### 2.2 Tratamento de Erros

O lexer levanta `LexError(message, line)` em dois casos: caractere inválido (ex: `@`, `$`) e string não fechada antes do fim da linha. Por ser um erro fatal, o pipeline interrompe a compilação e reporta o erro sem prosseguir para as fases seguintes.

### 2.3 Estrutura do Token

```python
@dataclass
class Token:
    type: str   # ex: "KW_QUANDO", "ENTITY_ID", "CLOCK_TIME"
    value: str  # lexema original, incluindo aspas em STRING
    line: int   # número da linha (1-indexed)
```

---

## 3. Analisador Sintático

### 3.1 Implementação

O analisador sintático (`src/parser.py`) implementa um parser descendente recursivo LL(1) sem bibliotecas externas. Cada não-terminal da gramática corresponde a um método privado `_parse_<nome>()`.

A classe `Parser` recebe a lista de tokens do lexer e expõe:

- `parse() -> ProgramNode`: retorna a AST completa
- `errors: list[ParseError]`: erros coletados durante o parsing

#### Primitivas de navegação

- `_peek() -> Token`: retorna o token atual sem consumir
- `_advance() -> Token`: consome e retorna o token atual
- `_check(*types) -> bool`: verifica se o token atual é de algum dos tipos
- `_match(expected_type) -> Token | None`: consome se o tipo bate; registra erro e sincroniza caso contrário
- `_optional_semicolon()`: consome `SEMICOLON` se presente (tokens opcionais)

### 3.2 Árvore Sintática Abstrata (AST)

A AST é composta por dataclasses Python com o sufixo `Node`. A raiz é `ProgramNode`:

```
ProgramNode
└── automacoes: list[AutomacaoNode]
    ├── nome: str
    ├── triggers: list[TriggerNode]
    │   ├── TriggerEstadoNode(entity_id, estado, line)
    │   ├── TriggerHoraNode(clock_time, line)
    │   ├── TriggerMovimentoNode(entity_id, line)
    │   └── TriggerBateriaNode(entity_id, operador, valor, line)
    ├── conditions: list[ConditionNode]
    │   ├── ConditionEstadoNode(entity_id, estado, line)
    │   └── ConditionHoraNode(operador, clock_time, line)
    └── actions: list[ActionNode]
        ├── ActionLigarNode(entity_id, line)
        ├── ActionDesligarNode(entity_id, line)
        ├── ActionEsperarNode(duration, line)
        ├── ActionNotificarNode(message, line)
        └── ActionSeNode(condition, then_actions, else_actions, line)
```

### 3.3 Recuperação de Erros — Modo Pânico

O parser nunca aborta no primeiro erro. Ao encontrar um token inesperado em qualquer produção:

1. Cria e registra um `ParseError(message, line, token)` em `self.errors`
2. Chama `_sync()`, que descarta tokens até encontrar um ponto de sincronização
3. Retorna `None` para o nó que falhou; o chamador verifica `None` antes de adicionar à lista

Os tokens de sincronização são `SEMICOLON`, `RBRACE` e `EOF`. `SEMICOLON` e `RBRACE` são consumidos ao serem encontrados para permitir o progresso do parser; `EOF` apenas interrompe o descarte sem consumo. Como o `SEMICOLON` é opcional na gramática, a recuperação prática apoia-se principalmente no `RBRACE` (fechamento de bloco).

---

## 4. Analisador Semântico

### 4.1 Implementação

O analisador semântico (`src/semantic.py`) percorre a AST validando regras de compatibilidade de domínio e preenchendo a tabela de símbolos. Todos os erros são coletados em `self.errors` — nunca aborta.

A classe `SemanticAnalyzer` expõe:

- `analyze() -> ProgramNode`: percorre a AST e retorna a AST original
- `symbol_table: SymbolTable`: tabela preenchida após a análise
- `errors: list[SemanticError]`: erros semânticos coletados

### 4.2 Tabela de Símbolos

A `SymbolTable` mapeia `entity_id → domínio`. O domínio é o prefixo antes do ponto:

| entity_id                    | Domínio extraído      |
| ---------------------------- | --------------------- |
| `luz.sala`                   | `luz`                 |
| `binary_sensor.corredor`     | `binary_sensor`       |
| `alarm_control_panel.alarmo` | `alarm_control_panel` |
| `sensor.temperatura`         | `sensor`              |

Toda `entity_id` encontrada em qualquer posição (trigger, condition ou action) é declarada na tabela. Re-declarações com o mesmo domínio são silenciosas.

### 4.3 Regras de Validação

**Regra 1 — Domínio de ações:** `ligar` e `desligar` só podem ser aplicados a entidades dos domínios `luz`, `switch` e `media_player`.

```
[SEMÂNTICO] linha 5: 'sensor.temperatura' não pode ser ligado:
            domínio 'sensor' não suporta esta ação
```

**Regra 2 — Trigger de movimento:** apenas `binary_sensor` pode ter trigger de movimento.

```
[SEMÂNTICO] linha 3: trigger de movimento requer domínio 'binary_sensor', encontrado 'luz'
```

**Regra 3 — Trigger de bateria:** apenas `sensor` pode ter trigger de bateria.

```
[SEMÂNTICO] linha 3: trigger de bateria requer domínio 'sensor', encontrado 'switch'
```

**Regra 4 — Estado armado/desarmado:** os estados `armado` e `desarmado` só são válidos para `alarm_control_panel`.

```
[SEMÂNTICO] linha 4: estado 'armado' só é válido para domínio
            'alarm_control_panel', encontrado 'luz'
```

As regras são verificadas recursivamente, inclusive dentro de `ActionSeNode`.

---

## 5. Geração de Código (YAML)

### 5.1 Implementação

O gerador de código (`src/codegen.py`) percorre a AST e constrói dicionários Python serializados com `pyyaml`. A opção por dicionários — em vez de f-strings — garante indentação correta e escaping automático.

### 5.2 Mapeamentos

#### Domínio Homi → Serviço Home Assistant

| Domínio Homi   | Serviço ligar          | Serviço desligar        |
| -------------- | ---------------------- | ----------------------- |
| `luz`          | `light.turn_on`        | `light.turn_off`        |
| `switch`       | `switch.turn_on`       | `switch.turn_off`       |
| `media_player` | `media_player.turn_on` | `media_player.turn_off` |

#### Estado Homi → Estado HA

| Estado Homi | Estado HA  |
| ----------- | ---------- |
| `ligado`    | `on`       |
| `desligado` | `off`      |
| `armado`    | `armed`    |
| `desarmado` | `disarmed` |

#### Construções Homi → YAML HA

| Construção Homi                    | Tipo YAML gerado                                               |
| ---------------------------------- | -------------------------------------------------------------- |
| `quando ENTITY muda para ligado`   | `trigger: state`, `to: 'on'`                                   |
| `quando hora = 22:30`              | `trigger: time`, `at: '22:30:00'`                              |
| `quando ENTITY movimento`          | `trigger: state`, `to: 'on'`                                   |
| `quando ENTITY bateria abaixo 20%` | `trigger: numeric_state`, `below: 20`                          |
| `se ENTITY esta desarmado`         | `condition: state`, `state: disarmed`                          |
| `se hora abaixo 22:00`             | `condition: time`, `before: '22:00:00'`                        |
| `ligar luz.sala`                   | `action: light.turn_on`, `target: {entity_id: luz.sala}`       |
| `esperar 45s`                      | `delay: {seconds: 45}`                                         |
| `notificar "msg"`                  | `action: notify.mobile_app`, `data: {message: msg}`            |
| `se COND entao {...} senao {...}`  | `choose: [{conditions, sequence}, {conditions: [], sequence}]` |

Horários são sempre normalizados para `HH:MM:SS` com zero-padding (`22:30` → `22:30:00`).

---

## 6. Exemplos

### 6.1 Trigger por movimento com delay

**Entrada:**

```homi
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

**Saída:**

```yaml
- alias: Corredor - movimento
  triggers:
    - trigger: state
      entity_id: binary_sensor.corredor_suite
      to: "on"
  conditions:
    - condition: state
      entity_id: alarm_control_panel.alarmo
      state: disarmed
    - condition: state
      entity_id: luz.corda_led_corredor
      state: "off"
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

### 6.2 Trigger por horário

**Entrada:**

```homi
automacao "Sala - desligar tudo" {
    quando hora = 05:00
    entao {
        desligar switch.luzes_da_sala
        desligar switch.luzes_da_cozinha
        desligar switch.luzes_do_lavabo
    }
}
```

**Saída:**

```yaml
- alias: Sala - desligar tudo
  triggers:
    - trigger: time
      at: 05:00:00
  conditions: []
  actions:
    - action: switch.turn_off
      target:
        entity_id: switch.luzes_da_sala
    - action: switch.turn_off
      target:
        entity_id: switch.luzes_da_cozinha
    - action: switch.turn_off
      target:
        entity_id: switch.luzes_do_lavabo
  mode: single
```

### 6.3 Trigger por bateria

**Entrada:**

```homi
automacao "Tablet - carregador" {
    quando sensor.bateria_tablet bateria abaixo 20%
    entao {
        ligar switch.carregador_tablet
        notificar "Tablet carregando"
    }
}
```

**Saída:**

```yaml
- alias: Tablet - carregador
  triggers:
    - trigger: numeric_state
      entity_id: sensor.bateria_tablet
      attribute: battery_level
      below: 20
  conditions: []
  actions:
    - action: switch.turn_on
      target:
        entity_id: switch.carregador_tablet
    - action: notify.mobile_app
      data:
        message: Tablet carregando
  mode: single
```

### 6.4 Demonstração de Erros

**Erro Léxico** — caractere inválido:

```
[LÉXICO]    linha 3: caractere inválido '@'
```

**Erro Sintático** — falta o bloco `entao`:

```
[SINTÁTICO] linha 3: esperado 'entao' para iniciar bloco de ações, encontrado '}'
[SINTÁTICO] linha 3: esperado '}' para fechar automação, encontrado ''
```

**Erros Semânticos** — múltiplos erros coletados sem abortar:

```
[SEMÂNTICO] linha 3: estado 'armado' só é válido para domínio 'alarm_control_panel', encontrado 'luz'
[SEMÂNTICO] linha 5: 'sensor.temperatura' não pode ser ligado: domínio 'sensor' não suporta esta ação
```
