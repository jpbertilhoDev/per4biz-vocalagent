# Per4Biz — Plano Ágil Completo (V1) — v2.0 Chat-First

**Produto:** Per4Biz — Agente vocal de email multi-conta Google
**Squad:** mkt-agency
**Product Owner / Scrum Master:** JP Bertilho
**Data de kickoff:** Semana 1 (2026-04-20)
**Data-alvo V1 (self-use):** Semana 9 (2026-06-22)
**Versão do documento:** 2.0 — 2026-04-16 (pivot chat-first + redesign visual)

> **Mudança v2.0:** Pivot de inbox-first para chat-first. O agente **Vox** é a tela principal. E1-E5 (inbox-first) já implementados — frontend será redesenhado. Paleta mudou para dark-first violet+cyan. Sem beta externo — JP é user único.

---

## 1. Visão do MVP e escopo

### Visão do Produto
Per4Biz é um agente vocal mobile-first que transforma o celular num assistente executivo: o utilizador fala com o **Vox**, e o Vox lê emails, responde, e gere a inbox. O diferencial é o paradigma conversacional — em vez de navegar menus, o utilizador diz o que quer e o Vox executa.

### MVP (V1) — escopo fechado (self-use)
O MVP entrega o "loop mínimo de valor" via conversa com Vox: **falar, ouvir, confirmar, enviar**, para **1 conta Google**.

**Dentro do MVP:**
- Chat-first UI — Vox é a tela principal, inbox é tab secundária
- Login com 1 conta Google (OAuth 2.0, escopos Gmail read/send)
- PWA instalável no iOS/Android, dark-first
- Vox lê emails em voz alta (TTS ElevenLabs PT-PT feminina)
- Vox transcreve resposta por voz (Groq Whisper v3)
- Vox gera draft profissional (Groq Llama 3.3 70B)
- Revisão e edição do draft no chat (texto ou voz)
- Envio via Gmail API com confirmação
- MicButton: tap-to-toggle + auto-silêncio 2s
- Onboarding: splash + 2 ecrãs + Google login → Vox guia no chat

**Fora do MVP — vai para V2:**
- Multi-conta Google simultânea (seletor, threading cross-account)
- Google Calendar (criar/editar eventos por voz)
- Google Contacts (resolver destinatários por voz)
- Push notifications (FCM/APNs)
- Modo offline avançado (fila de envios, sync bidirecional)
- Resumos de thread por IA e classificação automática
- Wake-word ("Ei Vox")
- Integração com agendas externas (Outlook, iCloud)

### Hipótese de valor a validar
"Um profissional ocupado responde **3x mais rápido** 10 emails por voz do que digitando no celular, com qualidade equivalente de resposta."

---

## 2. Epics

| # | Épico | Objetivo | Valor entregue | Status |
|---|---|---|---|---|
| **E1** | Autenticação & Google OAuth | Login seguro, token refresh, escopos mínimos | Utilizador entra em 10s | ✅ Done |
| **E2** | Microserviço Python Gmail | Proxy Gmail API (list/get/send), cache | Base técnica segura | ✅ Done |
| **E3** | Inbox PWA | UI mobile para listar, abrir, navegar emails | Leitura confortável | ✅ Done (inbox-first) |
| **E4** | Voice Agent (STT+LLM+TTS) | Pipeline vocal completo | Experiência "conversar com o email" | ✅ Done |
| **E5** | Composer Vocal & Envio | Ditar resposta, revisar, enviar | Core loop do produto | ✅ Done |
| **E9** | Chat-First Redesign | Redesenhar frontend para Vox chat-first | Paradigma conversacional | ⬜ Next |
| **E6** | Multi-conta (V1.x) | 2+ contas Google ativas com seletor | Diferencial poweruser | ⬜ |
| **E10** | Polish & Self-Use Production | QA, performance, onboarding polido | Produto usável diariamente | ⬜ |

---

## 3. User Stories por épico

### E1 — Autenticação & Google OAuth (13 pts) ✅
- **E1.US1 (3)** Como usuário, quero fazer login com Google para não criar mais uma conta. ✅
- **E1.US2 (5)** Como usuário, quero que meu login persista entre sessões para não logar de novo toda hora. ✅
- **E1.US3 (3)** Como usuário, quero revogar acesso facilmente para ter controle dos meus dados. ✅
- **E1.US4 (2)** Como dev, quero refresh automático de tokens para evitar erros 401 em produção. ✅

