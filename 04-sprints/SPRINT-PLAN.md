# Per4Biz — Plano Ágil Completo (V1)

**Produto:** Per4Biz — PWA mobile, copiloto vocal de email e agenda com multi-conta Google
**Squad:** mkt-agency
**Product Owner / Scrum Master:** JP Bertilho
**Data de kickoff:** Semana 1 (2026-04-20)
**Data-alvo V1 (beta):** Semana 13 (2026-07-20)
**Versão do documento:** 1.0

---

## 1. Visão do MVP e escopo

### Visão do Produto
Per4Biz é um copiloto vocal mobile-first que transforma o celular num assistente executivo: o usuário ouve seus emails, responde falando, marca reuniões e gerencia contatos sem tocar no teclado. O diferencial é a latência baixa do ciclo voz-LLM-voz e a experiência multi-conta para profissionais que operam com 2+ emails Google (pessoal + trabalho + cliente).

### MVP (V1) — escopo fechado
O MVP entrega o "loop mínimo de valor": **entrar, ouvir, responder por voz, enviar**, para **1 conta Google**.

**Dentro do MVP:**
- Login com 1 conta Google (OAuth 2.0, escopos Gmail read/send)
- PWA instalável no iOS/Android, funcionamento offline básico (shell)
- Listagem dos últimos 50 emails (inbox read-only) com pull-to-refresh
- Leitura em voz alta (TTS) do email aberto
- Gravação de resposta por voz (STT), geração de draft via LLM
- Edição rápida do draft (texto) + envio
- Microserviço Python como proxy seguro para Gmail API
- Supabase para sessão, cache de emails e logs de uso
- Deploy em Vercel (frontend) + Railway (backend Python)

**Fora do MVP — vai para V2:**
- Multi-conta Google simultânea (seletor, threading cross-account)
- Google Calendar (criar/editar eventos por voz)
- Google Contacts (resolver destinatários por voz)
- Push notifications (FCM/APNs)
- Modo offline avançado (fila de envios, sync bidirecional)
- Resumos de thread por IA e classificação automática
- Wake-word ("Ei Per4")
- Integração com agendas externas (Outlook, iCloud)

### Hipótese de valor a validar no beta
"Um profissional ocupado responde **3x mais rápido** 10 emails por voz do que digitando no celular, com qualidade equivalente de resposta."

---

## 2. Epics

| # | Épico | Objetivo | Valor entregue |
|---|---|---|---|
| **E1** | Autenticação & Google OAuth | Login seguro, token refresh, escopos mínimos | Usuário entra em 10s e confia na app |
| **E2** | Microserviço Python Gmail | Proxy Gmail API (list/get/send), rate-limit, cache | Base técnica segura para todas as operações de email |
| **E3** | Inbox PWA | UI mobile para listar, abrir, navegar emails | Leitura confortável no mobile |
| **E4** | Voice Agent (STT+LLM+TTS) | Pipeline vocal completo com latência < 4s p95 | Experiência "conversar com o email" |
| **E5** | Composer Vocal & Envio | Ditar resposta, revisar, enviar | Core loop do produto |
| **E6** | Multi-conta (V2) | 2+ contas Google ativas com seletor | Diferencial competitivo para poweruser |
| **E7** | Calendar & Contacts (V2) | Criar eventos e resolver contatos por voz | Copiloto completo, não só email |
| **E8** | Notifications & Offline (V2) | Push + fila offline | Retenção e confiabilidade |

---

## 3. User Stories por épico

### E1 — Autenticação & Google OAuth (13 pts)
- **E1.US1 (3)** Como usuário, quero fazer login com Google para não criar mais uma conta.
- **E1.US2 (5)** Como usuário, quero que meu login persista entre sessões para não logar de novo toda hora.
- **E1.US3 (3)** Como usuário, quero revogar acesso facilmente para ter controle dos meus dados.
- **E1.US4 (2)** Como dev, quero refresh automático de tokens para evitar erros 401 em produção.

