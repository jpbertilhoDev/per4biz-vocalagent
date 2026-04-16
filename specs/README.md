# specs/

**Output da skill `brainstorming` do Superpowers.**

Cada feature tem a sua própria pasta com um `SPEC.md` aprovado pelo PO **antes** de qualquer código.

## Estrutura esperada

```
specs/
├── auth-google-oauth/
│   └── SPEC.md              ← output do brainstorming, aprovado por secções
├── inbox-read-only/
│   └── SPEC.md
├── voice-agent-mvp/
│   └── SPEC.md
└── composer-vocal/
    └── SPEC.md
```

## Convenção do nome da feature

- `kebab-case`
- Prefixo **opcional** do épico: `e4-voice-agent-mvp` (ver épicos em `../04-sprints/SPRINT-PLAN.md`)

## O que vai dentro de SPEC.md

Seguir o template que a skill `brainstorming` produz. Tipicamente:

1. Problema específico que esta feature resolve
2. User stories afetadas (ref. SPRINT-PLAN.md)
3. Requisitos funcionais (subset do PRD §7)
4. Comportamento esperado (happy path + edge cases)
5. Considerações de segurança / privacidade
6. Considerações de UX (ref. DESIGN-SPEC.md)
7. Critérios de aceitação (Gherkin: Given / When / Then)
8. Não-objetivos (o que esta feature **não** cobre)

## Quando criar

- Antes de `plans/<feature>/PLAN.md`.
- Antes de escrever qualquer linha de código de produção.
- A skill `brainstorming` bloqueia até o SPEC estar aprovado.