### E2 — Microserviço Python Gmail (21 pts) ✅
- **E2.US1 (5)** Como frontend, quero um endpoint `/emails/list` paginado. ✅
- **E2.US2 (3)** Como frontend, quero `/emails/{id}` com corpo parseado. ✅
- **E2.US3 (8)** Como frontend, quero `/emails/send` autenticado. ✅
- **E2.US4 (3)** Como ops, quero rate-limiting e circuit breaker. ✅
- **E2.US5 (2)** Como dev, quero logs estruturados em Supabase. ✅

### E3 — Inbox PWA (18 pts) ✅
- **E3.US1–US5** ✅ (inbox-first, será redesenhado para tab secundária)

### E4 — Voice Agent (26 pts) ✅
- **E4.US1–US5** ✅ (será integrado no chat Vox)

### E5 — Composer Vocal & Envio (16 pts) ✅
- **E5.US1–US5** ✅ (será integrado nos Vox cards)

### E9 — Chat-First Redesign (30 pts) ⬜ NEXT
- **E9.US1 (5)** Como utilizador, quero uma bottom navbar com 4 tabs (Chat, Inbox, Agenda, Settings) para navegar rapidamente.
- **E9.US2 (8)** Como utilizador, quero ver o chat do Vox como tela principal com cards de acção (email lido, transcrição, draft, confirmação).
- **E9.US3 (5)** Como utilizador, quero tocar no MicButton para falar com o Vox, com auto-silêncio após 2s.
- **E9.US4 (3)** Como utilizador, quero ver a minha transcrição a aparecer em tempo real enquanto falo.
- **E9.US5 (3)** Como utilizador, quero ver o draft gerado pelo Vox como card editável, com botões Editar/Enviar.
- **E9.US6 (2)** Como utilizador, quero confirmar envio com toque único no card de draft.
- **E9.US7 (2)** Como utilizador, quero ver confirmação "Enviado" como card de sucesso no chat.
- **E9.US8 (2)** Como utilizador, quero ver a inbox como tab secundária com lista de emails e swipe actions.

### E6 — Multi-conta (16 pts, V1.x) ⬜
- **E6.US1 (5)** Como usuário, quero adicionar uma segunda conta Google.
- **E6.US2 (3)** Como usuário, quero um seletor de conta no chat header.
- **E6.US3 (5)** Como usuário, quero inbox unificada opcional.
- **E6.US4 (3)** Como usuário, quero escolher de qual conta envio a resposta.

### E10 — Polish & Self-Use Production (20 pts) ⬜
- **E10.US1 (5)** Como utilizador, quero onboarding polido (splash + 2 ecrãs + Google login → Vox guia).
- **E10.US2 (3)** Como utilizador, quero que o Vox fale PT-PT natural e conciso.
- **E10.US3 (5)** Como utilizador, quero p95 latência voz < 4s (STT+LLM+TTS).
- **E10.US4 (3)** Como utilizador, quero indicador de status online/offline.
- **E10.US5 (2)** Como utilizador, quero fila de envio offline (outbox).
- **E10.US6 (2)** Como dev, quero crash-free sessions ≥ 99%.

**Total V1 novo (E9+E10): 50 pts | V1.x (E6): 16 pts | Done (E1-E5): 94 pts**

---

## 4. Roadmap em Sprints (v2.0)

### Sprint 0 — Setup & Discovery ✅ DONE
- Repo criado, CI configurado, Supabase criado, OAuth consent screen submetido, scaffold frontend/backend.

### Sprint 1 — Auth Google + Inbox read-only ✅ DONE
- E1 + E2 + E3 implementados. Login funciona, inbox lista.

### Sprint 2 — Voice Agent MVP ✅ DONE
- E4 implementado. TTS + STT + pipeline vocal.

### Sprint 3 — Composer Vocal + Envio ✅ DONE
- E5 implementado. Loop completo ouvir→responder→enviar.

### Sprint 4 — Chat-First Redesign (Semanas 1-2, início 2026-04-21) ⬜ NEXT
- **Goal:** "Vox é a tela principal. O utilizador fala e vê cards de acção."
- **Stories:** E9.US1, E9.US2, E9.US3, E9.US4, E9.US5, E9.US6, E9.US7, E9.US8
- **Pontos:** 30
- **Entregas:**
  - Bottom navbar 4 tabs (Chat · Inbox · Agenda · Settings)
  - Chat layout com Vox cards (6 tipos: email-read, transcription, draft, confirmation, error, agenda-placeholder)
  - MicButton com 5 estados (idle, listening, silence-detected, processing, error) + auto-silêncio 2s
  - Transcrição em tempo real (JetBrains Mono, confirmed/hypothesis)
  - Inbox redesenhada como tab secundária
  - Dark-first paleta violet `#6C5CE7` + cyan `#00CEFF` + glass surfaces
  - Onboarding básico (Google login → Vox guia permissões)
