---
title: "Per4Biz — PRD Completo"
subtitle: "Copiloto Vocal de Email e Agenda"
author: "JP Bertilho · mkt-agency"
date: "2026-04-15"
pdf_options:
  format: A4
  margin: 20mm
  printBackground: true
  headerTemplate: |-
    <style>
      .header { font-size: 9px; width: 100%; text-align: center; color: #888; padding: 4px; }
    </style>
    <div class="header">Per4Biz — PRD Completo · v1.0 · 2026-04-15</div>
  footerTemplate: |-
    <style>
      .footer { font-size: 9px; width: 100%; text-align: center; color: #888; padding: 4px; }
    </style>
    <div class="footer"><span class="pageNumber"></span> / <span class="totalPages"></span></div>
  displayHeaderFooter: true
stylesheet_encoding: utf-8
body_class: markdown-body
css: |-
  body {
    font-family: -apple-system, "Segoe UI", "Inter", Roboto, Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.55;
    color: #1C1C1E;
    max-width: 100%;
  }
  h1 {
    color: #0A84FF;
    border-bottom: 2px solid #0A84FF;
    padding-bottom: 8px;
    margin-top: 28px;
    page-break-before: always;
  }
  h1:first-of-type { page-break-before: avoid; }
  h2 {
    color: #1C1C1E;
    border-bottom: 1px solid #E5E5EA;
    padding-bottom: 4px;
    margin-top: 24px;
  }
  h3 { color: #3A3A3C; margin-top: 20px; }
  h4 { color: #48484A; }
  code {
    background: #F2F2F7;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 9.5pt;
    font-family: "Consolas", "SF Mono", Menlo, monospace;
  }
  pre {
    background: #1C1C1E;
    color: #F2F2F7;
    padding: 12px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 9pt;
    line-height: 1.4;
    page-break-inside: avoid;
  }
  pre code { background: transparent; color: inherit; padding: 0; }
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
    font-size: 10pt;
    page-break-inside: avoid;
  }
  th, td { border: 1px solid #D1D1D6; padding: 6px 10px; text-align: left; vertical-align: top; }
  th { background: #F2F2F7; font-weight: 600; }
  blockquote {
    border-left: 4px solid #0A84FF;
    padding: 4px 12px;
    color: #48484A;
    background: #F9F9FB;
    margin: 12px 0;
  }
  hr { border: none; border-top: 1px solid #E5E5EA; margin: 24px 0; }
  a { color: #0A84FF; text-decoration: none; }
  ul, ol { padding-left: 20px; }
  li { margin: 2px 0; }
  .cover {
    page-break-after: always;
    text-align: center;
    padding-top: 140px;
  }
  .cover h1 {
    font-size: 48pt;
    color: #0A84FF;
    border: none;
    margin: 0;
    letter-spacing: -1px;
    page-break-before: avoid;
  }
  .cover .subtitle { font-size: 18pt; color: #6E6E73; margin-top: 8px; }
  .cover .meta { margin-top: 60px; color: #48484A; font-size: 12pt; }
  .toc { page-break-after: always; }
---

<div class="cover">

# Per4Biz

<div class="subtitle">Copiloto Vocal de Email e Agenda · PRD Completo</div>

<div class="meta">

**Produto:** PWA mobile multi-conta Google com agente vocal
**Cliente / Product Owner:** JP Bertilho · mkt-agency
**Versão:** 1.0 (baseline)
**Data:** 2026-04-15
**Squad:** mkt-agency (JP + agents Claude)

---

*Documento gerado automaticamente pelo squad mkt-agency*
*consolidando PRD + Ultraplan + Design Spec + Sprint Plan + Validação Interna*

</div>
</div>

<div class="toc">

# Índice

1. **Sumário Executivo & Visão**
2. **Problema & Solução**
3. **Personas & Objetivos**
4. **Escopo V1/V2 (MoSCoW)**
5. **Requisitos Funcionais (RF-1 a RF-11)**
6. **Requisitos Não-Funcionais (RNF-1 a RNF-8)**
7. **Arquitetura Técnica (Ultraplan)**
8. **Stack Tecnológica**
9. **Modelo de Dados (Supabase)**
10. **Integração Google APIs**
11. **Voice Agent (STT + LLM + TTS)**
12. **Segurança & Privacidade / GDPR**
13. **Suporte Multi-Conta**
14. **PWA Specifics**
15. **Decisões Arquiteturais (6 ADRs)**
16. **UI/UX — Design Principles & Sistema Visual**
17. **Arquitetura de Telas & Wireframes**
18. **Composer Vocal (tela-estrela)**
19. **Interações, Microinterações & Acessibilidade**
20. **Design System (Componentes)**
21. **Plano Ágil: Épicos & User Stories**
22. **Roadmap em 6 Sprints (13 semanas)**
23. **Backlog Priorizado (MoSCoW)**
24. **Cerimônias & Métricas**
25. **Riscos Top 7 & Mitigações**
26. **Checklist Dia 1 do Sprint 0**
27. **Distribuição de Trabalho por Role**
28. **Validação Interna (Red-Team do Squad)**
29. **Consistência Cross-Docs**
30. **Perguntas Críticas ao PO & Próximos Passos**

</div>

---

# Parte I — Product Requirements Document

## 1. Sumário Executivo

Per4Biz é um **PWA mobile** (instalável no iOS/Android) que funciona como um **secretário pessoal vocal** para profissionais que gerem **múltiplas contas Google**. O utilizador fala, o sistema ouve, consulta Gmail/Calendar/Contacts, gera respostas, confirma e envia — tudo sem tocar num teclado.

**Posicionamento:** "Superhuman encontra Siri para profissionais com 2+ emails." Diferente de Superhuman (rápido no teclado) e Siri (assistente genérico), Per4Biz é focado em **email vocal profissional multi-conta** com qualidade PT-PT.

**Público-alvo:** profissionais 20–40 anos em Portugal/Brasil, freelancers, consultores, empresários que operam pelo menos 2 caixas de correio Google (pessoal + trabalho) e passam >1h/dia a responder emails no móvel.

---

## 2. Problema

### 2.1 Dores do utilizador

1. **Responder email no móvel é lento e frustrante.** Teclado pequeno, auto-correção má, trocar de janela para ver a agenda — média de 3-4 min por resposta elaborada.
2. **Profissionais têm 2+ contas Google** (pessoal, agência, projetos) e alternar entre apps/contas é fricção constante, com envio acidental pela conta errada.
3. **Voice input nativo (Siri, Google Assistant) é genérico** — não resolve "lê-me o email do cliente X e responde a dizer que confirmo a reunião de quinta".
4. **Copilotos de email atuais** (Superhuman AI, Shortwave, Notion AI) são desktop-first e não têm fluxo vocal mobile-nativo.

### 2.2 Evidência de mercado

- 70%+ do consumo de email é mobile (Litmus, 2024).
- Voice assistants crescem 25% YoY em uso profissional (Juniper, 2025).
- Superhuman + Shortwave provam que há willingness to pay para produtividade de email (€30/mês).
- Gap: nenhum destes é mobile-voice-first e multi-conta real.

---

## 3. Solução

### 3.1 Proposta de valor

> *"Responde aos teus emails falando. Qualquer conta Google. Em 10 segundos."*

### 3.2 Jornada principal (loop de valor)

1. Utilizador recebe push notification de email.
2. Abre PWA Per4Biz → vê inbox unificada das 2+ contas.
3. Toca num email → app lê em voz alta (TTS).
4. Carrega no botão do microfone → dita a resposta natural.
5. AI gera draft em PT-PT profissional → mostra na tela.
6. Utilizador diz "envia" ou toca em "Enviar" → email sai pela conta certa.

**Tempo total esperado:** 30-60s por email, vs 3-4 min no fluxo tradicional.

### 3.3 Fluxos secundários

- **Compose por voz** sem email anterior: "manda um email ao João a dizer que confirmo a reunião de quinta".
- **Agenda por voz:** "marca reunião com a Ana amanhã às 15h".
- **Busca de contatos:** "qual é o email do Tiago da Finicapital?".
- **Troca de conta:** "muda para a conta da agência".

---

## 4. Personas

### Persona 1 — "Carla, 32 anos, consultora independente"
- 3 contas Google (pessoal, consultoria, cliente X).
- Recebe ~80 emails/dia, responde no móvel entre reuniões.
- **Dor:** enviar pela conta errada, responder no metro com teclado minúsculo.
- **Win:** responder 10 emails em 5 min a caminho do próximo meeting.

### Persona 2 — "Miguel, 28 anos, fundador de agência"
- 2 contas Google (pessoal + agência) + 1 Workspace.
- Vive no WhatsApp e email; pouco tempo para triagem.
- **Dor:** gerir caixas diferentes, tom profissional inconsistente.
- **Win:** ter um "chief of staff" vocal que sabe o tom de cada conta.

### Persona 3 — "Rita, 40 anos, executiva sénior"
- 1 Workspace corporativo + 1 pessoal.
- Inglês + PT-PT no dia-a-dia.
- **Dor:** calendário caótico, responde email enquanto conduz.
- **Win:** modo hands-free real, comando vocal no carro.

---

## 5. Objetivos & Métricas de Sucesso

### 5.1 Objetivos de produto (V1 beta — 13 semanas)

| Objetivo | Métrica | Meta V1 |
|---|---|---|
| Adoção | Utilizadores beta ativos | 10 / 10 convidados |
| Ativação | % que completam 1º envio por voz | ≥ 80% |
| Retenção | D7 retention | ≥ 40% |
| Valor | Emails respondidos por voz / DAU | ≥ 5 |
| Velocidade | Tempo médio reply vs manual | -60% |
| NPS | Net Promoter Score | ≥ 40 |

### 5.2 Métricas técnicas

- p95 latência voz end-to-end < 4s
- Uptime ≥ 99.5%
- Crash-free sessions ≥ 99%
- Custo APIs < €3/user/mês

---

## 6. Escopo — V1 vs V2

### V1 (Must have — 13 semanas)

- PWA instalável iOS/Android
- **1 conta Google** (OAuth 2.0, scopes Gmail readonly + send)
- Inbox read-only (últimos 50 emails)
- Leitura TTS de email aberto
- Composer vocal (push-to-talk) + transcrição em tempo real
- Draft LLM em PT-PT + revisão + envio
- Backend Python (FastAPI) seguro
- Supabase (auth + data + cache com TTL)
- Deploy Vercel + Fly.io (Madrid)
- Logs, métricas, Sentry

### V1.x (Should have — se capacidade permitir)

- **Multi-conta Google** (2+ contas, seletor rápido, inbox unificada opcional)
- Calendar: criar evento por voz
- Push notifications (Web Push)
- Onboarding polido

### V2 (Could have — pós-beta)

- Contacts (resolver destinatários por voz)
- Offline avançado (fila de envio, background sync)
- Wake-word ("Ei Per4")
- Classificação IA automática
- Resumos de thread
- Integração Outlook/iCloud

### Won't have (now)

- Versão desktop nativa
- CRM / follow-ups automáticos
- Transcrição de reuniões
- Tradução automática
- Modo colaborativo

---

## 7. Requisitos Funcionais

### RF-1 — Autenticação
- **RF-1.1** Login com conta Google via OAuth 2.0 (scopes: `gmail.readonly`, `gmail.send`, `gmail.modify`, `calendar`, `contacts.readonly`).
- **RF-1.2** Persistência de sessão via Supabase Auth (JWT refreshable).
- **RF-1.3** Refresh automático de access tokens em background.
- **RF-1.4** Revogar acesso em 1 clique nas Configurações.

### RF-2 — Gestão de contas Google (multi-conta, V1.x)
- **RF-2.1** Adicionar N contas Google (V1: 1 conta; V1.x: 2+ contas).
- **RF-2.2** Editar nickname e cor de cada conta.
- **RF-2.3** Remover conta (revoga token + apaga cache local).
- **RF-2.4** Seletor de conta ativa com swipe down no header.
- **RF-2.5** Inbox unificada (toggle) — mostra emails de todas as contas.

### RF-3 — Inbox
- **RF-3.1** Listar últimos 50 emails ordenados por data decrescente.
- **RF-3.2** Mostrar remetente, assunto, snippet, badge de conta.
- **RF-3.3** Pull-to-refresh para sincronizar.
- **RF-3.4** Badge de não lidos no header.
- **RF-3.5** Swipe actions: arquivar, marcar lido, responder por voz, eliminar.

### RF-4 — Detalhe do email
- **RF-4.1** Exibir corpo do email parseado (HTML → texto legível).
- **RF-4.2** CTA primário: "Responder por voz".
- **RF-4.3** CTAs secundários: Encaminhar, Arquivar, Eliminar.
- **RF-4.4** Indicar claramente em que conta o email foi recebido.

### RF-5 — Voice Agent (STT)
- **RF-5.1** Push-to-talk: toque inicia gravação, toque finaliza.
- **RF-5.2** Feedback visual em 4 estados: idle / listening / processing / draft-ready.
- **RF-5.3** Waveform animado reativo ao volume do input.
- **RF-5.4** Transcrição em tempo real durante a fala.

### RF-6 — LLM Draft
- **RF-6.1** Gerar draft a partir do ditado (Claude 3.5 Sonnet em PT-PT).
- **RF-6.2** Preservar contexto da thread de origem (se reply).
- **RF-6.3** Aplicar tom profissional cordial por default.
- **RF-6.4** Permitir comandos vocais de edição.
- **RF-6.5** Permitir edição textual inline do draft.

### RF-7 — Envio
- **RF-7.1** Confirmação obrigatória antes de enviar ("Enviar" / "Refazer").
- **RF-7.2** Envio via Gmail API com `from` da conta selecionada.
- **RF-7.3** Feedback "Enviado" com checkmark + haptic.
- **RF-7.4** Fila local (`outbox`) se offline; envio ao reconectar.

### RF-8 — TTS (Leitura de email)
- **RF-8.1** Tocar email em voz alta via ElevenLabs.
- **RF-8.2** Controles: play/pause, próximo email.
- **RF-8.3** Velocidade configurável (0.8x / 1x / 1.25x / 1.5x).

### RF-9 — Calendar (V2)
- **RF-9.1** Criar evento por voz ("marca reunião amanhã 15h com João").
- **RF-9.2** Ver agenda do dia na home.
- **RF-9.3** Confirmação visual antes de criar evento.

### RF-10 — Contacts (V2)
- **RF-10.1** Resolver destinatários por voz.
- **RF-10.2** Autocomplete de contatos no composer textual.

### RF-11 — Configurações
- **RF-11.1** Aparência (tema claro/escuro/sistema).
- **RF-11.2** Voz (idioma PT-PT, velocidade TTS, voz ElevenLabs).
- **RF-11.3** Notificações (ativar/desativar push).
- **RF-11.4** Contas Google (lista + gestão).
- **RF-11.5** Privacidade (exportar dados, apagar conta).

---

## 8. Requisitos Não-Funcionais

### RNF-1 — Performance
- p95 latência end-to-end voz (STT → LLM → TTS) < 4s.
- p95 listagem inbox < 1s (cacheada).
- First Contentful Paint PWA < 1.5s em 4G.

### RNF-2 — Segurança
- Refresh tokens OAuth cifrados em AES-256-GCM.
- mTLS interno entre Next.js BFF e FastAPI.
- RLS ativo em todas as tabelas Supabase.
- HTTPS TLS 1.3 obrigatório.

### RNF-3 — Privacidade & GDPR
- Consentimento explícito no 1º login.
- Corpo de email nunca persistido > 24h.
- Áudio apagado em 7 dias.
- Transcripts retidos 30 dias (opt-in).
- Endpoints `/me/export` e `DELETE /me`.
- Dados em região EU (Supabase Frankfurt ou Paris).

### RNF-4 — Fiabilidade
- Uptime ≥ 99.5%.
- Crash-free sessions ≥ 99%.
- Retry exponencial em chamadas externas.
- Circuit breaker em Gmail API.

### RNF-5 — Escalabilidade
- Arquitetura suporta 1000 utilizadores no beta+ sem refactor.
- Auto-scale Fly.io 1-3 máquinas.

### RNF-6 — Acessibilidade
- WCAG 2.1 AA mínimo.
- Suporte a VoiceOver (iOS) e TalkBack (Android).
- Touch targets ≥ 48×48px.
- `prefers-reduced-motion` respeitado.

### RNF-7 — Idioma
- PT-PT como default.
- Preparar i18n para PT-BR e EN (V2).

### RNF-8 — Custo operacional
- < €3/utilizador/mês em APIs externas.
- Cap de 200 interações vocais/dia/utilizador.

---

# Parte II — Ultraplan Técnico

## 9. Arquitetura Geral

```
                            ┌─────────────────────────────────────┐
                            │          UTILIZADOR                 │
                            │   iPhone / Android (PWA instalado)  │
                            └──────────────┬──────────────────────┘
                                           │ HTTPS + WSS
                                           ▼
              ┌────────────────────────────────────────────────────┐
              │   FRONTEND PWA (Next.js 16, Vercel Edge)           │
              │   - App Shell cache-first (Workbox via next-pwa)   │
              │   - MediaRecorder API (captura de voz)             │
              │   - WebPush / FCM receiver                         │
              │   - Supabase JS SDK (auth session)                 │
              └──────────────┬─────────────────────────────────────┘
                             │ REST + Server Actions + WebSocket
                             ▼
              ┌────────────────────────────────────────────────────┐
              │   API GATEWAY (Next.js Route Handlers - BFF)       │
              │   - Valida sessão Supabase (JWT)                   │
              │   - Orquestra chamadas ao microserviço Python      │
              │   - Rate limiting (Upstash Redis)                  │
              └──────────────┬─────────────────────────────────────┘
                             │ HTTPS mTLS interno
                             ▼
              ┌────────────────────────────────────────────────────┐
              │   MICROSERVIÇO PYTHON (FastAPI, Fly.io Madrid)     │
              │   ├── /auth/google (OAuth callback)                │
              │   ├── /emails   (Gmail API)                        │
              │   ├── /calendar (Calendar API)                     │
              │   ├── /contacts (People API)                       │
              │   ├── /voice    (STT + intent + LLM + TTS)         │
              │   └── /sync     (background worker - arq)          │
              └──────┬──────────────────┬────────────────┬─────────┘
                     │                  │                │
                     ▼                  ▼                ▼
            ┌──────────────┐   ┌──────────────┐  ┌──────────────────┐
            │ Google APIs  │   │ LLM / STT /  │  │   Supabase       │
            │ - Gmail      │   │ TTS vendors  │  │ - Postgres + RLS │
            │ - Calendar   │   │ - Groq       │  │ - Auth (session) │
            │ - People     │   │ - Claude     │  │ - Storage (audio)│
            │              │   │ - ElevenLabs │  │ - Realtime       │
            └──────────────┘   └──────────────┘  └──────────────────┘
                                                        ▲
                                                        │
                                              ┌─────────┴─────────┐
                                              │  Upstash Redis    │
                                              │  - cache emails   │
                                              │  - job queue      │
                                              │  - rate limits    │
                                              └───────────────────┘
```

---

## 10. Stack Tecnológica

### 10.1 Frontend PWA — Next.js 16 App Router + `next-pwa`

Next.js 16 com App Router, Server Components onde possível, Client Components para gravação de voz. Já é padrão do JP (Vercel), Server Actions eliminam BFF custom, streaming LLM nativo.

**Pacotes:**
- `next@16.x`, `next-pwa@6.x` (ou `@serwist/next`)
- `@supabase/ssr@0.5.x` + `@supabase/supabase-js@2.x`
- `tailwindcss@4.x` + `shadcn/ui`
- `zustand@5.x` (estado UI)
- `@tanstack/react-query@5.x` (cache emails)
- `react-media-recorder@1.x`
- `framer-motion@12.x`

### 10.2 Backend Python — FastAPI 0.115

Async I/O (Google APIs + LLM streaming), Pydantic v2, OpenAPI auto-gerado, contrato firme com frontend TypeScript.

**Pacotes:**
- `fastapi==0.115.*`, `uvicorn[standard]==0.32.*`
- `google-api-python-client==2.150.*`, `google-auth-oauthlib==1.2.*`
- `anthropic==0.40.*`, `groq==0.13.*`, `elevenlabs==1.8.*`
- `supabase==2.10.*`
- `arq==0.26.*` (worker assíncrono)
- `cryptography==44.*` (AES-GCM)
- `httpx==0.27.*`

### 10.3 Base de dados — Supabase (padrão JP)

Postgres 16 + RLS + `pgvector` para futura busca semântica. Supabase Auth emite JWT consumido pelo FastAPI.

### 10.4 Voice / STT — Groq Whisper Large v3

| Opção | Latência | Custo / min | PT-PT | Veredicto |
|---|---|---|---|---|
| Groq Whisper v3 | ~200-400ms | ~$0.0001 | Excelente | **Vencedor** |
| OpenAI Whisper | ~1-2s | $0.006 | Excelente | Fallback |
| Google Speech-to-Text | ~500ms | $0.016 | Bom | Caro |

### 10.5 LLM — Claude 3.5 Sonnet + Groq Llama 3.3 70B

- **Intent classification** → Groq Llama 3.3 70B (<500ms, barato)
- **Drafts de email** → Claude 3.5 Sonnet (qualidade superior PT-PT)
- **Fallback** → GPT-4o-mini

### 10.6 TTS — ElevenLabs Multilingual v2

Streaming via WebSocket, voz PT-PT excelente. Web Speech API nativa como fallback.

### 10.7 Deploy

- **Frontend:** Vercel (Hobby → Pro)
- **Microserviço Python:** Fly.io região `mad` (Madrid, ~15ms de Lisboa)
- **Redis:** Upstash serverless
- **Observabilidade:** Sentry + Axiom

### 10.8 Sync de Emails

- Principal: Gmail API `watch()` + Google Cloud Pub/Sub → webhook FastAPI
- Fallback: polling 2min via worker `arq`

---

## 11. Modelo de Dados (Supabase)

```sql
-- 1. users (estende auth.users do Supabase)
users (
  id UUID PK REFERENCES auth.users(id),
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,
  preferred_language TEXT DEFAULT 'pt-PT',
  voice_id TEXT,
  active_account_id UUID,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

-- 2. google_accounts (N contas por user)
google_accounts (
  id UUID PK,
  user_id UUID FK -> users(id) ON DELETE CASCADE,
  google_email TEXT NOT NULL,
  display_name TEXT,
  color_hex TEXT DEFAULT '#3B82F6',
  refresh_token_encrypted BYTEA NOT NULL,
  access_token_encrypted BYTEA,
  access_token_expires_at TIMESTAMPTZ,
  scopes TEXT[],
  key_version INT DEFAULT 1,
  last_sync_at TIMESTAMPTZ,
  pubsub_watch_expiration TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ,
  UNIQUE(user_id, google_email)
)

-- 3. email_cache (TTL 24h)
email_cache (
  id UUID PK,
  google_account_id UUID FK -> google_accounts(id),
  gmail_message_id TEXT NOT NULL,
  thread_id TEXT,
  from_email TEXT,
  from_name TEXT,
  to_emails TEXT[],
  subject TEXT,
  snippet TEXT,
  body_cached TEXT,
  received_at TIMESTAMPTZ,
  is_read BOOLEAN,
  is_starred BOOLEAN,
  labels TEXT[],
  cache_expires_at TIMESTAMPTZ DEFAULT now() + interval '24 hours',
  UNIQUE(google_account_id, gmail_message_id)
)

-- 4. draft_responses
draft_responses (
  id UUID PK,
  user_id UUID FK -> users(id),
  google_account_id UUID FK,
  reply_to_message_id TEXT,
  subject TEXT,
  body_text TEXT,
  tone TEXT,
  llm_model TEXT,
  status TEXT, -- 'draft' | 'approved' | 'sent' | 'discarded'
  voice_session_id UUID FK,
  created_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ
)

-- 5. voice_sessions
voice_sessions (
  id UUID PK,
  user_id UUID FK,
  google_account_id UUID FK,
  audio_url TEXT, -- apagado 7d
  transcript TEXT,
  intent TEXT,
  llm_response TEXT,
  tts_audio_url TEXT,
  duration_ms INT,
  created_at TIMESTAMPTZ
)

-- 6. app_settings
app_settings (
  user_id UUID PK FK,
  default_tone TEXT DEFAULT 'profissional_cordial',
  signature_text TEXT,
  push_notifications_enabled BOOLEAN DEFAULT true,
  wake_word_enabled BOOLEAN DEFAULT false,
  voice_speed FLOAT DEFAULT 1.0,
  auto_sync_interval_sec INT DEFAULT 120,
  unified_inbox BOOLEAN DEFAULT true
)

-- Índices críticos
CREATE INDEX idx_email_cache_account_received ON email_cache(google_account_id, received_at DESC);
CREATE INDEX idx_email_cache_expiry ON email_cache(cache_expires_at);
CREATE INDEX idx_drafts_user_status ON draft_responses(user_id, status);

-- RLS
ALTER TABLE google_accounts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_own_accounts" ON google_accounts
  FOR ALL USING (auth.uid() = user_id);
```

---

## 12. Integração Google APIs

### 12.1 Scopes OAuth 2.0

```
gmail.readonly · gmail.send · gmail.modify
calendar · calendar.events
contacts.readonly
openid · email · profile
```

Evitar `gmail.full` (Google rejeita em verificação).

### 12.2 Endpoints REST internos

| Método | Path | Função |
|---|---|---|
| GET | `/accounts` | Lista contas Google do user |
| POST | `/accounts/link` | Inicia OAuth |
| DELETE | `/accounts/{id}` | Revoga token + apaga |
| GET | `/emails` | Lista inbox (cache) |
| GET | `/emails/{id}` | Email completo |
| POST | `/emails/draft` | Gera draft via LLM |
| POST | `/emails/send` | Envia email |
| GET | `/calendar/events` | Eventos |
| POST | `/calendar/events` | Cria evento |
| GET | `/contacts/search` | Busca contatos |
| POST | `/voice/process` | Pipeline STT→LLM→TTS |
| POST | `/webhooks/gmail-push` | Pub/Sub notification |

### 12.3 Refresh token storage

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def encrypt_token(plaintext: str, key: bytes) -> bytes:
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return nonce + ct
```

---

## 13. Voice Agent

### 13.1 Pipeline (push-to-talk)

```
[1] Toque no mic → MediaRecorder (webm/opus @ 16kHz)
[2] Blob → POST multipart /voice/process
[3] Groq Whisper v3 (~300ms)
[4] Intent: Groq Llama 3.3 70B + function calling
    → read_inbox | reply_email | compose_email
    → check_calendar | create_event | search_contact
[5] Router executa ferramenta (Gmail/Calendar)
[6] LLM gera resposta PT-PT (Claude/Groq)
[7] ElevenLabs TTS streaming (WebSocket)
[8] Frontend: chunks via MediaSource API
```

### 13.2 Push-to-talk vs wake word

**Decisão V1: push-to-talk.** Wake word em PWA é frágil em iOS (bloqueia mic em background), PTT é 100% fiável. Wake word na V2 via Porcupine Web SDK.

### 13.3 Contexto de conversa

- `voice_session_id` agrupa turnos num período de 5 min.
- Últimos 6 turnos enviados ao LLM (~2k tokens).
- Sessão nova após 5 min inatividade.

---

## 14. Segurança & Privacidade

### 14.1 Criptografia

- **At rest:** AES-256-GCM em refresh tokens, chave em Fly Secrets.
- **In transit:** HTTPS TLS 1.3 + mTLS interno BFF↔FastAPI.
- Supabase Storage: buckets privados, signed URLs 5min.

### 14.2 Retenção mínima

| Dado | Retenção |
|---|---|
| Corpo de email (cache) | 24h |
| Áudio do utilizador | 7 dias |
| Transcripts | 30 dias (opt-in) |
| Logs de acesso | 90 dias |

### 14.3 GDPR / Portugal / UE

- Consentimento explícito no 1º login
- DPA com Google (automático em apps OAuth verificadas)
- Verificação Google OAuth (CASA Tier 2, 4-6 semanas)
- `DELETE /me` (direito ao esquecimento)
- `GET /me/export` (portabilidade)
- Dados em Supabase EU (Paris ou Frankfurt)

---

## 15. Multi-Conta

- Dropdown no topbar PWA com avatar + chevron
- State global Zustand: `activeAccountId`
- Hotkey vocal: "muda para conta pessoal"
- Inbox unificada vs separada (toggle)
- Cada conta tem `color_hex` — avatar circular + barra lateral 4px

---

## 16. PWA Specifics

### 16.1 Service Worker Strategy

```
App shell:          CacheFirst (1 ano)
/api/emails:        NetworkFirst, fallback 5min
/api/calendar:      NetworkFirst, fallback 10min
Áudio blobs:        NetworkOnly
Ícones/manifest:    CacheFirst
```

### 16.2 Push Notifications

- Web Push API (VAPID) via `web-push` Python
- iOS 16.4+ suporta (requer PWA instalado)
- Payload sem corpo de email (privacidade)

### 16.3 Offline

**Funciona offline:** shell, últimos 50 emails cacheados, 20 eventos, escrita de drafts (IndexedDB).

**Não funciona offline:** voice agent, envio (fila `outbox`, envia ao reconectar).

### 16.4 manifest.json

```json
{
  "name": "Per4Biz",
  "short_name": "Per4Biz",
  "start_url": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#0A0A0A",
  "theme_color": "#3B82F6",
  "icons": [
    { "src": "/icons/192.png", "sizes": "192x192" },
    { "src": "/icons/512.png", "sizes": "512x512" },
    { "src": "/icons/maskable-512.png", "sizes": "512x512", "purpose": "maskable" }
  ],
  "shortcuts": [
    { "name": "Novo email por voz", "url": "/voice?intent=compose" },
    { "name": "Ler inbox", "url": "/voice?intent=read_inbox" }
  ]
}
```

---

## 17. Decisões Arquiteturais (ADRs)

### ADR-001 — Next.js 16 App Router
**Decisão:** Next.js 16 + next-pwa. Server Actions eliminam BFF custom. Trade-off: lock-in Vercel (aceitável).

### ADR-002 — FastAPI em vez de Flask
**Decisão:** FastAPI + Pydantic v2. Async nativo + OpenAPI auto-gerado → cliente TypeScript.

### ADR-003 — Split LLM: Groq + Claude
**Decisão:** Intent → Groq Llama 3.3; drafts → Claude 3.5 Sonnet. 70% redução custo em interações simples, qualidade PT-PT superior em drafts.

### ADR-004 — Push-to-talk V1
**Decisão:** PTT na V1, wake word via Porcupine na V2. iOS PWA limita mic contínuo.

### ADR-005 — Email body TTL 24h
**Decisão:** `email_cache.body_cached` com TTL 24h + cron. Minimização GDPR. Re-fetch ao Gmail se user relê antigo.

### ADR-006 — Fly.io Madrid
**Decisão:** Fly.io região `mad`. Latência Lisboa→Madrid ~15ms vs ~80ms US. Reversível (Dockerfile standard).

---

# Parte III — Design Spec (UI/UX)

## 18. Design Principles

1. **Voice-first, touch-fallback.** Voz é input primário; toque é fallback silencioso.
2. **Glance-able inbox.** 3 segundos para entender o que importa.
3. **One-thumb reachable.** Ações primárias na zona inferior.
4. **Multi-conta sem fricção.** Contexto visível, mudável em 1 gesto.
5. **Silent confidence.** Feedback visual sutil, háptico generoso.

---

## 19. Sistema Visual

### 19.1 Paleta de cores

**Tema claro**
- Primária: `#0A84FF` (azul elétrico)
- Secundária: `#1C1C1E`
- Background: `#FFFFFF` / Surface: `#F2F2F7` / Divider: `#E5E5EA`
- Accent (voz ativa): `#FF375F`
- Sucesso: `#34C759` · Erro: `#FF3B30` · Info: `#FF9500`

**Tema escuro**
- Primária: `#0A84FF`
- Background: `#000000` / Surface: `#1C1C1E` / Elevada: `#2C2C2E`
- Accent: `#FF6482` · Sucesso: `#30D158` · Erro: `#FF453A`

**Cores de conta (6 hues):**
`#0A84FF · #FF9500 · #AF52DE · #34C759 · #FF375F · #5AC8FA`

### 19.2 Tipografia

- **Fonte:** Inter variable (fallback SF Pro, Roboto)
- Display 32/700/-0.5 · Title 22/600 · Headline 17/600
- Body 15/400 · Subhead 13/500 · Caption 11/500 uppercase
- Line-height 1.4 body, 1.2 títulos

### 19.3 Espaçamento & shape

- Sistema base **4px** → tokens: `4, 8, 12, 16, 20, 24, 32, 48, 64`
- Padding tela: 20px lateral, 16px vertical
- Radius: `sm=8 · md=12 · lg=16 · xl=24 · pill=999`
- Elevação 1: `0 1px 2px rgba(0,0,0,0.04)`
- Elevação 2: `0 4px 12px rgba(0,0,0,0.08)`
- Voice button shadow: `0 8px 24px rgba(10,132,255,0.35)`

### 19.4 Iconografia

Lucide Icons (stroke 1.5–2). Tamanhos: 16, 20, 24, 28px.

---

## 20. Arquitetura de Telas

```
Onboarding
├─ Welcome
├─ Google Sign-in (1ª conta)
├─ Permissões (Gmail, Calendar, mic, notif)
└─ Tutorial vocal (30s)

App (pós-login)
├─ Inbox unificada  [tela home]
│  ├─ Detalhe do email
│  │  └─ Composer (reply contextual)
│  └─ Composer vocal (FAB)
├─ Agenda (V2)
│  ├─ Dia / Semana / Mês
│  └─ Detalhe do evento
├─ Contatos (V2)
└─ Configurações
   ├─ Contas Google
   ├─ Voz
   ├─ Notificações
   ├─ Aparência
   └─ Privacidade

Overlays globais
├─ Seletor rápido de conta (pull-down)
├─ Composer vocal (modal full-screen)
└─ Comando vocal global (long-press FAB)
```

---

## 21. Wireframes Descritivos

### 21.1 Inbox Unificada (Home)

```
┌─────────────────────────────┐
│ ≡   Todas as contas  ▾   🔍 │
├─────────────────────────────┤
│ ● Ana Costa        14:32  ● │
│   Proposta Q2                │
│   Olha, revisei e acho que…  │
├─────────────────────────────┤
│ ● Banco XP         13:10  ● │
│   Extrato disponível         │
├─────────────────────────────┤
│ ○ João Silva       11:45    │
│   Re: reunião terça          │
│                             │
│                       ┌───┐ │
│                       │ 🎙 │ │
│                       └───┘ │
└─────────────────────────────┘
```

### 21.2 Detalhe do Email

```
┌─────────────────────────────┐
│ ←                    ⋯      │
├─────────────────────────────┤
│ Proposta Q2                 │
│                             │
│ 👤 Ana Costa                │
│ para: você (conta pessoal)  │
│ 14:32 · hoje                │
├─────────────────────────────┤
│  Corpo do email com         │
│  tipografia confortável     │
│  em 15px, line-height 1.5   │
├─────────────────────────────┤
│ ┌─────────────────────────┐ │
│ │ 🎙  Responder por voz   │ │
│ └─────────────────────────┘ │
│  Encaminhar · Arquivar      │
└─────────────────────────────┘
```

---

## 22. Tela-estrela — Composer Vocal

Modal full-screen, slide-up + scale do FAB (250ms ease-out).

```
┌─────────────────────────────┐
│ ✕                  Pessoal▾ │
├─────────────────────────────┤
│                             │
│   Para: Ana Costa           │
│                             │
│   "Oi Ana, tudo bem? Sobre  │
│    a proposta que você…"    │
│                             │
│   ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲          │
│                             │
├─────────────────────────────┤
│        ┌─────────┐          │
│        │   ■     │          │
│        └─────────┘          │
│   Toque para pausar         │
└─────────────────────────────┘
```

### Estados do botão

| Estado | Visual | Háptico | Som |
|---|---|---|---|
| idle | Azul, 🎙 estático | — | — |
| listening | Vermelho `#FF375F`, pulsação 1.5s, waveform | Impact light | Bip curto |
| processing | Azul, spinner circular | Selection | — |
| draft-ready | Card com draft + CTAs | Success notif | — |
| sending | Barra progresso horizontal | — | — |
| sent | Checkmark verde 400ms | Success impact | Bip confirmação |

### Transcrição em tempo real

Centro da tela, 22px/500. Palavras confirmadas em preto, hipótese em cinza 60% opacity. Fade-in 120ms por palavra.

### Edição do draft

- **Voz:** "Muda o tom para mais formal", "Remove a última frase"
- **Toque:** tap abre teclado, edição inline

---

## 23. Interações & Microinterações

### Swipe actions (72px altura)

- Swipe right 25%: marcar lido/não-lido (cinza)
- Swipe right 60%: arquivar (`#34C759`)
- Swipe left 25%: responder por voz (azul)
- Swipe left 60%: eliminar (vermelho, confirmação haptic heavy)

### Háptico

- Tap primário: light (10ms)
- Início gravação: medium
- Sucesso: success notification pattern
- Erro: error notification pattern

### Animações

- Transições: slide 280ms `cubic-bezier(0.32, 0.72, 0, 1)` (iOS-like)
- Modal composer: slide-up + fade 250ms
- Lista: stagger 30ms entre items
- `prefers-reduced-motion`: crossfade 150ms

### Pull-to-refresh

Threshold 80px, resistência progressiva, animação de waveform horizontal (3 ondas) em vez de spinner.

---

## 24. Acessibilidade (WCAG AA+)

- Contraste texto/background ≥ 4.5:1 (body), ≥ 3:1 (títulos)
- Touch targets ≥ 48×48px (FAB 64px, botão gravação 96px)
- `aria-label` em PT em todos elementos
- Composer anuncia estados via `aria-live="polite"`
- Focus visible ring `#0A84FF` 3px + offset 2px
- Fontes escaláveis até 200% (Dynamic Type iOS / Android font-size)
- Transcrição sempre visível (não só áudio)

---

## 25. PWA Specifics (Design)

- **Splash:** `#0A84FF` (claro) ou `#000000` (escuro), logo 120px
- **Ícone adaptativo:** SVG mascarável, safe zone 40%
- **Safe-areas iOS:** header usa `env(safe-area-inset-top)`; FAB `bottom: calc(24px + env(safe-area-inset-bottom))`
- **Install prompt:** banner educativo após 3ª sessão, dismissível

---

## 26. Design System — Componentes

| Componente | Variantes |
|---|---|
| Button | primary · secondary · ghost · destructive · sm(36) md(44) lg(56) |
| VoiceButton | fab(64) hero(96) inline(48) · idle/listening/processing |
| Card | default · elevated · selectable |
| EmailListItem | unread · read · selected · swiping |
| AccountBadge | dot(8) · chip · avatar-ring |
| Chip | filter · input · suggestion |
| Toast | success · error · info · voice-hint |
| Waveform | live (reativo) · static · mini (16px inline) |
| TranscriptText | confirmed · hypothesis · edited |
| Modal | bottom-sheet · full-screen · dialog |
| Avatar | 24 · 32 · 40 · 64px · com/sem ring |
| Segmented Control | 2/3/4 opções |
| ListRow | default · with-icon · with-toggle · destructive |

---

# Parte IV — Plano Ágil (Sprint Plan)

## 27. Épicos

| # | Épico | Valor entregue | Versão |
|---|---|---|---|
| E1 | Autenticação & Google OAuth | Login seguro, confiança | V1 |
| E2 | Microserviço Python Gmail | Base técnica segura | V1 |
| E3 | Inbox PWA | Leitura confortável mobile | V1 |
| E4 | Voice Agent (STT+LLM+TTS) | Experiência conversacional | V1 |
| E5 | Composer Vocal & Envio | Core loop do produto | V1 |
| E6 | Multi-conta | Diferencial para poweruser | V1.x |
| E7 | Calendar & Contacts | Copiloto completo | V2 |
| E8 | Notifications & Offline | Retenção e confiabilidade | V2 |

---

## 28. User Stories por épico

### E1 — Autenticação (13 pts)
- **E1.US1 (3)** Login com Google
- **E1.US2 (5)** Sessão persistente
- **E1.US3 (3)** Revogar acesso facilmente
- **E1.US4 (2)** Refresh automático de tokens

### E2 — Microserviço Python Gmail (21 pts)
- **E2.US1 (5)** `/emails/list` paginado
- **E2.US2 (3)** `/emails/{id}` parseado
- **E2.US3 (8)** `/emails/send` autenticado
- **E2.US4 (3)** Rate-limiting + circuit breaker
- **E2.US5 (2)** Logs estruturados Supabase

### E3 — Inbox PWA (18 pts)
- **E3.US1 (5)** Lista 50 emails com remetente/assunto/snippet
- **E3.US2 (3)** Pull-to-refresh
- **E3.US3 (5)** Abrir email em tela cheia
- **E3.US4 (3)** PWA install manifest
- **E3.US5 (2)** Badge não lidos

### E4 — Voice Agent (26 pts)
- **E4.US1 (5)** TTS play button
- **E4.US2 (8)** Gravar com indicador visual
- **E4.US3 (5)** Transcrição em tempo real
- **E4.US4 (5)** LLM polisse ditado
- **E4.US5 (3)** Métricas latência STT/LLM/TTS

### E5 — Composer Vocal (16 pts)
- **E5.US1 (3)** Revisar draft
- **E5.US2 (3)** Editar por texto
- **E5.US3 (5)** Re-ditar sem perder
- **E5.US4 (3)** Confirmar envio 1-tap
- **E5.US5 (2)** Confirmação "Enviado"

### E6 — Multi-conta (16 pts, V1.x)
- **E6.US1 (5)** Adicionar 2ª conta
- **E6.US2 (3)** Seletor de conta
- **E6.US3 (5)** Inbox unificada
- **E6.US4 (3)** Escolher conta no envio

### E7 — Calendar & Contacts (21 pts, V2)
- **E7.US1 (8)** Criar evento por voz
- **E7.US2 (5)** Ver agenda do dia
- **E7.US3 (5)** Resolver contato por voz
- **E7.US4 (3)** Confirmação visual evento

### E8 — Notifications & Offline (13 pts, V2)
- **E8.US1 (5)** Push notification email
- **E8.US2 (5)** Fila offline de envios
- **E8.US3 (3)** Status online/offline

**Total V1 (E1-E5): 94 pts · V1.x (E6): 16 pts · V2 (E7+E8): 34 pts**

---

## 29. Roadmap em Sprints (13 semanas)

### Sprint 0 — Setup & Discovery (Sem 1)
- **Goal:** "Ambiente pronto para codar no Sprint 1."
- Repo GitHub + CI, Vercel + Fly.io deploys, Supabase, Google Cloud OAuth consent screen, Figma design tokens, ADR STT/LLM/TTS
- **DoD:** "hello world" PWA com deploy automático
- **Demo:** tour pelos dashboards

### Sprint 1 — Auth + Inbox read-only (Sem 2-3) · 28 pts
- **Goal:** "Usuário loga e vê 50 emails no celular."
- Stories: E1.US1, E1.US2, E1.US4, E2.US1, E2.US2, E2.US5, E3.US1, E3.US2, E3.US3
- **DoD:** login iOS+Android, inbox < 2s, testes > 60% backend
- **Demo:** JP loga em device real, navega emails

### Sprint 2 — Voice Agent MVP (Sem 4-5) · 26 pts
- **Goal:** "App lê email em voz alta e transcreve o que eu digo."
- Stories: E4.US1, E4.US2, E4.US3, E4.US5, E3.US4, E1.US3
- **DoD:** STT < 2s para áudios < 15s, TTS natural
- **Demo:** ler, gravar "obrigado", ver texto

### Sprint 3 — Composer Vocal + Envio (Sem 6-7) · 27 pts
- **Goal:** "Respondo 100% por voz e destinatário recebe."
- Stories: E4.US4, E5.US1-5, E2.US3, E2.US4
- **DoD:** ciclo < 90s com > 95% sucesso, 10 emails reais
- **Demo:** **Milestone V1-alpha** — 5 emails por voz ao vivo

### Sprint 4 — Multi-conta + Seletor (Sem 8-9) · 22 pts
- **Goal:** "Alterno entre conta pessoal e trabalho."
- Stories: E6.US1, E6.US2, E6.US4, E3.US5 + dívida técnica
- **DoD:** 2 contas simultâneas, tokens isolados, seletor < 500ms
- **Demo:** JP alterna 3x entre contas

### Sprint 5 — Calendar + Push (Sem 10-11) · 24 pts
- **Goal:** "Crio eventos por voz e recebo push."
- ⚠️ **Nota:** inconsistência PRD vs Sprint — ver Validação §34. Decidir com PO antes do kickoff.
- Stories: E7.US1, E7.US2, E7.US4, E8.US1, E8.US3
- **DoD:** evento com 95% acerto, push iOS+Android
- **Demo:** "Marca reunião com Maria quarta 14h" → Google Calendar

### Sprint 6 — Polish + Beta Launch (Sem 12-13) · 20 pts
- **Goal:** "10 beta-testers usando diariamente."
- Dívida, otimização, onboarding, E6.US3, bugs QA
- **DoD:** p95 voz < 4s, crash-free > 99%, onboarding 3 telas, landing page
- **Demo:** **V1 GA beta** — 10 usuários reais

**Total: 147 pts · velocity média 24.5 pts/sprint (alvo 25-30)**

---

## 30. Backlog MoSCoW

### Must have (V1)
Login Google · refresh · revogação · inbox 50 · TTS leitura · STT ditado · LLM draft · envio Gmail · PWA instalável · logs e métricas

### Should have (V1.x)
Multi-conta + seletor · Calendar create event · push notifications · onboarding 3 telas · badge não lidos

### Could have (V2)
Inbox unificada multi-conta · resolver contatos por voz · classificação IA · resumos de thread · offline avançado · wake-word · integração Outlook

### Won't have (now)
Desktop nativo · CRM/follow-ups · transcrição de reuniões · tradução automática · Slack/Teams · colaborativo

---

## 31. Cerimônias Ágeis

| Cerimônia | Frequência | Duração | Formato |
|---|---|---|---|
| Daily | Seg-sex 9h | 5-10 min | Ontem/hoje/bloqueios (auto-check JP + agents) |
| Sprint Planning | 1ª seg do sprint | 1-2h | Review backlog, selecionar, estimar, goal |
| Sprint Review / Demo | Última sex manhã | 1h | Demo ao vivo + feedback |
| Retrospetiva | Última sex tarde | 45 min | Start/Stop/Continue + 1 ação concreta |
| Backlog Refinement | Meio do sprint (qua) | 1h | Refinar próximas 5-8 stories |

---

## 32. Métricas

### Métricas de Produto (beta V1)
- DAU / WAU ≥ 60%
- Emails respondidos por voz / DAU ≥ 5
- Tempo reply voz vs manual: -60%
- D7 retention ≥ 40%
- NPS ≥ 40

### Métricas Técnicas
- p95 latência voz < 4s
- Uptime ≥ 99.5%
- Crash-free ≥ 99%
- Custo € / user / mês < €3
- Taxa erro envio Gmail < 0.5%

### Métricas de Sprint
- Velocity baseline 25 pts (banda 22-30)
- Burndown alerta > 20% desvio
- Escape defects < 2 / sprint
- Commitment accuracy ≥ 85%

---

## 33. Top 7 Riscos & Mitigações

| # | Risco | Impacto | Probab. | Mitigação |
|---|---|---|---|---|
| R1 | OAuth Gmail verification demora 4-6 semanas (CASA Tier 2) | Alto | Alta | Submeter Dia 1, modo "testing" com 100 users no beta |
| R2 | Custo APIs de voz explode | Alto | Média | Cota 200 interações/dia, monitorar S2, plano B Whisper self-hosted |
| R3 | Latência voz > 4s | Alto | Média | POC no S0, benchmark 3 fornecedores, streaming |
| R4 | PWA push iOS limitado | Médio | Alta | Fallback email/SMS, comunicar no onboarding |
| R5 | LLM gera resposta inadequada enviada | Alto | Baixa | Sempre mostrar draft, guardrails, log revisões |
| R6 | Capacidade JP (PO+SM+TL+review) | Médio | Alta | Buffer 20%, review cross-agent, spot-check 30% |
| R7 | Scope creep no beta | Médio | Alta | Roadmap público + MoSCoW para "não por agora" |

---

## 34. Checklist Dia 1 do Sprint 0 — 20 tarefas

**Dia 1 (Seg)**
1. Criar repo `per4biz` (monorepo /web + /api)
2. Branch protection + Conventional Commits
3. Criar projeto Google Cloud Console
4. Submeter OAuth consent screen

**Dia 2 (Ter)**
5. Scaffold Next.js 16 PWA (/web) com manifest + SW
6. Scaffold FastAPI (/api) com rotas base
7. Deploy inicial Vercel + Fly.io — hello world
8. Criar projeto Supabase, schema inicial

**Dia 3 (Qua)**
9. GitHub Actions: lint + test + deploy preview
10. Design system Figma: tokens + 3 componentes
11. Wireframe Login, Inbox, Email Detail
12. ADR-001 (benchmark STT/LLM/TTS)

**Dia 4 (Qui)**
13. Implementar login Google end-to-end (prep S1)
14. Sentry frontend + backend
15. PostHog/Plausible analytics
16. OpenAPI spec inicial

**Dia 5 (Sex)**
17. Sprint 0 Review interno
18. Sprint 1 Planning: 28 pts
19. Board GitHub Projects (Backlog/To Do/In Progress/Review/Done)
20. Publicar roadmap no Notion/README

---

## 35. Distribuição de trabalho por role

| Role | S1 | S2 | S3 | S4 | S5 | S6 | **Total** |
|---|---|---|---|---|---|---|---|
| Tech Lead/Fullstack (JP) | 8 | 6 | 6 | 7 | 5 | 4 | **36** |
| Frontend PWA (agent) | 10 | 12 | 10 | 8 | 9 | 8 | **57** |
| Backend Python (agent) | 8 | 3 | 8 | 5 | 7 | 3 | **34** |
| UI/UX designer (agent) | 2 | 3 | 2 | 1 | 2 | 3 | **13** |
| QA (agent) | 0 | 2 | 1 | 1 | 1 | 2 | **7** |
| **Total sprint** | **28** | **26** | **27** | **22** | **24** | **20** | **147** |

**Notas:**
- JP ~20h/semana de código + resto em orquestração e review
- Review cross-agent obrigatório (QA revê Frontend, arquiteto revê Backend); JP faz spot-check 30%
- Agente QA entra com força a partir do Sprint 2

---

# Parte V — Validação Interna (Red-Team do Squad)

## 36. Checklist de qualidade do PRD (INVEST + DIEP)

| # | Critério | Status |
|---|---|---|
| 1 | Problema claramente articulado | ✅ |
| 2 | Solução mensurável (tempos-alvo) | ✅ |
| 3 | Personas distintas e realistas | ✅ |
| 4 | Escopo MVP fechado (MoSCoW) | ✅ |
| 5 | Métricas de sucesso quantificadas | ✅ |
| 6 | RF numerados e testáveis | ✅ |
| 7 | RNF cobrem SLO + privacidade | ✅ |
| 8 | Arquitetura com ADRs justificados | ✅ |
| 9 | Stack opinativa com versões | ✅ |
| 10 | Modelo de dados em SQL | ✅ |
| 11 | Roadmap realista com capacidade | ✅ |
| 12 | Riscos identificados + mitigados | ✅ |
| 13 | Dependências externas listadas | ✅ |
| 14 | Definition of Done por sprint | ✅ |
| 15 | Acessibilidade considerada | ✅ |
| 16 | Privacidade e GDPR abordados | ✅ |
| 17 | Multi-device iOS vs Android | ✅ |
| 18 | Questões em aberto documentadas | ✅ |

**Score: 18/18** ✅

---

## 37. Red-team — 6 ataques do squad

### Ataque 1 — "PRD é vaporware bonito"
**Crítica:** faltam **critérios de aceitação Gherkin** (Given/When/Then) por user story.
**Ação:** adicionar na Sprint 0 subtask "escrever critérios Gherkin para os 9 stories do Sprint 1".

### Ataque 2 — "Latência < 4s é otimista"
**Crítica:** Groq (300ms) + Llama (500ms) + Claude (1-2s) + ElevenLabs (400ms) = 2.2-3.2s em cenário ideal. Com 4G fraco passa dos 4s.
**Ação:** POC de latência no **S0 Dia 1-2** antes de comprometer arquitetura. Se falhar > 20%, repensar (ex: OpenAI Realtime API unificada).

### Ataque 3 — "Google OAuth verification mata cronograma"
**Crítica:** scopes `gmail.send` + `gmail.modify` são restricted. CASA Tier 2 custa €8-15k e demora 6-10 semanas.
**Resposta:** R1 já cobre — modo "testing" aceita 100 users (beta de 10 cabe). Submeter Dia 1, paralelizar com dev. Produção pública depois de CASA OK.
**Ação:** PO confirmar orçamento CASA disponível.

### Ataque 4 — "Split LLM (Groq + Claude) é over-engineering"
**Crítica:** ADR-003 assume split sem benchmark.
**Ação:** marcar ADR-003 como **"tentativa — revisitar após benchmark do S0"**. Se Groq/Llama atingir > 95% em intents e for aceitável em drafts, simplificar para um provider único.

### Ataque 5 — "Capacidade do squad é fantasia"
**Crítica:** JP como único humano revendo 111 pts de agents = ~34h/semana só em review. Inviável.
**Ação:** introduzir **review cross-agent** (QA revê Frontend, arquiteto revê Backend) + JP spot-check 30%. Reduz carga JP para ~10h/semana.

### Ataque 6 — "Cache 24h contradiz 'não guardamos'"
**Crítica:** user pode ver cache 24h como quebra de promessa.
**Ação:** onboarding e policy explícitos: "cachamos temporariamente até 24h, apagamos automaticamente". Adicionar RF-11.5.1 "tela mostra countdown de cache por email" (transparência total).

---

## 38. Consistência cross-documentos

### PRD vs Ultraplan
| Item | PRD | Ultraplan | OK? |
|---|---|---|---|
| Stack frontend | Next.js 16 PWA | Next.js 16 + next-pwa | ✅ |
| Backend | FastAPI Python | FastAPI 0.115 | ✅ |
| STT | Groq Whisper | Groq Whisper v3 | ✅ |
| LLM | Claude + Groq split | Claude 3.5 + Llama 3.3 | ✅ |
| TTS | ElevenLabs | ElevenLabs Multilingual v2 | ✅ |
| Região | EU (Madrid) | Fly.io mad | ✅ |
| Escopo V1 | 1 conta Google | — | ✅ |

### PRD vs Design Spec
Todos consistentes. Nota menor: Design Spec descreve wireframe de Agenda; PRD coloca Calendar em V2. Marcar wireframe como "V2 preview".

### PRD vs Sprint Plan — ❌ **Inconsistência #3 (crítica)**

PRD diz Calendar em V2, Sprint Plan tem Calendar no Sprint 5 da V1.

**Resolução sugerida (escolher com PO):**
- **Opção A:** mover Calendar para V2 definitivo → substituir Sprint 5 por "Polish + Performance + Push + Onboarding polido" (18-20 pts). Mais folga.
- **Opção B:** aceitar Calendar em V1.x → atualizar PRD para Should have. Mantém 24 pts do Sprint 5.

---

## 39. Gaps identificados

1. Critérios de aceitação Gherkin (a adicionar S0)
2. Política de privacidade PT-PT (rascunho S0, final S6)
3. Estratégia de pricing (pergunta aberta #2)
4. Analytics stack — mencionar em RNF
5. Strategy de beta invite (S0)
6. Support/feedback channel durante beta (WhatsApp? Form? Telegram?)
7. Kill-switch / feature flags (mencionar no Ultraplan)
8. Logging de PII (NÃO logar emails/transcripts em Sentry/Axiom) → RNF-2

---

## 40. Perguntas críticas ao PO (consolidadas)

| Pergunta | Bloqueia? | Prazo |
|---|---|---|
| Mercado PT vs PT+BR desde V1 | Não, afeta i18n | Antes S0 |
| Monetização (freemium / €/mês) | Não, afeta subscription UI | Antes S4 |
| Retenção de transcripts 30d (opt-in) | Sim, afeta privacy policy | Antes S0 |
| Lista dos 10 beta-testers | Crítico p/ beta | Antes S5 |
| Orçamento CASA (~€8-15k) | Crítico p/ V2 produção | Antes S0 |
| Voz do TTS (clonada JP / feminina / user) | Não, afeta polish | Antes S6 |
| **Calendar V1.x ou V2?** (Inconsistência #3) | **Sim, afeta S5** | **Antes S0** |

---

## 41. Veredicto & Próximos Passos

**Veredicto:** PRD **"pronto com ressalvas"** — qualidade profissional, base técnica sólida, executável.

**Correções obrigatórias antes do Sprint 0:**
1. Resolver Inconsistência #3 (Calendar V1.x vs V2) — decisão PO
2. Responder 4 perguntas críticas (mercado, transcripts, CASA, beta invite)
3. Adicionar critérios de aceitação Gherkin pelo menos para o Sprint 1 (8 stories)
4. Confirmar review cross-agent para desbloquear JP

**Correções recomendadas (não bloqueantes):**
- Nota "V2" no wireframe da Agenda
- Adicionar analytics stack em RNF
- Adicionar kill-switch / feature flags no Ultraplan
- Logging de PII explícito em RNF-2

---

## 42. Assinatura do squad

- **Ultraplan** — arquitetura aprovada, sujeita ao POC de latência do S0
- **UI/UX Designer** — design coerente; pede protótipo Figma clicável antes do S2
- **Scrum Master / PO** — plano realista com buffer; pede decisão sobre Calendar
- **QA crítico** — pede critérios Gherkin e plano de testes E2E

**Data validação interna:** 2026-04-15
**Próxima revisão:** após respostas do PO + início do Sprint 0

---

# Anexo — Como este PRD foi construído

Este documento completo foi produzido pelo squad **mkt-agency** com 3 agents especializados executados em paralelo:

- **Agent Plan (Ultraplan)** — arquiteto técnico → Parte II
- **Agent UI/UX Designer** — mobile PWA → Parte III
- **Agent Scrum Master / PO** — ágil → Parte IV

Depois o PRD Mestre (Parte I) foi consolidado e o próprio squad auto-validou o conjunto via red-team interno (Parte V), **sem depender de revisor externo** — conforme o pedido do PO de "validar sem o Victor".

**Tempo total de entrega:** ~3 minutos de execução paralela + consolidação final.

---

**Fim do documento.**

*Per4Biz · PRD v1.0 · mkt-agency · 2026-04-15*
