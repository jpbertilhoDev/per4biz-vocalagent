# PRD — Per4Biz

**Product Requirements Document**
**Produto:** Per4Biz — Copiloto Pessoal Vocal de Email e Agenda
**Cliente / PO:** JP Bertilho (mkt-agency)
**Data:** 2026-04-15
**Versão:** 1.0 (baseline)
**Status:** Aguarda validação interna do squad

---

## 0. Como ler este documento

Este PRD é o documento **mestre**. Ele referencia 3 documentos complementares:

| Documento | Localização | O que contém |
|---|---|---|
| **Ultraplan técnico** | `../02-ultraplan/ULTRAPLAN-tecnico.md` | Arquitetura, stack, data model, ADRs |
| **Design Spec (UI/UX)** | `../03-ui-ux/DESIGN-SPEC.md` | Sistema visual, telas, componentes, PWA |
| **Sprint Plan (Agile)** | `../04-sprints/SPRINT-PLAN.md` | Épicos, user stories, roadmap 13 semanas |
| **Validação interna** | `../05-validacao/VALIDACAO-INTERNA.md` | Auto-crítica, gaps, perguntas em aberto |

---

## 1. Executive Summary

Per4Biz é um **PWA mobile** (instalável no iOS/Android) que funciona como um **secretário pessoal vocal** para profissionais que gerem **múltiplas contas Google**. O utilizador fala, o sistema ouve, consulta Gmail/Calendar/Contacts, gera respostas, confirma e envia — tudo sem tocar num teclado.

**Posicionamento:** "Superhuman encontra Siri para profissionais com 2+ emails." Diferente de Superhuman (rápido no teclado) e Siri (assistente genérico), Per4Biz é focado em **email vocal profissional multi-conta** com qualidade PT-PT.

**Public-alvo:** profissionais 20-40 anos em Portugal/Brasil, freelancers, consultores, empresários que operam pelo menos 2 caixas de correio Google (pessoal + trabalho) e passam >1h/dia a responder emails no móvel.

---

## 2. Problema

### 2.1 Dores do utilizador (validadas informalmente pelo JP)

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

## 4. Personas & User Personas

### Persona 1 — "Carla, 32 anos, consultora independente"
- 3 contas Google (pessoal, consultoria, cliente X).
- Recebe ~80 emails/dia, responde no móvel entre reuniões.
- Dor: enviar pela conta errada, responder no metro com teclado minúsculo.
- Win: responder 10 emails em 5 min a caminho do próximo meeting.

### Persona 2 — "Miguel, 28 anos, fundador de agência (como o JP)"
- 2 contas Google (pessoal + agência) + 1 Workspace.
- Vive no WhatsApp e email; pouco tempo para triagem.
- Dor: gerir caixas diferentes, tom profissional inconsistente.
- Win: ter um "chief of staff" vocal que sabe o tom de cada conta.

### Persona 3 — "Rita, 40 anos, executiva sénior"
- 1 Workspace corporativo + 1 pessoal.
- Inglês + PT-PT no dia-a-dia.
- Dor: calendário caótico, responde email enquanto conduz (legalmente problemático).
- Win: modo hands-free real, comando vocal no carro.

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

## 6. Escopo — o que entra na V1 e o que fica para V2

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

- **Multi-conta Google** (2+ contas simultâneas, seletor rápido, inbox unificada opcional)
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
- RF-1.1 Login com conta Google via OAuth 2.0 (scopes: `gmail.readonly`, `gmail.send`, `gmail.modify`, `calendar`, `contacts.readonly`).
- RF-1.2 Persistência de sessão via Supabase Auth (JWT refreshable).
- RF-1.3 Refresh automático de access tokens em background.
- RF-1.4 Revogar acesso em 1 clique nas Configurações.

### RF-2 — Gestão de contas Google (multi-conta, V1.x)
- RF-2.1 Adicionar N contas Google (V1: 1 conta; V1.x: 2+ contas).
- RF-2.2 Editar nickname e cor de cada conta.
- RF-2.3 Remover conta (revoga token + apaga cache local).
- RF-2.4 Seletor de conta ativa com swipe down no header.
- RF-2.5 Inbox unificada (toggle) — mostra emails de todas as contas.

### RF-3 — Inbox
- RF-3.1 Listar últimos 50 emails ordenados por data decrescente.
- RF-3.2 Mostrar remetente, assunto, snippet, badge de conta.
- RF-3.3 Pull-to-refresh para sincronizar.
- RF-3.4 Badge de não lidos no header.
- RF-3.5 Swipe actions: arquivar, marcar lido, responder por voz, eliminar.

### RF-4 — Detalhe do email
- RF-4.1 Exibir corpo do email parseado (HTML → texto legível).
- RF-4.2 CTA primário: "Responder por voz".
- RF-4.3 CTAs secundários: Encaminhar, Arquivar, Eliminar.
- RF-4.4 Indicar claramente em que conta o email foi recebido.

