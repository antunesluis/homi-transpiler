# Trabalho Final: Compiladores (2026)

## 1. Construir uma Linguagem e um Tradutor para Automações no Home Assistant

Os alunos deverão projetar e implementar um compilador (tradutor) para a linguagem **Homi**.

A linguagem deve abstrair a complexidade das automações procedurais, transformando scripts lógicos em arquivos de configuração YAML compatíveis com o padrão do Home Assistant.

### Prazo de Entrega

- Até dia **06/06/2026**
- Entrega via Classroom (link GitHub)

### Apresentação Presencial

- De acordo com o cronograma da disciplina.
- Formato presencial e explicativo.
- Serão realizadas 7 apresentações por dia letivo, seguindo a ordem de entrega.

---

# 2. Requisitos Técnicos Obrigatórios

O projeto deve ser construído seguindo rigorosamente as fases do front-end e o início do back-end de um compilador.

## A. Definição da Linguagem

- A linguagem definida pela GLC deve ser focada em pessoas leigas, que não possuem domínio de computação ou automação residencial.
- A(s) Gramática(s) Livre(s) de Contexto da linguagem deve(m) estar completamente especificada(s) na documentação.
- Em anexo a este documento existe uma série de automações em YAML que servirão de base.

---

## B. Análise Léxica (Scanner)

- Especificação e implementação de um DFA (Autômato Finito Determinístico), manual ou gerado (ex.: Flex), para reconhecimento dos tokens da GLC.
- Suporte a tokens complexos:
  - `entity_id` (ex.: `sensor.temperature_living_room`)
  - Unidades de tempo (ex.: `10s`, `5min`)
  - Strings
  - Operadores lógicos
- Tratamento de comentários.
- Contagem de linhas para reporte de erros.

---

## C. Análise Sintática (Parser)

- Representação da GLC na forma:
  - Top-Down LL(1), ou
  - Bottom-Up LR(k)
- Implementação obrigatoriamente baseada em:
  - Tabela Preditiva LL(1), ou
  - Tabela LR(k)

### Recuperação de Erros

O parser não deve abortar no primeiro erro.

Implementar a técnica de **Modo Pânico**, utilizando sincronização por tokens como:

- `;`
- `}`

---

## D. Análise Semântica

### Tabela de Símbolos

Armazenar:

- Tipos de entidades:
  - Luz
  - Sensor
  - Interruptor
- Escopo de variáveis

### Verificação de Tipos

Impedir operações inválidas.

Exemplo:

- Atribuir `"25°C"` a uma lâmpada ON/OFF.

### Consistência Externa

Validar se os serviços chamados são compatíveis com o domínio da entidade.

Exemplo:

```text
light.turn_on
```

---

## E. Geração de Código Intermediário (YAML)

- Tradução da árvore sintática (AST) para a estrutura declarativa do Home Assistant.
- Tratamento da indentação rígida do YAML.
- Mapeamento de:
  - Triggers
  - Condições
  - Ações

---

# 3. Entregáveis

## 1. Código Fonte

Repositório organizado contendo instruções de compilação:

- Makefile
- CMake
- Ou equivalente

---

## 2. Relatório Técnico

### a. Descrição da GLC

- Identificação dos terminais
- Identificação dos não-terminais

### b. Analisador Léxico

Descrição da especificação do analisador léxico.

### c. Analisador Sintático

Descrição da especificação do analisador sintático.

### d. Analisador Semântico

Descrição da especificação do analisador semântico.

### e. Exemplos

Apresentar:

- Scripts Homi
- YAMLs gerados

---

## 3. Apresentação

Defesa presencial de **15 minutos** contendo:

### a. Explicação Técnica

Explicação da:

- Gramática
- Especificação
- Implementação de cada etapa do compilador
- Decisões de projeto

### b. Demonstração de Erros

Demonstrar o compilador:

- Detectando erros sintáticos
- Detectando erros semânticos
- Reportando erros adequadamente

### c. Demonstração de Caso Válido

Processar um exemplo válido fornecido pelo docente durante a apresentação.

---

# 5. Critérios de Avaliação

| Item                  | Peso |
| --------------------- | ---- |
| Especificação da GLC  | 10%  |
| Analisador Léxico     | 10%  |
| Analisador Sintático  | 10%  |
| Analisador Semântico  | 10%  |
| Detecção de Erros     | 10%  |
| Apresentação e Testes | 50%  |

---
