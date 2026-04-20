# Vox Latency Reduction — Design Spec (E10)

**Data:** 2026-04-20
**Autor:** JP + Claude (brainstorming session)
**Status:** Proposed — awaiting PO review
**Épico:** E10 (novo, adicionar a `04-sprints/SPRINT-PLAN.md`)
**Relacionado:** `06-addendum/TESTING-STRATEGY.md`, `CLAUDE.md` §3.14 (auto-silêncio), §3.10 (Groq-only)

---

## 1. Problema

O agente vocal Vox está implementado end-to-end (E1-E5 + E9) mas o PO reporta percepção de lentidão. O maior incómodo é **time-to-first-audio** — tempo entre o utilizador parar de falar e ouvir a Vox começar a responder.

Não existe telemetria. Pipeline actual estima-se em ~4.7s, acima do budget `p95 < 4s` definido no PRD e no agente `per4biz-voice-engineer`.

## 2. Objectivo

Reduzir time-to-first-audio para:

- **p50 < 1.8s**
- **p95 < 3.5s** (apertamos em 500ms face ao budget PRD)

Medido end-to-end no cliente em rede 4G mobile real.

## 3. Escopo

### Dentro

- Instrumentação de latência por fase (VAD, upload, STT, intent, LLM, TTS, playback).
- Optimizações guiadas pelos dados: VAD adaptativo, split intent 8B/70B, streaming LLM→TTS.
- Feature flags para rollout seguro.
- Testes de latência em CI + E2E nightly.

### Fora

- Troca de provider (Vapi/LiveKit/OpenAI Realtime) — viola `CLAUDE.md` §3.10 (Groq-only).
- Melhorias de accuracy de intent/STT (outro épico).
- Barge-in / turn-taking (outro épico).
- Redesign visual, features novas.

### Critério de saída

Telemetria de produção mostra **p95 < 3500ms em ≥20 sessões/dia durante 3 dias consecutivos** → remover feature flags, aceitar código como definitivo.

## 4. Arquitectura — Fase 1 (Instrumentação)

### Identificador de sessão

Cada sessão de voz gera um `voice_session_id` (UUID v4) no cliente. Propaga-se via header `X-Voice-Session-Id` em todas as chamadas backend e é incluído em todos os eventos de telemetria.

### Fases medidas

Todos os tempos em ms desde `t0 = mic stop detected`:

| Fase | Marco | Onde instrumentar |
|---|---|---|
| `vad_cut` | auto-silêncio decide fim | `frontend/components/record-modal.tsx` |
| `upload_start` / `upload_done` | POST blob áudio | `frontend/lib/voice-client.ts` (novo) |
| `stt_start` / `stt_done` | Groq Whisper v3 | `backend/app/services/voice_stt.py` |
| `intent_start` / `intent_done` | Llama classify | `backend/app/services/voice_intent.py` |
| `llm_start` / `llm_first_token` / `llm_done` | Llama generate | `backend/app/services/voice_llm.py` |
| `action_start` / `action_done` | Gmail/Calendar side-effect | `backend/app/routers/voice.py` |
| `tts_start` / `tts_first_byte` / `tts_done` | ElevenLabs stream | `backend/app/services/voice_tts.py` |
| `audio_first_play` | browser começa playback | `frontend/components/record-modal.tsx` |

### Transporte dos dados

- **Backend:** structured log JSON `{voice_session_id, phase, ms, status}` → Sentry breadcrumbs.
- **Frontend:** no fim de cada sessão envia `POST /voice/telemetry` com array de timings (fire-and-forget, non-blocking).
- **Persistência:** tabela Supabase `voice_latency_events` (TTL 30 dias via cron).
- **Dashboard:** query SQL produz p50/p95/p99 por fase das últimas 24h. JP corre manualmente via Supabase SQL Editor.

### Zero PII

Eventos contêm apenas: `voice_session_id`, `phase`, `ms`, `status`, `user_id` (hash), `timestamp`. Nunca transcript, corpo de email, tokens, voice bytes. Conforme `CLAUDE.md` §3.3 e `06-addendum/LOGGING-POLICY.md`.