### E2 — Microserviço Python Gmail (21 pts)
- **E2.US1 (5)** Como frontend, quero um endpoint `/emails/list` paginado para popular o inbox.
- **E2.US2 (3)** Como frontend, quero `/emails/{id}` com corpo parseado (HTML→texto) para leitura vocal.
- **E2.US3 (8)** Como frontend, quero `/emails/send` autenticado para enviar respostas.
- **E2.US4 (3)** Como ops, quero rate-limiting e circuit breaker para não estourar quota do Gmail.
- **E2.US5 (2)** Como dev, quero logs estruturados em Supabase para debugar em produção.

### E3 — Inbox PWA (18 pts)
- **E3.US1 (5)** Como usuário, quero ver os 50 emails mais recentes com remetente, assunto e snippet.
- **E3.US2 (3)** Como usuário, quero pull-to-refresh para atualizar inbox.
- **E3.US3 (5)** Como usuário, quero abrir um email em tela cheia legível no mobile.
- **E3.US4 (3)** Como usuário, quero instalar a app na home screen (PWA manifest).
- **E3.US5 (2)** Como usuário, quero ver badge de não lidos.

### E4 — Voice Agent (26 pts)
- **E4.US1 (5)** Como usuário, quero ouvir o email em voz alta tocando em um botão "Play".
- **E4.US2 (8)** Como usuário, quero gravar minha resposta falando, com indicador visual de escuta.
- **E4.US3 (5)** Como usuário, quero ver o texto transcrito aparecendo em tempo real.
- **E4.US4 (5)** Como usuário, quero que o LLM polisse meu ditado em um email educado.
- **E4.US5 (3)** Como dev, quero métricas de latência por etapa (STT/LLM/TTS) para otimizar.

### E5 — Composer Vocal & Envio (16 pts)
- **E5.US1 (3)** Como usuário, quero revisar o draft antes de enviar.
- **E5.US2 (3)** Como usuário, quero editar o draft por texto se precisar ajustar.
- **E5.US3 (5)** Como usuário, quero re-ditar ("regravar") sem perder o original.
- **E5.US4 (3)** Como usuário, quero confirmar envio com toque único.
- **E5.US5 (2)** Como usuário, quero ver confirmação "Enviado" com feedback sonoro.

### E6 — Multi-conta (16 pts, V2)
- **E6.US1 (5)** Como usuário, quero adicionar uma segunda conta Google.
- **E6.US2 (3)** Como usuário, quero um seletor de conta no topo da inbox.
- **E6.US3 (5)** Como usuário, quero inbox unificada opcional.
- **E6.US4 (3)** Como usuário, quero escolher de qual conta envio a resposta.

### E7 — Calendar & Contacts (21 pts, V2)
- **E7.US1 (8)** Como usuário, quero criar evento falando ("reunião amanhã às 15h com João").
- **E7.US2 (5)** Como usuário, quero ver minha agenda do dia na home.
- **E7.US3 (5)** Como usuário, quero ditar "responder ao João" e o app resolver o contato.
- **E7.US4 (3)** Como usuário, quero confirmação visual antes de criar evento.

### E8 — Notifications & Offline (13 pts, V2)
- **E8.US1 (5)** Como usuário, quero push notification de emails importantes.
- **E8.US2 (5)** Como usuário, quero que respostas ditadas offline entrem numa fila e enviem ao reconectar.
- **E8.US3 (3)** Como usuário, quero indicador de status online/offline.

**Total V1 (E1-E5): 94 pts | V2 (E6-E8): 50 pts**

---

## 4. Roadmap em Sprints

### Sprint 0 — Setup & Discovery (Semana 1, 1 semana)
- **Goal:** "Ambiente pronto para codar no Sprint 1."
- **Stories:** (não-pontuadas, tarefas de setup)
- **Entregas:** repo GitHub com CI, Vercel+Railway deploys vazios ok, projeto Supabase criado, Google Cloud Console com OAuth consent screen, Figma com design tokens e 3 telas-chave, ADR sobre escolha STT/LLM/TTS.
- **DoD:** um "hello world" PWA faz deploy automático no push.
- **Riscos:** aprovação do OAuth consent screen pode demorar 2-5 dias (mitigação: fazer day 1).
- **Demo:** tour pelos dashboards Vercel/Railway/Supabase e Figma.

