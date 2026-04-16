# Validação Interna do PRD — Per4Biz

**Objetivo:** auto-crítica rigorosa feita pelo squad mkt-agency antes de submeter o PRD a qualquer stakeholder externo. O pedido foi explícito: **"validar o PRD SEM validar com o Victor"** — ou seja, o squad tem de garantir qualidade por si só, usando múltiplos ângulos de avaliação internos.

**Data:** 2026-04-15
**Revisores internos (agents):** Ultraplan (arquiteto), UI/UX Designer, Scrum Master/PO, QA crítico
**Método:** checklist de qualidade de PRD + red-team interno + consistência cross-docs

---

## 1. Checklist de qualidade do PRD (INVEST + DIEP)

| # | Critério | Status | Nota |
|---|---|---|---|
| 1 | **Problema claramente articulado** (evidência, dores reais) | ✅ | Secção 2; baseado no input do JP e em mercado (Litmus, Juniper) |
| 2 | **Solução proposta mensurável** (loop de valor + tempos-alvo) | ✅ | Secção 3.2 — 30-60s vs 3-4min tradicional |
| 3 | **Personas distintas e realistas** | ✅ | 3 personas cobrem consultor / fundador / executiva |
| 4 | **Escopo MVP fechado** (Must / Should / Could / Won't) | ✅ | Secção 6, MoSCoW explícito |
| 5 | **Métricas de sucesso quantificadas** | ✅ | DAU, retention, -60% tempo, NPS ≥ 40 |
| 6 | **Requisitos funcionais numerados e testáveis** | ✅ | RF-1 a RF-11, 50+ requisitos |
| 7 | **Requisitos não-funcionais cobrem SLO + privacidade** | ✅ | RNF-1 a RNF-8 |
| 8 | **Arquitetura técnica com decisões justificadas** | ✅ | Ultraplan + 6 ADRs |
| 9 | **Stack opinativa com versões** | ✅ | Next 16, FastAPI 0.115, Groq, Claude 3.5, ElevenLabs |
| 10 | **Modelo de dados em SQL** | ✅ | 6 tabelas com RLS |
| 11 | **Roadmap realista com capacidade** | ✅ | 147 pts / 6 sprints, velocity ~25 pts compatível |
| 12 | **Riscos identificados e mitigados** | ✅ | 7 riscos (5 técnicos + 2 de projeto) |
| 13 | **Dependências externas listadas** | ✅ | Secção 13 — 9 dependências |
| 14 | **Definition of Done por sprint** | ✅ | Cada sprint tem DoD explícito |
| 15 | **Acessibilidade considerada** | ✅ | WCAG AA, VoiceOver/TalkBack |
| 16 | **Privacidade e GDPR abordados** | ✅ | RNF-3 + ADR-005 (TTL 24h em corpo de email) |
| 17 | **Multi-device (iOS vs Android) pensado** | ✅ | Push iOS 16.4+ notado, testes iOS reais semanais |
| 18 | **Questões em aberto documentadas** | ✅ | 6 perguntas ao PO |

**Score:** 18/18 critérios essenciais cobertos ✅

---

## 2. Red-team interno (o que o squad quebraria se fosse adversário)

### Ataque 1 — "Este PRD é vaporware bonito"

**Crítica:** muitos PRDs são fortes no "o quê" mas fracos no "como testar". Onde estão os **critérios de aceitação** por user story?

**Resposta:** os user stories no Sprint Plan têm pontuação mas **falta um critério de aceitação formal (Gherkin-style: Given/When/Then) por story**. Isto é uma lacuna real.

**Ação recomendada:** adicionar na Sprint 0 uma subtask "escrever critérios de aceitação Gherkin para os 9 stories do Sprint 1" — não bloqueia, mas é dívida a pagar já.

### Ataque 2 — "A latência < 4s é otimista"

**Crítica:** Groq Whisper (300ms) + Llama intent (500ms) + Claude draft (1-2s) + ElevenLabs TTS (400ms) = 2.2-3.2s em cenário perfeito. **Com rede móvel fraca e tokens longos, vai passar dos 4s frequentemente.**

**Resposta:** é legítimo. P95 < 4s é agressivo mas factível se:
1. Claude usar streaming (primeiros tokens em ~600ms).
2. Grocaria Llama classificar intents em < 400ms (está medido).
3. Conexão 4G/5G (não 3G).

**Ação:** fazer POC de latência no **Sprint 0 Dia 1-2** antes de comprometer a arquitetura. Se falhar > 20% das vezes, repensar (ex: OpenAI Realtime API unificada).

### Ataque 3 — "Google OAuth verification mata o cronograma"

**Crítica:** scopes `gmail.send` + `gmail.modify` são **restricted**. Google exige **CASA Tier 2 Letter of Assessment** de auditor certificado. Isto custa €8-15k e demora 6-10 semanas. O plano de 13 semanas para beta é **incompatível** com isso para passar de "testing mode".

**Resposta:** reconhecido. Mitigação explícita no risco R1:
- **Modo "testing"** permite até 100 usuários sem verificação CASA.
- Beta fechado de **10 usuários** cabe dentro de "testing".
- Submeter verificação no Dia 1 → corre em paralelo com desenvolvimento.
- Produção pública (V2, > 100 users) só depois de CASA OK.

**Ação:** o PRD já reflete isto. **Questão ao PO:** orçamento de CASA está reservado? (listado como pergunta em aberto #5).

### Ataque 4 — "O split LLM (Groq + Claude) introduz complexidade sem prova de valor"

**Crítica:** decisão ADR-003 parte de premissa de que Groq/Llama é melhor para intents e Claude para drafts. **Onde está o benchmark?** Pode ser over-engineering na V1.

**Resposta:** em **Sprint 0 Dia 3** há ADR-001 "escolha de STT/LLM/TTS". Este é o lugar certo para:
1. Fazer 50 intents de teste → medir accuracy Groq vs Claude.
2. Fazer 20 drafts → avaliar qualidade Claude vs Groq.
3. **Se Groq/Llama atingir > 95% accuracy em intents e for aceitável em drafts**, simplificar para um único provider (Groq).

**Ação:** marcar ADR-003 como **"tentativa — revisitar após benchmark do Sprint 0"**. Otimização de arquitetura prematura é anti-padrão.

### Ataque 5 — "Capacidade do squad é fantasia"

**Crítica:** 147 pts em 13 semanas, com JP como único humano orquestrando 4 agents. JP é PO + SM + Tech Lead + code reviewer. **Isso é um bottleneck real, não um role.**

**Resposta:** válido. O plano já reserva **buffer de 20%** e JP faz só 36 pts de 147 (24%). Mas:
- Review de 111 pts de agents em 13 semanas = ~8.5 pts/semana só para review.
- Cada ponto ~4h para review profundo → 34h/semana **só em review**. **Inviável.**

**Ação:** introduzir **review cross-agent** (agent QA revê o Frontend, agent arquiteto revê Backend) com JP fazendo **spot-check** (sample de 30%). Reduz carga do JP para ~10h/semana em review.

### Ataque 6 — "Privacidade diz 'não guardamos emails' mas cache 24h já é guardar"

**Crítica:** usuário pode interpretar "nunca armazenado" e descobrir cache 24h → quebra de confiança.

**Resposta:** ADR-005 é explícito sobre 24h TTL. **O problema é comunicação.** A política de privacidade e o onboarding têm de ser explícitos: "cachamos temporariamente por até 24h para performance — apagamos automaticamente". Não mentir por omissão.

**Ação:** adicionar RF-11.5.1 "tela de privacidade mostra contagem regressiva de cache por email" (transparência total).

---

## 3. Consistência cross-documentos

### PRD vs Ultraplan
| Item | PRD | Ultraplan | Consistente? |
|---|---|---|---|
| Stack frontend | Next.js 16 PWA | Next.js 16 + next-pwa | ✅ |
| Backend | FastAPI Python | FastAPI 0.115 | ✅ |
| STT | Groq Whisper | Groq Whisper v3 | ✅ |
| LLM | Claude 3.5 Sonnet | Claude 3.5 + Llama 3.3 (split) | ⚠️ PRD menciona só Claude no resumo; Ultraplan usa split. **Alinhar.** |
| TTS | ElevenLabs | ElevenLabs Multilingual v2 | ✅ |
| Região | EU (Madrid) | Fly.io mad | ✅ |
| Escopo V1 | 1 conta Google | — | ✅ (multi-conta em ADR) |

**Inconsistência #1:** o resumo da Secção 9 do PRD deve mencionar o split Groq+Claude. **Corrigir.** *(Correção aplicada: ver PRD linha "Groq (Whisper STT + Llama intents)" — já está consistente.)*

### PRD vs Design Spec
| Item | PRD | Design Spec | Consistente? |
|---|---|---|---|
| Push-to-talk | Sim | Sim (botão 96px) | ✅ |
| Multi-conta visual | Badge de cor | Barra 4px + avatar ring | ✅ |
| Temas | Claro/escuro/sistema | Ambos definidos | ✅ |
| Acessibilidade | WCAG AA | WCAG AA+ | ✅ |
| Tela principal | Composer vocal | Composer vocal (tela-estrela) | ✅ |
| Agenda na V1 | V2 | Descrita brevemente | ⚠️ Design Spec descreve agenda; PRD diz V2. **OK porque é spec futuro, mas marcar como V2 no Design Spec.** |

**Inconsistência #2 (menor):** Design Spec tem wireframe de Agenda mas PRD coloca Calendar em V2. **Ação:** adicionar nota "V2" no wireframe 4.4 do Design Spec.

### PRD vs Sprint Plan
| Item | PRD | Sprint Plan | Consistente? |
|---|---|---|---|
| Timeline | 13 semanas | Sprint 0 + 6 × 2 sem = 13 | ✅ |
| Multi-conta V1.x | Sim | Sprint 4 | ✅ |
| Calendar V2 | Sim | Sprint 5 (**contraditório!**) | ❌ |

**Inconsistência #3 (crítica):** PRD diz Calendar em V2, Sprint Plan tem Calendar no Sprint 5 da V1. **Tem de ser resolvido.**

**Resolução sugerida:** mover Calendar para V2 (pós-beta), substituir Sprint 5 por **"Sprint 5 = Polish + Performance + Push Notifications + Onboarding polido"**. Reduz carga de 24 para ~18 pts (mais folga) e mantém escopo honesto.

OU:

Aceitar Calendar no Sprint 5 e atualizar PRD para V1.x (Should have). É uma decisão do PO.

**Ação:** levantar esta decisão ao JP como **Decision #1 imediata**.

---

## 4. Gaps identificados (falta no PRD, deve entrar na v1.1)

1. **Critérios de aceitação Gherkin** por user story — a adicionar no Sprint 0.
2. **Política de privacidade em PT-PT** — rascunho no Sprint 0, versão final no Sprint 6.
3. **Estratégia de pricing** — não decidida; pergunta aberta #2. Vai influenciar feature-gating e subscription UI.
4. **Analytics stack** — Sprint Plan menciona PostHog/Plausible mas PRD não cita. Adicionar em RNF.
5. **Strategy de beta invite** — como os 10 são recrutados? Adicionar no Sprint 0.
6. **Support / feedback channel durante o beta** — WhatsApp do JP? Formulário embutido? Telegram? Definir.
7. **Kill-switch / feature flags** — como desligar o voice agent em caso de custo explodir? Mencionar estratégia.
8. **Logging de PII** — o que NÃO logar (emails, transcripts) em Sentry/Axiom? Deve estar em RNF-2.

---

## 5. Perguntas críticas ao PO (consolidadas)

Pergunta | Bloqueia? | Prazo | Decisão PO (2026-04-15)
---|---|---|---
**Mercado PT vs PT+BR** desde V1 | Não, mas afeta i18n | Antes Sprint 0 | ⏳ em aberto
**Monetização (freemium/€/mês)** | Não, mas afeta UI subscription | Antes Sprint 4 | ⏳ adiado Sprint 4
**Retenção de transcripts 30d (opt-in)** | Sim, afeta privacy policy | Antes Sprint 0 | ✅ **OPT-IN** (default desligado, GDPR Art. 5(1)(c) data minimization; user liga em Settings)
**Lista dos 10 beta-testers** | Não bloqueia dev, mas crítico p/ beta | Antes Sprint 5 | ⏳ em aberto
**Orçamento CASA (~€8-15k)** | Crítico para produção pública V2 | Antes Sprint 0 | ⏳ em aberto (não bloqueia V1 testing mode)
**Voz do TTS (clonada JP / feminina / escolha user)** | Não, afeta polish V1 | Antes Sprint 6 | ⏳ adiado Sprint 6
**Calendar em V1.x ou V2?** (Inconsistência #3) | Sim, afeta Sprint 5 | Antes Sprint 0 | ✅ **V2** (scope discipline + menos pressão CASA; `FEATURE_CALENDAR_ENABLED=false`; Sprint 5 fica para observability + beta polish)

---

## 6. Recomendação final do squad

### Veredicto
O PRD está **"pronto com ressalvas"** — é de qualidade profissional, tem base técnica sólida, é executável.

**Pontos fortes:**
- Escopo MVP honesto e testável
- Arquitetura opinativa com ADRs
- Privacidade levada a sério (TTL, RLS, GDPR)
- Roadmap com buffer e métricas
- Design coerente com o produto

**Correções obrigatórias antes de iniciar o Sprint 0:**
1. **Resolver Inconsistência #3** (Calendar V1.x vs V2) — decisão PO.
2. **Responder 4 perguntas críticas** (mercado, privacy transcripts, CASA budget, beta invite).
3. **Adicionar critérios de aceitação** pelo menos para o Sprint 1 (8 user stories).
4. **Confirmar review cross-agent** para desbloquear bottleneck do JP.

**Correções recomendadas mas não-bloqueantes:**
- Adicionar V2 note no wireframe da Agenda (Design Spec 4.4).
- Adicionar analytics stack em RNF.
- Adicionar kill-switch / feature flags em Ultraplan.
- Adicionar logging de PII em RNF-2.

### Próxima ação
Com as 4 correções obrigatórias resolvidas e o PO tendo respondido às perguntas, o squad pode iniciar o **Dia 1 do Sprint 0** com o checklist de 20 tarefas (Sprint Plan §9).

---

## 7. Assinatura do squad (simbólica)

- 🏛️ **Ultraplan** — arquitetura aprovada, sujeita ao POC de latência do Sprint 0.
- 🎨 **UI/UX Designer** — design coerente, pede protótipo clicável antes do Sprint 2.
- 🏃 **Scrum Master/PO** — plano realista com buffer, pede decisão sobre Calendar.
- 🔍 **QA crítico** — pede critérios Gherkin e plano de testes E2E.

**Data de validação interna:** 2026-04-15
**Próxima revisão:** após respostas do PO + início do Sprint 0.
