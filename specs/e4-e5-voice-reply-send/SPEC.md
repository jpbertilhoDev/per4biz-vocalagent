# SPEC — E4+E5 Voice Reply + Send (MVP combined)

**Feature ID:** `e4-e5-voice-reply-send`
**Data:** 2026-04-15 · **Status:** ✅ aprovado PO · **Pontos:** 42

> Fecha o loop MVP: user ouve email (TTS) → dita resposta (STT) → LLM polish → edita/envia (Gmail API).

---

## 1. Problema

Após E1+E2+E3, user lê inbox mas não responde. Core value prop (copiloto vocal) requer loop completo: TTS + STT + LLM polish + send. Sem este loop, produto é read-only.

## 2. Stories (42 pt)
- US-V.1 (5) — Play button lê email (TTS PT-PT feminino)
- US-V.2 (13) — Record → Groq Whisper → transcript visível
- US-V.3 (5) — LLM polish (Llama 3.3 70B) → email educado
- US-V.4 (11) — Review: editar + re-ditar + enviar + cancelar
- US-V.5 (8) — Backend `/emails/send` Gmail API

## 3. Requisitos funcionais

### Backend voice
- **RF-V.1** `POST /voice/transcribe` multipart audio ≤1MB → Groq Whisper v3 → `{text, language, duration_ms}`
- **RF-V.2** `POST /voice/polish` `{transcript, email_context}` → Groq Llama 3.3 70B → `{polished_text, model_ms}`
- **RF-V.3** `POST /voice/tts` `{text, voice_id?}` → ElevenLabs streaming → bytes MP3

### Backend send
- **RF-V.4** `POST /emails/send` `{to, subject, body, in_reply_to?, references?}` → build RFC 5322 → Gmail `users.messages.send`
- **RF-V.5** Draft cached em `draft_responses` antes do envio (`status="pending"` → `"sent"`)

### Frontend
- **RF-V.6** `/email/[id]`: 2 novos botões "Ouvir" + "Responder"
- **RF-V.7** Record overlay modal com MediaRecorder WebM, timer, stop button, max 60s
- **RF-V.8** `/email/[id]/draft`: textarea editável + botões Re-ditar / Enviar / Cancelar
- **RF-V.9** Send success → toast PT-PT + redirect `/inbox`

## 4. Segurança/Privacidade
- Auth `Depends(current_user)` em todos os endpoints
- Audio blob **não persistido** (stream direto Groq → descartar)
- Transcript não logado (só IDs + latencies)
- Rate limit in-memory V1: 200 voice/dia, 100 sends/dia
- Send exige confirmação UI explícita (CLAUDE.md §3.7)

## 5. UX (PT-PT)
- Botões "Ouvir" + "Responder" no fundo do email detail
- Record modal com pulse animation + contador tempo
- Review page: campos For/Assunto read-only, body textarea editável
- Toast "Enviado com sucesso" verde após send OK
- Erros: toast vermelho "Falha a enviar — tenta de novo"

## 6. ACs
- **AC-V.1** Tap "Ouvir" → áudio PT-PT toca <3s
- **AC-V.2** Tap "Responder" → mic permission → gravar → parar → transcrever <5s → redirect `/draft`
- **AC-V.3** Draft pré-populated com LLM polish
- **AC-V.4** Editar + re-ditar + enviar todos funcionam
- **AC-V.5** Email aparece na Sent do Gmail real
- **AC-V.6** Zero audio em disco/Supabase
- **AC-V.7** Erros mostram fallback UI
- **AC-V.8** Latência total p95 <8s (batch mode V1)

## 7. Não-objetivos V1.x
Streaming STT live, barge-in, multi-language, attachments, draft auto-save cross-session, voice cloning.

---

**Fim.**