### Schema Supabase

```sql
CREATE TABLE voice_latency_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  voice_session_id UUID NOT NULL,
  user_id UUID NOT NULL,
  phase TEXT NOT NULL,
  ms INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ok', 'error', 'timeout')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX voice_latency_events_session_idx
  ON voice_latency_events(voice_session_id);
CREATE INDEX voice_latency_events_created_idx
  ON voice_latency_events(created_at DESC);
```

Cron diário apaga registos > 30 dias.

### Entregável Fase 1

Após 20-30 sessões reais capturadas, tabela ordenada "fase X = N ms" que decide a ordem real da Fase 2.

**Duração estimada:** 2-3 dias.

## 5. Arquitectura — Fase 2 (Optimizações)

Três candidatas com design pronto. Ordem real sai dos dados da Fase 1. Expectativa a priori: A → B → C.

### Candidata A — VAD adaptativo

**Problema:** auto-silêncio fixo 2000ms (regra `CLAUDE.md` §3.14) é pagamento fixo por turno.

**Solução:** substituir timer fixo por Voice Activity Detection baseado em energia + duração:

- Biblioteca: `@ricky0123/vad-web` (WebAssembly Silero VAD, ~1MB, 100% client-side, sem telemetria externa).
- Parâmetros: fim de fala quando energia abaixo de threshold adaptativo durante **400-600ms** contínuos.
- Fallback: se VAD falhar a carregar, volta ao timer fixo de 2s (zero regressão).
- Settings: slider em Settings "sensibilidade do corte" (300-2000ms), default 500ms.

**Ganho estimado:** —1400ms médio.
**Risco:** cortar utilizador a meio. Mitigação: validação com 30 frases reais PT-PT antes de rollout, logar `false_cut` quando utilizador reinicia em < 1s.
**Ficheiros:** `frontend/components/record-modal.tsx`, `frontend/lib/vad.ts` (novo), `frontend/app/(app)/settings/page.tsx`.

### Candidata B — Split intent (Llama 8B) + draft (Llama 70B)

**Problema:** Llama 3.3 70B faz tudo — classificar intent + gerar resposta. Classificação não precisa de 70B.

**Solução:** pipeline em dois modelos no Groq:

1. **Llama 3.1 8B Instant** classifica intent (~150ms no Groq) → JSON `{intent, slots, confidence}`.
2. Apenas para intents generativas (`chat`, `summarize`, `compose_reply`) chama **Llama 3.3 70B**.
3. Para intents determinísticas (`delete_email`, `create_event`, `list_emails`, `cancel`) resposta vocal é **template PT-PT pré-escrito** → zero segunda chamada LLM.

**Templates PT-PT (exemplos):**

- `delete_email` → "Apaguei o email de {sender}."
- `create_event` → "Marquei {title} para {date_human}."
- `list_emails` → "Tens {n} emails novos. O primeiro é de {sender}, sobre {subject}."

**Ganho estimado:** —500ms em intents determinísticas (maioria dos turnos), —200ms em generativas.
**Risco:** 8B pode classificar mal. Mitigação: extender harness de 20 → 50+ casos PT-PT. Gate de merge = ≥95% accuracy. Se confidence < 0.7, fallback para 70B como classificador.
**Ficheiros:** `backend/app/services/voice_intent.py`, `backend/app/services/voice_llm.py`, `backend/app/services/voice_templates.py` (novo), `backend/tests/voice/test_intent_accuracy.py`.

### Candidata B.1 — Groq native tool calling (sub-item de B)

**Problema:** `voice_intent.py` hoje usa prompt-parsing custom (instruções no system prompt + `json.loads()` sobre resposta text do LLM). Frágil (falha ~5% dos casos com JSON malformado), verboso, adiciona latência de parsing/retry.

**Solução:** substituir prompt-parsing por tool calling nativo do Groq (`tools=[...]` no SDK). Cada intent vira uma function com JSON schema estruturado:

```python
tools = [
    {"type": "function", "function": {
        "name": "delete_email",
        "parameters": {"type": "object", "properties": {
            "email_id": {"type": "string"},
            "sender_match": {"type": "string"}
        }, "required": []}
    }},
    {"type": "function", "function": {
        "name": "create_event",
        "parameters": {"type": "object", "properties": {
            "title": {"type": "string"},
            "datetime_iso": {"type": "string", "format": "date-time"},
            "duration_min": {"type": "integer"}
        }, "required": ["title", "datetime_iso"]}
    }},
    # ... restantes intents determinísticas (list_emails, cancel, reminder)
    #     + generativas (chat, summarize, compose_reply) como tools
]
```

Llama 3.1 8B devolve `tool_calls=[{name, arguments}]` estruturado pelo runtime Groq. Sem regex, sem `json.loads()` defensivo, sem retries por JSON partido.

**Fallback:** se `tool_calls` vazio → tratar como intent `chat` (rota generativa, Llama 70B).

**Relação com B:** B.1 implementa-se dentro do mesmo refactor de B — zero trabalho duplicado. Apenas troca *como* o 8B classifica; o pipeline det/gen de B fica igual.

**Ganho estimado (adicional a B):** —50 a —100ms (eliminação do parsing custom + retries); accuracy +2–5% (runtime garante JSON válido).
**Risco:** baixo. Groq suporta tool calling em Llama 3+ desde 2024-07, produção estável.
**Ficheiros:** `backend/app/services/voice_intent.py`, `backend/app/services/voice_tools.py` (novo — schema das tools), `backend/tests/voice/test_intent_tool_calling.py`.

### Candidata C — Streaming LLM → ElevenLabs

**Problema:** esperamos frase inteira do LLM antes de chamar TTS.

**Solução:** stream de tokens Groq → input stream ElevenLabs `/v1/text-to-speech/{voice_id}/stream-input` (WebSocket, já suportado pelo SDK `elevenlabs`). Primeiro áudio toca ~300ms após primeiro token LLM.

**Aplica-se apenas a:** intents generativas (path 2 da candidata B). Intents determinísticas usam templates curtos, não beneficiam de streaming.

**Ganho estimado:** —600 a —900ms em respostas generativas.
**Risco:** complexidade WebSocket, reconexão, backpressure. Mitigação: implementar com fallback automático para modo batch em erro (timeout 1s sem primeiro byte → cai para batch).
**Ficheiros:** `backend/app/services/voice_tts.py`, `backend/app/routers/voice.py`.

### Projecção agregada

Duas paths distintas após candidata B:

- **det** (intent determinístico → template PT-PT, sem 2ª chamada LLM): `delete_email`, `create_event`, `list_emails`, `cancel`, `reminder`.
- **gen** (intent generativo → Llama 70B): `chat`, `summarize`, `compose_reply`.

| Pipeline | det (ms) | gen (ms) |
|---|---|---|
| Actual | ~4700 | ~4700 |
| + A (VAD) | ~3300 | ~3300 |
| + A + B (split intent) | ~1850 | ~3350 |
| + A + B + C (stream TTS) | ~1850 (C não aplica) | ~2650 |

- **det** fica em ~1850ms, **dentro do p50 target** (1800ms) com margem apertada.
- **gen** fica em ~2650ms, **dentro do p95 target** (3500ms) com folga.
- Experiência percebida é dominada pelas intents determinísticas (maioria dos turnos no uso real), logo o *feel* geral deve aproximar-se do p50.

### Explicitamente rejeitado

- **Filler acústico** ("hmm", "ok" antes da resposta real): sente-se falso, quebra a persona "senior-secretary" (`CLAUDE.md` §3, commit `7ad0166`).
- **Cache de respostas frequentes:** complexidade alta, ganho baixo em multi-turn com contexto.
- **Antecipar intent com transcript parcial:** risco alto de cancelamentos quando utilizador muda de ideia a meio.
- **TTS local (Piper / Kokoro):** qualidade PT-PT inferior, perde-se o diferencial da voz ElevenLabs.

## 6. Testing