### RF-5 — Voice Agent (STT)
- RF-5.1 Push-to-talk: toque inicia gravação, toque finaliza.
- RF-5.2 Feedback visual em 4 estados: idle / listening / processing / draft-ready.
- RF-5.3 Waveform animado reativo ao volume do input.
- RF-5.4 Transcrição em tempo real durante a fala (palavras confirmadas vs hipótese).

### RF-6 — LLM Draft
- RF-6.1 Gerar draft a partir do ditado (Claude 3.5 Sonnet em PT-PT).
- RF-6.2 Preservar contexto da thread de origem (se reply).
- RF-6.3 Aplicar tom profissional cordial por default.
- RF-6.4 Permitir comandos vocais de edição: "muda o tom", "remove X", "adiciona Y".
- RF-6.5 Permitir edição textual inline do draft.

### RF-7 — Envio
- RF-7.1 Confirmação obrigatória antes de enviar ("Enviar" / "Refazer").
- RF-7.2 Envio via Gmail API com `from` da conta selecionada.
- RF-7.3 Feedback "Enviado" com checkmark + haptic.
- RF-7.4 Fila local (`outbox`) se offline; envio ao reconectar.

### RF-8 — TTS (Leitura de email)
- RF-8.1 Tocar email em voz alta via ElevenLabs.
- RF-8.2 Controles: play/pause, próximo email.
- RF-8.3 Velocidade configurável (0.8x / 1x / 1.25x / 1.5x).

### RF-9 — Calendar (V2)
- RF-9.1 Criar evento por voz ("marca reunião amanhã 15h com João").
- RF-9.2 Ver agenda do dia na home.
- RF-9.3 Confirmação visual antes de criar evento.

### RF-10 — Contacts (V2)
- RF-10.1 Resolver destinatários por voz ("responder ao João" → encontra nos contatos).
- RF-10.2 Autocomplete de contatos no composer textual.

### RF-11 — Configurações
- RF-11.1 Aparência (tema claro/escuro/sistema).
- RF-11.2 Voz (idioma PT-PT, velocidade TTS, voz ElevenLabs).
- RF-11.3 Notificações (ativar/desativar push).
- RF-11.4 Contas Google (lista + gestão).
- RF-11.5 Privacidade (exportar dados, apagar conta).

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
- Endpoints `/me/export` e `DELETE /me` (direito ao esquecimento).
- Dados em região EU (Supabase Frankfurt ou Paris).

### RNF-4 — Fiabilidade
- Uptime ≥ 99.5%.
- Crash-free sessions ≥ 99%.
- Retry exponencial em chamadas externas.
- Circuit breaker em Gmail API.

### RNF-5 — Escalabilidade
- Arquitetura suporta 1000 utilizadores no beta+ sem refactor.
- Auto-scale Fly.io 1-3 máquinas.
- Supabase Pro plan quando > 500 MAU.

### RNF-6 — Acessibilidade
- WCAG 2.1 AA mínimo.
- Suporte a VoiceOver (iOS) e TalkBack (Android).
- Touch targets ≥ 48×48px.
- `prefers-reduced-motion` respeitado.

### RNF-7 — Idioma
- PT-PT como default (usuário alvo em Portugal).
- Preparar i18n para PT-BR e EN (V2).

### RNF-8 — Custo operacional
- < €3/utilizador/mês em APIs externas (Groq + Claude + ElevenLabs).
- Cap de 200 interações vocais/dia/utilizador.

---

## 9. Arquitetura (resumo; detalhes em `../02-ultraplan/ULTRAPLAN-tecnico.md`)

```
[PWA Next.js 16] ↔ [BFF Route Handlers] ↔ [FastAPI Python em Fly.io Madrid]
                                              ├→ Google APIs (Gmail, Calendar, People)
                                              ├→ Groq (Whisper STT + Llama intents)
                                              ├→ Claude 3.5 Sonnet (drafts PT-PT)
                                              ├→ ElevenLabs (TTS PT-PT streaming)
                                              └→ Supabase (Postgres + Auth + Storage + Realtime)
                                                     ↑
                                                Upstash Redis (cache + rate limit + queue)
```

---

## 10. UI/UX (resumo; detalhes em `../03-ui-ux/DESIGN-SPEC.md`)