- **DoD:** chat é a tab home, Vox responde com cards, MicButton funciona com auto-silêncio, inbox acessível via tab, paleta dark aplicada.
- **Riscos:** refactor significativo do layout existente (mitigação: preservar componentes de email-item, reutilizar lógica de voice).
- **Demo:** JP abre app → vê chat → toca mic → diz "lê os meus emails" → Vox mostra card de email → JP diz "responde" → Vox mostra card de draft → JP confirma envio.

### Sprint 5 — Multi-conta + Seletor (Semanas 3-4) ⬜
- **Goal:** "Alterno entre contas no chat do Vox."
- **Stories:** E6.US1, E6.US2, E6.US4, + dívida técnica do Sprint 4
- **Pontos:** 18
- **DoD:** 2 contas simultâneas, seletor no chat header, Vox sugere conta por default.
- **Riscos:** refactor da camada de auth para N contas.

### Sprint 6 — Polish, Onboarding, Self-Use Production (Semanas 5-6) ⬜
- **Goal:** "JP usa o Per4Biz diariamente sem fricção."
- **Stories:** E10.US1, E10.US2, E10.US3, E10.US4, E10.US5, E10.US6, + dívida técnica
- **Pontos:** 20
- **DoD:** p95 latência voz < 4s, crash-free ≥ 99%, onboarding polido, fila offline básica, Vox PT-PT natural.
- **Riscos:** latência pode não baixar de 4s (mitigação: streaming STT + LLM).
- **Demo:** **V1 done** — JP usa o Per4Biz como ferramenta diária.

**Total planejado (novos sprints): 68 pts em 3 sprints de 2 semanas = velocity ~23 pts/sprint.**

**Timeline:** Sprint 4 (sem 1-2) → Sprint 5 (sem 3-4) → Sprint 6 (sem 5-6) → **V1 self-use production = 6 semanas a partir de agora.**

---

## 5. Backlog priorizado (MoSCoW) — v2.0

### Must have (V1) — inegociável
- Chat-first UI com Vox cards
- Bottom navbar 4 tabs
- MicButton com auto-silêncio
- Dark-first paleta violet+cyan
- Login Google (1 conta)
- Vox lê email (TTS)
- Vox transcreve resposta (STT)
- Vox gera draft (LLM)
- Revisão + envio com confirmação
- Inbox como tab secundária

### Should have (V1.x, Sprint 5-6)
- Multi-conta com seletor no chat
- Onboarding polido (splash + ecrãs)
- Fila de envio offline
- Badge de não lidos
- Indicador online/offline

### Could have (V2, pós-self-use)
- Inbox unificada multi-conta
- Calendar create event por voz
- Push notifications
- Resolver contatos por voz
- Classificação IA de emails
- Resumos de thread
- Wake-word "Ei Vox"
- Integração Outlook

### Won't have (agora)
- Versão desktop nativa
- CRM/follow-up automático
- Assistente de reunião (transcrição de calls)
- Tradução automática
- Integração com Slack/Teams
- Modo colaborativo multi-usuário
- Tema claro

---

## 6. Cerimônias Ágeis

| Cerimônia | Frequência | Duração | Participantes | Formato |
|---|---|---|---|---|
| **Daily stand-up** | Diária (seg-sex, 9h) | 5-10 min | JP + agents | JP lê ontem/hoje/bloqueios |
| **Sprint Planning** | 1ª seg do sprint | 1-2h | Todos | Review backlog, selecionar stories, definir goal |
| **Sprint Review / Demo** | Última sex do sprint | 1h | JP | Demo ao vivo, capturar feedback |
| **Retrospectiva** | Última sex do sprint | 45 min | Time técnico | Start/Stop/Continue, 1 ação concreta |

---

## 7. Métricas de sucesso

### Métricas de Produto (self-use V1)
- **Emails respondidos por voz / dia:** meta ≥ 5 por sessão
- **Tempo médio resposta por voz vs manual:** meta **-60%** (ex: 90s vs 225s)
- **Sessões diárias:** meta ≥ 1 (JP usa diariamente)