### Unit

- `voice_intent.py`: harness 50 casos PT-PT, devolve intent+slots esperados. Categorias: apagar, responder, agendar, lembretes, listar, chit-chat, ambíguos, out-of-scope.
- `test_intent_tool_calling.py` (B.1): 20 casos PT-PT focados em arguments dos tool_calls — assert `tool_calls[0].name` e `arguments` correctos; verifica fallback para `chat` quando `tool_calls` vazio.
- `voice_tts.py`: mock ElevenLabs, verifica streaming arranca após N tokens, fallback activa em erro.
- `vad.ts`: 10 clips áudio fixture (silêncio, fala+pausa, ruído, fala contínua, sotaque PT-PT rápido/lento) → cut point esperado ±100ms.
- `voice_templates.py`: cada template renderiza com slots válidos; assert zero placeholders `{x}` no output.

### Integration

- `test_voice_pipeline_latency.py`: chama `/voice/intent` end-to-end com audio fixture → assert cada fase emite timing → assert total < 3500ms. Groq real em CI, ElevenLabs mockado para determinismo.
- Executado em todos os PRs que tocam em `voice/*` ou `tests/voice/*`.

### E2E (Playwright)

- `voice-latency.spec.ts`: 5 cenários reais:
  1. "lê os meus emails"
  2. "apaga esse"
  3. "lembra-me amanhã às 9 da manhã"
  4. "responde obrigado"
  5. "cancela"

  Mede `mic stop → audio first play` no browser. Assert p95 < 3500ms sobre 20 execuções.
- Nightly cron, não por PR (custo Groq/ElevenLabs + tempo).

### Produção

- Dashboard SQL com p50/p95/p99 por fase, 7 dias rolling.
- Revisão manual 2×/semana (JP).

### Gates de merge

| Gate | Limiar |
|---|---|
| Harness accuracy intent | ≥ 95% (50 casos PT-PT) |
| Unit tests | 100% pass |
| Integration latency test | p95 < 3500ms (10 runs) |
| E2E nightly | p95 < 3500ms em 3 noites consecutivas |
| Harness original 20-case | 100% pass (zero regressão) |

## 7. Rollout

Feature flags via env var (`backend/app/config.py` — sem sistema de flags em V1):

- `VOICE_VAD_ADAPTIVE=false|true` (default `false`) — liga VAD adaptativo.
- `VOICE_INTENT_SPLIT=false|true` (default `false`) — liga pipeline 8B classifier + 70B/template.
- `VOICE_TTS_STREAMING=false|true` (default `false`) — liga streaming LLM→TTS para intents generativos.

Todas ficam `false` em produção até o merge passar nos gates da §6. Cada uma activa-se individualmente após dados reais confirmarem ganho.

Cada candidata merge-a atrás da sua flag. Rollback = flip da env var no Fly.io, zero git revert.

## 8. Dependências

- `@ricky0123/vad-web` (frontend, ~1MB WASM) — adicionar a `frontend/package.json`.
- Groq já expõe Llama 3.1 8B Instant — sem nova dependência backend.
- Groq SDK `groq` (já instalado) suporta native tool calling (`tools=[...]`) em Llama 3+ — B.1 sem nova dependência.
- ElevenLabs SDK já instalado, WebSocket streaming API disponível — sem upgrade.
- Supabase migration nova: `voice_latency_events` + índices + cron de cleanup 30d.

## 9. Open questions

Nenhuma — todas as decisões foram tomadas durante a sessão de brainstorming. Se aparecerem durante a escrita do plano, voltam aqui.

## 10. Referências

- `CLAUDE.md` §3.3 (zero PII), §3.10 (Groq-only), §3.14 (auto-silêncio).
- `02-ultraplan/ULTRAPLAN-tecnico.md` — stack voz e latency budget.
- `06-addendum/TESTING-STRATEGY.md` — pirâmide de testes.
- `06-addendum/LOGGING-POLICY.md` — redacção automática.
- Commits recentes: `ae9052c`, `7ad0166`, `8106b4b`, `be9596a`.