- **Design principles:** voice-first, glance-able, one-thumb, multi-conta sem fricção, silent confidence.
- **Sistema visual:** paleta iOS-inspired (azul elétrico #0A84FF primário, rosa #FF375F voice ativa), Inter variable, radius 12-16, sistema 4px.
- **Tela-estrela:** Composer Vocal full-screen com waveform, transcrição live e CTA único de 96px.
- **Multi-conta:** barra colorida lateral de 4px em cada email + avatar ring colorido + chip "De: X" no composer.

---

## 11. Sprint & Roadmap (resumo; detalhes em `../04-sprints/SPRINT-PLAN.md`)

| Sprint | Semanas | Goal | Pts |
|---|---|---|---|
| S0 | 1 | Setup & discovery | — |
| S1 | 2-3 | Auth Google + Inbox read-only | 28 |
| S2 | 4-5 | Voice Agent MVP (STT + TTS) | 26 |
| S3 | 6-7 | Composer Vocal + Envio (**alpha**) | 27 |
| S4 | 8-9 | Multi-conta + Seletor | 22 |
| S5 | 10-11 | Calendar + Push | 24 |
| S6 | 12-13 | Polish + Beta Launch (**V1 GA**) | 20 |

**Total:** 147 pts em 13 semanas · 10 beta-testers no final.

---

## 12. Riscos Top 5 (resumo consolidado)

| # | Risco | Mitigação |
|---|---|---|
| R1 | Verificação Google OAuth demora 4-6 semanas | Submeter no Dia 1, modo "testing" com 100 users no beta |
| R2 | Latência voz > 4s inviabiliza UX | Groq+ElevenLabs streaming, POC no S0, P95 em Sentry |
| R3 | Custos LLM/TTS explodem | Cap 200 interações/dia, Claude só em drafts, alerta a €5/user |
| R4 | iOS PWA limitado (mic, push) | Push-to-talk explícito, detectar standalone, testar iOS real semanal |
| R5 | Vazamento de refresh tokens | AES-GCM + Fly secrets + rotação trimestral + 2FA obrigatório |

---

## 13. Dependências & Integrações externas

| Dependência | Propósito | Risco |
|---|---|---|
| Google Cloud Console (OAuth + APIs) | Autorização e acesso a Gmail/Calendar/Contacts | Verificação CASA para scopes sensíveis |
| Supabase | Auth + DB + Storage + Realtime | Lock-in aceitável (padrão da casa) |
| Vercel | Deploy frontend | Lock-in médio (padrão da casa) |
| Fly.io | Deploy microserviço Python (região Madrid) | Médio — alternativa: Railway/Render |
| Groq | STT Whisper v3 + Llama intent | Alto — único fornecedor viável de baixa latência |
| Anthropic | Claude para drafts | Médio — fallback GPT-4o-mini |
| ElevenLabs | TTS PT-PT | Médio — fallback Web Speech API |
| Upstash Redis | Cache + rate limit | Baixo — substituível |
| Sentry + Axiom | Observabilidade | Baixo |

---

## 14. Equipa & Responsabilidades

| Role | Pessoa | Responsabilidade |
|---|---|---|
| PO / Scrum Master / Tech Lead | JP Bertilho | Visão, arquitetura, code review, decisões |
| Frontend PWA dev | Agent (Claude Code) | Next.js 16, PWA, UI voice |
| Backend Python dev | Agent | FastAPI, Google APIs, voice pipeline |
| UI/UX designer | Agent | Figma, design system, protótipos |
| QA | Agent | Playwright E2E, test plans, bug triage |

Capacidade: ~25 pts/sprint.

---

## 15. Aceitação & Definition of Done do PRD

Este PRD é considerado **"pronto para execução"** quando:

- [x] Escopo V1 aprovado pelo PO (JP)
- [x] Ultraplan técnico revisto e aprovado internamente
- [x] Design Spec validado contra os RFs
- [x] Sprint Plan tem capacidade compatível (147 pts / 13 semanas)
- [ ] Validação interna completa (ver `../05-validacao/VALIDACAO-INTERNA.md`)
- [ ] Checklist do Dia 1 do Sprint 0 pronto para executar

---

## 16. Perguntas em aberto para o PO (JP)

1. **Mercado-alvo primário:** Portugal only ou PT+BR desde a V1? (Impacta i18n e modelo LLM).
2. **Monetização:** freemium, €X/mês, ou ainda indefinido? (Influencia feature gating).
3. **Privacidade:** aceitamos transcripts retidos 30 dias para melhoria ou apenas on-device?
4. **Beta-testers:** JP já tem os 10 identificados ou parte do Sprint 0 é recrutamento?
5. **Budget CASA/OAuth verification:** orçamento disponível? (Pode chegar a €15k com auditoria terceirizada).
6. **Voz do TTS:** voz clonada do JP, voz feminina genérica ou escolha do utilizador?

**Estas perguntas devem ser respondidas antes do Sprint 0 começar.**

---

## 17. Changelog

| Versão | Data | Autor | Alterações |
|---|---|---|---|
| 1.0 | 2026-04-15 | JP + Squad agents | Baseline inicial (PRD + Ultraplan + UI/UX + Sprint) |

---

**Fim do documento mestre.** Para detalhes técnicos, visuais ou de planeamento, consulte os documentos referenciados na Secção 0.