### Sprint 1 — Auth Google + Inbox read-only (Semanas 2-3)
- **Goal:** "Usuário loga e vê seus 50 últimos emails no celular."
- **Stories:** E1.US1, E1.US2, E1.US4, E2.US1, E2.US2, E2.US5, E3.US1, E3.US2, E3.US3
- **Pontos:** 28
- **DoD:** login funciona em iOS e Android, inbox lista com < 2s, cobertura testes > 60% backend.
- **Riscos:** parsing MIME do Gmail é chato (dep: biblioteca `google-api-python-client`).
- **Demo:** JP loga em dispositivo real e navega pelos emails.

### Sprint 2 — Voice Agent MVP (Semanas 4-5)
- **Goal:** "O app lê o email em voz alta e transcreve o que eu digo."
- **Stories:** E4.US1, E4.US2, E4.US3, E4.US5, E3.US4, E1.US3
- **Pontos:** 26
- **DoD:** latência STT < 2s para áudios < 15s, TTS audível e natural, ADR de fornecedor escolhido (Whisper/Deepgram vs OpenAI Realtime).
- **Riscos:** custo de API de voz pode explodir (mitigação: cota dura por usuário).
- **Demo:** JP abre email, ouve, grava um "obrigado" e vê texto.

### Sprint 3 — Composer Vocal + Envio (Semanas 6-7)
- **Goal:** "Respondo um email 100% por voz e o destinatário recebe."
- **Stories:** E4.US4, E5.US1, E5.US2, E5.US3, E5.US4, E5.US5, E2.US3, E2.US4
- **Pontos:** 27
- **DoD:** ciclo completo ouvir→responder→enviar em < 90s com sucesso > 95%, 10 emails reais enviados em teste interno.
- **Riscos:** LLM pode gerar respostas inadequadas (mitigação: sempre mostrar draft, nunca enviar direto).
- **Demo:** **Milestone V1-alpha** — JP responde 5 emails por voz ao vivo.

### Sprint 4 — Multi-conta + Seletor (Semanas 8-9)
- **Goal:** "Alterno entre conta pessoal e de trabalho sem sair do app."
- **Stories:** E6.US1, E6.US2, E6.US4, E3.US5, + dívida técnica do Sprint 3
- **Pontos:** 22
- **DoD:** 2 contas simultâneas, tokens isolados por conta, seletor < 500ms.
- **Riscos:** refactor da camada de auth para suportar N contas (mitigação: design preparado no Sprint 1).
- **Demo:** JP alterna 3x entre contas e envia de cada uma.

### Sprint 5 — Calendar Integration + Push (Semanas 10-11)
- **Goal:** "Crio eventos por voz e recebo notificação de email urgente."
- **Stories:** E7.US1, E7.US2, E7.US4, E8.US1, E8.US3
- **Pontos:** 24
- **DoD:** criar evento com 95% de acerto em frases naturais, push funcionando iOS+Android.
- **Riscos:** push em iOS PWA tem limitações (mitigação: fallback email/SMS).
- **Demo:** "Marca reunião com Maria quarta 14h" → aparece no Google Calendar.

### Sprint 6 — Polish, Performance, Beta Launch (Semanas 12-13)
- **Goal:** "10 beta-testers usando diariamente."
- **Stories:** dívida técnica, otimização, onboarding, E6.US3, bugs de QA.
- **Pontos:** 20
- **DoD:** p95 latência voz < 4s, crash-free > 99%, onboarding em 3 telas, landing page pública, 10 convites enviados.
- **Riscos:** feedback do beta pode exigir replanejamento.
- **Demo:** **V1 GA beta** — 10 usuários reais logados.

**Total planejado V1: 147 pts em 6 sprints + sprint 0 = velocity média ~24-27 pts/sprint (dentro da capacidade).**

---

## 5. Backlog priorizado (MoSCoW)

### Must have (V1) — inegociável
- Login Google, refresh token, revogação
- Inbox list/read (50 emails)
- TTS leitura de email
- STT ditado de resposta
- LLM draft polido
- Envio Gmail
- PWA instalável
- Logs e métricas de latência

