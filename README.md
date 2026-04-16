# Per4Biz — Copiloto Vocal de Email e Agenda

> PWA mobile que responde emails e marca reuniões por voz, em múltiplas contas Google, com latência < 4s.

**Cliente:** JP Bertilho (mkt-agency)
**Status:** PRD v1.0 completo — aguarda validação do PO e início do Sprint 0
**Kickoff alvo:** Semana de 2026-04-20
**V1 Beta alvo:** 2026-07-20 (13 semanas)

---

## Índice de documentos

| # | Documento | Ficheiro | Autor | Objetivo |
|---|---|---|---|---|
| 1 | **PRD Mestre** | [01-prd/PRD-MASTER.md](01-prd/PRD-MASTER.md) | JP + Squad | Visão, personas, requisitos, escopo V1/V2 |
| 2 | **Ultraplan Técnico** | [02-ultraplan/ULTRAPLAN-tecnico.md](02-ultraplan/ULTRAPLAN-tecnico.md) | Agent Plan | Arquitetura, stack, data model, ADRs, riscos técnicos |
| 3 | **Design Spec (UI/UX PWA)** | [03-ui-ux/DESIGN-SPEC.md](03-ui-ux/DESIGN-SPEC.md) | Agent UI/UX | Sistema visual, wireframes, componentes, PWA specs |
| 4 | **Sprint Plan (Agile)** | [04-sprints/SPRINT-PLAN.md](04-sprints/SPRINT-PLAN.md) | Agent PO/SM | Épicos, stories, roadmap 13 semanas, checklist dia 1 |
| 5 | **Validação Interna** | [05-validacao/VALIDACAO-INTERNA.md](05-validacao/VALIDACAO-INTERNA.md) | Squad (red-team) | Auto-crítica, gaps, inconsistências, perguntas ao PO |
| 6 | **Addendum Enterprise** | [06-addendum/README.md](06-addendum/README.md) | Squad | Gherkin ACs completos, Constraints/Assumptions/OOS formais, Error Matrix, Testing Strategy, Logging Policy |

---

## Resumo em 60 segundos

**Produto:** PWA mobile (iOS/Android) que funciona como secretário vocal. Usuário toca no botão do microfone, fala, e o sistema:
1. Lê emails em voz alta (TTS via ElevenLabs PT-PT)
2. Transcreve respostas ditadas (STT via Groq Whisper)
3. Gera drafts profissionais (Claude 3.5 Sonnet em PT-PT)
4. Envia pela conta Google certa (Gmail API)
5. Marca reuniões por voz (Calendar — V2)

**Multi-conta:** 1 Google na V1, 2+ na V1.x. Inbox unificada com identidade visual por conta.

**Stack:** Next.js 16 PWA (Vercel) + FastAPI Python (Fly.io Madrid) + Supabase (EU) + Groq + Claude + ElevenLabs.

**Entrega:** Sprint 0 (setup) + 6 sprints de 2 semanas = 13 semanas até beta com 10 usuários.

**Velocity:** ~25 pts/sprint. Total V1: 147 story points.

---

## Próximos passos imediatos (por ordem)

1. ✅ **PRD, Ultraplan, Design Spec, Sprint Plan e Validação Interna criados** (2026-04-15).
2. ✅ **Projeto preparado para Superpowers** — CLAUDE.md, specs/, plans/, scaffold frontend/backend/supabase, .gitignore, .env.example.
3. ⬜ **PO (JP) responde às 7 perguntas críticas** em [05-validacao/VALIDACAO-INTERNA.md §5](05-validacao/VALIDACAO-INTERNA.md).
4. ⬜ **Decidir inconsistência Calendar V1.x vs V2** (bloqueia Sprint 5).
5. ⬜ **Instalar Superpowers** no Claude Code: `/plugin marketplace add obra/superpowers-marketplace` + `/plugin install superpowers@superpowers-marketplace`.
6. ⬜ **Adicionar critérios de aceitação Gherkin** para os 9 stories do Sprint 1.
7. ⬜ **Executar checklist Dia 1 do Sprint 0** (ver [04-sprints/SPRINT-PLAN.md §9](04-sprints/SPRINT-PLAN.md)).

---

## Integração Superpowers

O projeto está configurado para o workflow de [Superpowers](https://github.com/obra/superpowers):

- **[CLAUDE.md](CLAUDE.md)** — instruções carregadas em cada task (stack, regras invioláveis, comandos, convenções).
- **[specs/](specs/)** — outputs da skill `brainstorming` (um SPEC.md por feature, aprovado pelo PO antes de qualquer código).
- **[plans/](plans/)** — outputs da skill `writing-plans` (tasks bite-sized de 2-5 min com TDD estrito).

**Fluxo por feature:**
1. `brainstorming` → `specs/<feature>/SPEC.md` + aprovação PO
2. `using-git-worktrees` → branch `feat/per4biz-<feature>`
3. `writing-plans` → `plans/<feature>/PLAN.md`
4. `subagent-driven-development` → 1 subagent por task, two-stage review
5. `test-driven-development` → RED-GREEN-REFACTOR em cada task
6. `requesting-code-review` → entre tasks
7. `finishing-a-development-branch` → merge/PR

---

## Estrutura da pasta

```
clientes/Per4Biz/
├── README.md                    ← este ficheiro (índice)
├── CLAUDE.md                    ← instruções projeto-específicas p/ Superpowers
├── .gitignore
├── .env.example                 ← template de variáveis (copiar para .env)
├── Per4Biz-PRD-COMPLETO.{md,pdf} ← documento consolidado
├── 01-prd/PRD-MASTER.md         ← 17 secções, RF-1 a RF-11
├── 02-ultraplan/ULTRAPLAN-tecnico.md ← arquitetura, stack, ADRs
├── 03-ui-ux/DESIGN-SPEC.md      ← sistema visual, wireframes
├── 04-sprints/SPRINT-PLAN.md    ← épicos, 6 sprints, checklist dia 1
├── 05-validacao/VALIDACAO-INTERNA.md ← red-team, perguntas ao PO
├── 06-addendum/                 ← formalidade enterprise (Gherkin, CON/ASM/OOS, testes, logging)
├── specs/                       ← Superpowers: SPEC.md por feature
├── plans/                       ← Superpowers: PLAN.md por feature
├── frontend/                    ← Next.js 16 PWA (scaffold Sprint 0)
├── backend/                     ← FastAPI Python (scaffold Sprint 0)
└── supabase/                    ← migrations + RLS (scaffold Sprint 0)
```

---

## Como este PRD foi construído

Usando o squad da mkt-agency com 3 agents especializados executados em paralelo:

- **Agent Plan (Ultraplan)** — arquiteto técnico; produziu o Ultraplan.
- **Agent UI/UX** — mobile PWA designer; produziu o Design Spec.
- **Agent Scrum Master/PO** — ágil; produziu o Sprint Plan.

Depois o PRD Mestre foi consolidado e o próprio squad auto-validou o conjunto via red-team interno (Validação Interna), sem depender de revisor externo.

**Tempo de entrega do PRD completo:** ~3 minutos de execução paralela de agents + consolidação.