### Métricas Técnicas
- **p95 latência STT+LLM+TTS end-to-end:** < 4s
- **Uptime microserviço Python:** ≥ 99.5%
- **Crash-free sessions PWA:** ≥ 99%
- **Custo médio por utilizador/mês:** < €3 em APIs

---

## 8. Riscos e Mitigações (v2.0)

| # | Risco | Impacto | Probab. | Mitigação |
|---|---|---|---|---|
| R1 | **Refactor chat-first quebra funcionalidade existente** | Alto | Média | Preservar componentes E1-E5, testes E2E antes de redesenhar |
| R2 | **Custo de APIs de voz explode** | Alto | Média | Cota dura por utilizador, monitorar Sprint 4 |
| R3 | **Latência voz > 4s** | Alto | Média | Streaming STT + LLM, benchmark Groq |
| R4 | **LLM gera resposta inadequada** | Alto | Baixa | Sempre mostrar draft no card, nunca enviar sem confirmação |
| R5 | **Auto-silêncio corta utilizadores com pausas** | Médio | Média | Configurável em Settings (1s-5s), desactivável |
| R6 | **Scope creep** | Médio | Alta | MoSCoW rigoroso, V1 = self-use |

---

## 9. Checklist Sprint 4 — Chat-First Redesign (Semana 1-2)

**Dia 1 (Segunda)**
1. Criar branch `feat/per4biz-chat-first`
2. Implementar bottom navbar componente (Chat · Inbox · Agenda · Settings)
3. Aplicar paleta dark-first (tokens CSS: `#0A0A0F`, `#6C5CE7`, `#00CEFF`, glass surfaces)
4. Configurar routing: `/` → Chat, `/inbox` → Inbox, `/agenda` → placeholder, `/settings` → settings

**Dia 2 (Terça)**
5. Criar layout do chat (header "Vox" + account chip + scroll area + MicButton + navbar)
6. Implementar VoxCard base component (glass frost, radius 16px, tipo dinâmico)
7. Implementar UserInput component (texto simples alinhado direita)
8. Criar store Zustand para chat messages

**Dia 3 (Quarta)**
9. Implementar MicButton com estados (idle, listening, silence-detected, processing, error)
10. Implementar auto-silêncio (Web Audio API: detectar 2s de silêncio)
11. Implementar transcrição em tempo real (JetBrains Mono, confirmed/hypothesis)
12. Ligar MicButton ao backend voice endpoints existentes

**Dia 4 (Quinta)**
13. Implementar VoxCard tipo "email-read" (snippet + CTA Ouvir/Responder)
14. Implementar VoxCard tipo "draft" (body editável + CTAs Editar/Enviar)
15. Implementar VoxCard tipo "confirmation" (checkmark + "Enviado")
16. Implementar VoxCard tipo "error" (mensagem + Tentar de novo)

**Dia 5 (Sexta)**
17. Migrar inbox existente para tab secundária (preservar componentes)
18. Implementar Agenda placeholder (empty state)
19. Testes E2E: fluxo chat → mic → transcrição → draft → envio
20. Sprint 4 Review: demo ao vivo do chat-first

---

## 10. Distribuição de trabalho por role e sprint (v2.0)

| Role | S4 | S5 | S6 | **Total** |
|---|---|---|---|---|
| **Tech Lead (JP)** — arquitetura, code review, Vox prompts | 6 | 5 | 4 | **15** |
| **Frontend PWA dev** (agent) — chat UI, MicButton, cards, dark theme | 16 | 8 | 8 | **32** |
| **Backend Python dev** (agent) — multi-conta auth, Vox intent router | 4 | 5 | 4 | **13** |
| **UI/UX** (agent) — polish, onboarding, animations | 2 | 0 | 4 | **6** |
| **QA** (agent) — E2E, regression, performance | 2 | 0 | 0 | **2** |
| **Total do sprint** | **30** | **18** | **20** | **68** |

---

## Conclusão

O Per4Biz pivota de inbox-first para **chat-first** com o agente Vox. E1-E5 (94 pts) estão implementados e funcionais. O redesign em 3 sprints (6 semanas) transforma o frontend num paradigma conversacional dark-first. Meta: JP usa o Per4Biz diariamente como ferramenta de produtividade vocal.

**Próximo passo imediato:** executar checklist Dia 1 do Sprint 4 — bottom navbar + paleta dark + routing.
