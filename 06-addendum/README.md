# 06-addendum — Extensões formais ao PRD Per4Biz

**Objetivo:** adicionar ao PRD Per4Biz a formalidade enterprise que falta, inspirada no melhor do PRD VocalMind Pro, **sem tocar** nos documentos originais (01 a 05) nem no PDF consolidado.

**Data de criação:** 2026-04-15
**Versão:** 1.0
**Estado:** baseline — expansões incrementais por épico à medida que são implementadas.

---

## Porquê este addendum

O PRD Per4Biz (01 a 05) já tem arquitetura, design system, sprint plan e validação interna. Faltava-lhe a camada de formalismo documental tipicamente exigida em PRDs enterprise (FAANG / Série A+):

- Critérios de aceitação Gherkin por user story
- Tabelas formais de constraints / assumptions / out-of-scope
- Matriz de erros por módulo
- Estratégia de testes em pirâmide
- Política de logging / observabilidade

Estes 5 artefactos **não substituem** o PRD, **complementam-no**.

---

## Mapa dos documentos

| # | Documento | Inspirado em | O que acrescenta |
|---|---|---|---|
| 1 | [ACCEPTANCE-CRITERIA.md](ACCEPTANCE-CRITERIA.md) | VocalMind Pro §7.1 | Gherkin (Given/When/Then) para todos os 30 user stories (E1-E8) |
| 2 | [CONSTRAINTS-ASSUMPTIONS-OOS.md](CONSTRAINTS-ASSUMPTIONS-OOS.md) | VocalMind §7.2–7.3 | Tabelas formais CON-xxx, ASM-xxx, OOS-xxx com IDs rastreáveis |
| 3 | [ERROR-MATRIX.md](ERROR-MATRIX.md) | VocalMind §7.6 | Matriz Google API / Voice Agent / Email / Multi-conta + mensagens user-facing em PT-PT |
| 4 | [TESTING-STRATEGY.md](TESTING-STRATEGY.md) | VocalMind §7.5 | Pirâmide unit / integration / E2E com cenários concretos + configuração CI |
| 5 | [LOGGING-POLICY.md](LOGGING-POLICY.md) | VocalMind §7.6 (logging table) | O que logar, o que NUNCA logar, níveis, PII-redaction |

---

## Como usar

**Durante brainstorming** (Superpowers skill `brainstorming`):
- Consulta [ACCEPTANCE-CRITERIA.md](ACCEPTANCE-CRITERIA.md) para cobrir todos os ACs da feature no SPEC.

**Durante planeamento** (skill `writing-plans`):
- Consulta [TESTING-STRATEGY.md](TESTING-STRATEGY.md) para definir testes RED antes de cada task.

**Durante implementação** (skill `test-driven-development`):
- Consulta [ERROR-MATRIX.md](ERROR-MATRIX.md) para tratar falhas corretamente.
- Consulta [LOGGING-POLICY.md](LOGGING-POLICY.md) para instrumentar observabilidade.

**Durante code review** (skill `requesting-code-review`):
- Valida contra [CONSTRAINTS-ASSUMPTIONS-OOS.md](CONSTRAINTS-ASSUMPTIONS-OOS.md) — não violar constraints, não implementar fora do escopo.

---

## Adaptações feitas ao importar do VocalMind Pro

Onde o VocalMind tinha decisões técnicas diferentes das do Per4Biz, adaptei:

| VocalMind (original) | Per4Biz (adaptado) |
|---|---|
| Flet + Flutter Web PWA | Next.js 16 + next-pwa |
| SQLite single-process | Supabase Postgres + RLS |
| Fernet (AES-128-CBC) | AES-256-GCM |
| OpenAI GPT-4o-mini / Gemini | Claude 3.5 Sonnet (drafts) + Groq Llama 3.3 (intents) |
| Web Speech API + Whisper fallback | Groq Whisper v3 (principal) |
| gTTS fallback | ElevenLabs Multilingual v2 (principal) + Web Speech fallback |
| Railway / Render | Fly.io Madrid (`mad`) + Supabase EU |
| Omite CASA Tier 2 | Explícito — CASA obrigatório para production scopes restricted |
| 1 conta Google + 2ª opcional | Multi-conta nativo desde arquitectura (1 na V1, N na V1.x) |
| OpenAI keys | Anthropic + Groq + ElevenLabs keys |

---

## Validação acumulada

Com este addendum, o PRD Per4Biz cobre agora os 23 critérios de um PRD enterprise completo — ver [ACCEPTANCE-CRITERIA.md §final](ACCEPTANCE-CRITERIA.md) para o checklist.
