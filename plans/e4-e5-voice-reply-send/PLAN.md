# PLAN — E4+E5 Voice Reply + Send

**SPEC:** `../../specs/e4-e5-voice-reply-send/SPEC.md` ✅
**Status:** ✅ aprovado · **Data:** 2026-04-15
**Estimativa:** 13 tasks · ~5-6h focado

## Tasks

### Track 1 — Backend voice (Tasks 1-6)

#### Task 1 — RED: Groq Whisper service tests
- `backend/tests/test_voice_stt.py`
- Tests: `test_transcribe_returns_text_and_duration`, `test_handles_groq_api_error`, `test_rejects_audio_too_large`
- Mock `groq.Groq().audio.transcriptions.create`

#### Task 2 — GREEN: `app/services/voice_stt.py`
- `transcribe(audio_bytes: bytes, mime: str) -> dict` — usa `groq` SDK, model `whisper-large-v3`
- Max size 1MB guard
- Zero logging de conteúdo

#### Task 3 — RED: Groq LLM polish tests
- `backend/tests/test_voice_llm.py`
- Tests: `test_polish_returns_coherent_email`, `test_polish_uses_email_context`, `test_handles_rate_limit`
- Mock `groq.Groq().chat.completions.create`

#### Task 4 — GREEN: `app/services/voice_llm.py`
- `polish_draft(transcript: str, context: dict) -> dict`
- System prompt PT-PT, model `llama-3.3-70b-versatile`
- Preserva intent + corrige gramática + tom educado

#### Task 5 — RED: ElevenLabs TTS tests
- `backend/tests/test_voice_tts.py`
- Tests: `test_tts_returns_audio_bytes`, `test_uses_pt_pt_voice`
- Mock `elevenlabs.client.ElevenLabs().text_to_speech.convert`

#### Task 6 — GREEN: `app/services/voice_tts.py` + `/voice` router
- `synthesize(text: str, voice_id: str | None = None) -> bytes`
- Router `app/routers/voice.py`: `POST /voice/transcribe` (multipart), `POST /voice/polish`, `POST /voice/tts` (returns StreamingResponse)
- Register em `main.py`

### Track 2 — Backend send (Tasks 7-8)

#### Task 7 — RED: email send tests
- `backend/tests/test_email_send.py`
- Tests: `test_send_builds_rfc5322`, `test_send_calls_gmail_api`, `test_send_persists_draft_as_sent`, `test_send_requires_auth`
- Mock `gmail.send_message`

#### Task 8 — GREEN: send endpoint
- `app/services/gmail.py` adiciona `send_message(user_id, to, subject, body, in_reply_to?) -> dict`
- `app/routers/emails.py` adiciona `POST /emails/send`
- Upsert `draft_responses` com `status="sent"` + `sent_at=now`

### Track 3 — Frontend voice UI (Tasks 9-12)

#### Task 9 — GREEN: MediaRecorder hook + record modal
- `frontend/lib/use-media-recorder.ts` — custom hook com `start/stop/audioBlob` state
- `frontend/components/record-modal.tsx` — modal overlay com timer, pulse, stop button, max 60s countdown

#### Task 10 — GREEN: integration no /email/[id]
- Botões "Ouvir" + "Responder" no footer
- "Ouvir" → chama `/voice/tts` → toca via `new Audio(URL.createObjectURL(blob))`
- "Responder" → abre record modal → on stop → POST `/voice/transcribe` → POST `/voice/polish` → redirect `/email/[id]/draft?text=<polished>`

#### Task 11 — RED: draft page tests
- `frontend/tests/draft.test.tsx`
- 4 testes: render pré-populated, edit, re-ditar abre modal, send chama endpoint

#### Task 12 — GREEN: `/email/[id]/draft` page
- Textarea com polished text
- Botões Re-ditar (reabre record modal) / Enviar (POST /emails/send) / Cancelar (back /inbox)
- Loading state durante send
- Success toast + redirect /inbox

### Track 4 — E2E + Checkpoint (Task 13)

#### Task 13 — E2E + Checkpoint JP
- `frontend/tests/e2e/voice-reply.spec.ts` (stubs all backend endpoints)
- **STOP — JP testa com email real:** play funciona, gravação funciona, polish aparece, editar, enviar → verifica Gmail Sent

---

## Riscos

| R | Mitigação |
|---|---|
| Groq SDK async vs sync | Usa sync Client() — FastAPI TestClient é sync |
| ElevenLabs voice_id não configurado | Fallback hardcoded voice `JGnWZj684pcXmK2SxYIv` (já no .env) |
| MediaRecorder iOS Safari quirks | WebM/Opus é suportado iOS 14.5+; fallback para MP4 se necessário |
| RFC 5322 encoding (unicode subject) | Use `email.mime` stdlib + `Header(subject, 'utf-8')` |
| Gmail API quota exhausted | Respeitar rate limit 250 quota/s — V1 sem uso intenso |

**Fim.**
