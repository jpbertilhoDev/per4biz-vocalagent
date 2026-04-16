# plans/

**Output da skill `writing-plans` do Superpowers.**

Cada feature tem um `PLAN.md` baseado no `SPEC.md` correspondente em `../specs/<feature>/`.

## Estrutura esperada

```
plans/
├── auth-google-oauth/
│   └── PLAN.md              ← tasks bite-sized (2-5 min cada)
├── inbox-read-only/
│   └── PLAN.md
├── voice-agent-mvp/
│   └── PLAN.md
└── composer-vocal/
    └── PLAN.md
```

## O que vai dentro de PLAN.md

A skill `writing-plans` produz um plano que um **junior engineer sem contexto** consegue seguir:

1. Lista ordenada de tasks bite-sized
2. Cada task tem:
   - **Título** (curto, imperativo)
   - **Ficheiro(s) afetado(s)** com paths exatos
   - **Teste a escrever primeiro** (RED) — código completo
   - **Código mínimo para passar** (GREEN) — código completo
   - **Refactor** (se necessário)
   - **Verificação** (comando a correr, output esperado)
3. Ordem de execução respeitando dependências
4. Sem "ser criativo" — todas as decisões já foram tomadas

## Princípios

- **TDD estrito**: teste antes de código de produção.
- **YAGNI**: sem abstrações para o futuro.
- **DRY**: sem duplicação, mas só após 3ª ocorrência.
- **Bite-sized**: se uma task demora > 5 min, dividir.

## Como executar

- Skill `subagent-driven-development`: 1 subagent por task, two-stage review.
- Ou skill `executing-plans`: batches com checkpoints humanos.

## Ligação ao plano maior

Cada `plans/<feature>/PLAN.md` cobre **um** item do backlog (user story ou grupo de stories).
O roadmap global de 147 pontos está em `../04-sprints/SPRINT-PLAN.md`.