### Should have (V1.x, Sprints 4-6)
- Multi-conta com seletor
- Calendar create event por voz
- Push notifications
- Onboarding com 3 telas
- Badge não lidos

### Could have (V2, pós-beta)
- Inbox unificada multi-conta
- Resolver contatos por voz
- Classificação IA de emails
- Resumos de thread
- Modo offline avançado (fila)
- Wake-word
- Integração Outlook

### Won't have (agora)
- Versão desktop nativa
- CRM/follow-up automático
- Assistente de reunião (transcrição de calls)
- Tradução automática
- Integração com Slack/Teams
- Modo colaborativo multi-usuário

---

## 6. Cerimônias Ágeis

| Cerimônia | Frequência | Duração | Participantes | Formato |
|---|---|---|---|---|
| **Daily stand-up** | Diária (seg-sex, 9h) | 5-10 min | JP + agents (via auto-check) | JP lê ontem/hoje/bloqueios, agents reportam status de tasks |
| **Sprint Planning** | 1ª seg do sprint | 1-2h | Todos | Review backlog, selecionar stories, estimar, definir sprint goal |
| **Sprint Review / Demo** | Última sex do sprint (manhã) | 1h | Todos + stakeholders fictícios | Demo ao vivo, capturar feedback |
| **Retrospectiva** | Última sex do sprint (tarde) | 45 min | Time técnico | Start/Stop/Continue, 1 ação concreta |
| **Backlog Refinement** | Meio do sprint (quarta) | 1h | JP + devs | Refinar próximas 5-8 stories, quebrar épicos |

---

## 7. Métricas de sucesso

### Métricas de Produto (beta V1)
- **DAU / WAU:** meta ≥ 60% dos beta-testers ativos/semana
- **Emails respondidos por voz / dia:** meta ≥ 5 por usuário ativo
- **Tempo médio resposta por voz vs manual:** meta **-60%** (ex: 90s vs 225s)
- **Retention D7:** meta ≥ 40%
- **NPS do beta:** meta ≥ 40

### Métricas Técnicas
- **p95 latência STT+LLM+TTS end-to-end:** < 4s
- **Uptime microserviço Python:** ≥ 99.5%
- **Crash-free sessions PWA:** ≥ 99%
- **Custo médio por usuário/mês:** < €3 em APIs
- **Taxa de erro de envio Gmail:** < 0.5%

### Métricas de Sprint
- **Velocity:** baseline 25 pts, meta banda 22-30
- **Burndown:** linha ideal vs real, alerta se desvio > 20% no meio do sprint
- **Escape defects:** bugs que escapam para produção, meta < 2 / sprint
- **Commitment accuracy:** % de stories completadas vs comprometidas, meta ≥ 85%

---

## 8. Top 7 Riscos e Mitigações

| # | Risco | Impacto | Probab. | Mitigação |
|---|---|---|---|---|
| R1 | **OAuth Gmail verification demora** (Google exige security assessment para escopos sensíveis) | Alto | Alta | Iniciar submissão no Sprint 0, usar app em modo "testing" com até 100 usuários no beta |
| R2 | **Custo de APIs de voz explode** | Alto | Média | Cota dura por usuário (ex: 30min/dia), monitorar Sprint 2, preparar plano B com Whisper self-hosted |
| R3 | **Latência voz > 4s** (inviabiliza UX) | Alto | Média | POC no Sprint 0, benchmark 3 fornecedores, streaming STT + LLM |
| R4 | **PWA push iOS limitado** | Médio | Alta | Fallback para email/SMS, comunicar limitação no onboarding |
| R5 | **LLM gera resposta inadequada** enviada por engano | Alto | Baixa | Sempre mostrar draft, guardrails de prompt, log de revisões humanas |
| R6 | **Capacidade do time** (JP absorvendo 1 Tech Lead + revisão de agents) | Médio | Alta | Buffer de 20% por sprint, não comprometer > 27 pts |
| R7 | **Scope creep do beta** (testers pedindo features V2) | Médio | Alta | Roadmap público, usar MoSCoW para dizer "não por agora" |

---

## 9. Checklist dos primeiros 5 dias (Semana 1 — Sprint 0)

**Dia 1 (Segunda)**
1. Criar repo `per4biz` no GitHub (monorepo: `/web` + `/api`)
2. Configurar branch protection + Conventional Commits
3. Criar projeto no Google Cloud Console
4. Submeter OAuth consent screen (Gmail readonly + send)

**Dia 2 (Terça)**
5. Scaffold Next.js 14 PWA em `/web` com manifest + service worker básico
6. Scaffold FastAPI em `/api` com estrutura de rotas
7. Deploy inicial Vercel (`/web`) e Railway (`/api`) — "hello world"
8. Criar projeto Supabase, schema inicial (users, sessions, email_cache)

**Dia 3 (Quarta)**
9. Configurar GitHub Actions: lint + test + deploy preview
10. Design system base no Figma: tokens (cores, tipografia, espaçamentos), 3 componentes (Button, Card, VoiceButton)
11. Wireframe de 3 telas: Login, Inbox, Email Detail
12. ADR-001: escolha de STT/LLM/TTS (benchmark rápido OpenAI Realtime vs Deepgram+Claude+ElevenLabs)

**Dia 4 (Quinta)**
13. Implementar login Google end-to-end (preparação técnica para Sprint 1)
14. Configurar Sentry no frontend e backend
15. Setup PostHog ou Plausible para analytics
16. Documento "Contrato de API" inicial (OpenAPI spec)

**Dia 5 (Sexta)**
17. Sprint 0 Review interno: tudo deployado e conversando
18. Sprint 1 Planning: selecionar 28 pts, atribuir a agents
19. Criar board no GitHub Projects (colunas: Backlog / To Do / In Progress / Review / Done)
20. Publicar roadmap no Notion/README para alinhamento

---

## 10. Distribuição de trabalho por role e sprint (story points)

| Role | S1 | S2 | S3 | S4 | S5 | S6 | **Total** |
|---|---|---|---|---|---|---|---|
| **Tech Lead / Fullstack (JP)** — arquitetura, code review, integrações críticas | 8 | 6 | 6 | 7 | 5 | 4 | **36** |
| **Frontend PWA dev** (agent) — UI, PWA, voice UX | 10 | 12 | 10 | 8 | 9 | 8 | **57** |
| **Backend Python dev** (agent) — microserviço Gmail/Calendar, Supabase | 8 | 3 | 8 | 5 | 7 | 3 | **34** |
| **UI/UX designer** (agent) — wireframes, protótipos, design system | 2 | 3 | 2 | 1 | 2 | 3 | **13** |
| **QA** (agent) — test plans, E2E Playwright, bug triage | 0 | 2 | 1 | 1 | 1 | 2 | **7** |
| **Total do sprint** | **28** | **26** | **27** | **22** | **24** | **20** | **147** |

**Notas de capacidade:**
- JP atua como Tech Lead + Scrum Master + PO — ~20h/semana de código, resto em orquestração, review e decisões de produto.
- Agents Frontend e Backend carregam o peso de implementação. Agent QA entra com força a partir do Sprint 2, quando há fluxo vocal para testar.
- UI/UX designer tem picos em Sprint 0-1 (design system) e Sprint 6 (polish).
- Capacidade total por sprint: 147 pts / 6 sprints = **24.5 pts/sprint médio**, compatível com a velocidade estimada (25-30 pts/sprint).

---

## Conclusão

Em **13 semanas** (Sprint 0 + 6 sprints de 2 semanas), o squad mkt-agency entrega uma V1 beta do Per4Biz com o loop vocal completo para 1 conta Google, mais multi-conta e calendar como should-haves. O plano respeita capacidade real (um humano + agents), reserva buffer para riscos técnicos de voz/OAuth, e define um beta fechado de 10 usuários como validação da hipótese de valor.

**Próximo passo imediato:** executar o checklist de 5 dias da Semana 1, começando pela submissão do OAuth consent screen (risco R1) ainda no Dia 1.
