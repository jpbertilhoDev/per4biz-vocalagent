# SPEC — E1: Autenticação & Google OAuth

**Épico:** E1 (Sprint 1, 13 story points)
**Feature ID:** `e1-auth-google-oauth`
**Autor:** JP + Squad (brainstorming)
**Data:** 2026-04-15
**Status:** ✅ aprovado pelo PO (2026-04-15) com amendments A-E aplicados
**Aprovação:** ✅ §1 · ✅ §2 · ✅ §3 · ✅ §4 · ✅ §5 · ✅ §6 · ✅ §7 · ✅ §8

> **Como usar este SPEC:** o PO aprova secção por secção (marca ✅ em cada checkbox). Só depois de todas aprovadas o Superpowers avança para `writing-plans` → `plans/e1-auth-google-oauth/PLAN.md`.

---

## 1. Problema que esta feature resolve

O utilizador abre o Per4Biz pela primeira vez. Neste momento ele precisa de:

1. **Identificar-se** na aplicação de forma segura (sem criar mais uma password).
2. **Autorizar** o Per4Biz a ler/enviar emails **em seu nome** na sua caixa Google.
3. **Confiar** que pode revogar esse acesso a qualquer momento sem ajuda técnica.
4. **Manter-se logado** entre sessões (sem ter de fazer login cada vez que abre o PWA).

Sem esta feature, nada funciona — é o gateway para todo o resto do produto.

**Decisão de simplificação V1:** na V1, há apenas 1 conta Google por utilizador. Essa conta serve **simultaneamente** como identidade (login na app) e como conta operacional (caixa Gmail a ser lida/enviada). Na V1.x entram contas operacionais adicionais separadas da identidade.

---

## 2. User Stories afetadas

Do [SPRINT-PLAN.md §3](../../04-sprints/SPRINT-PLAN.md):

| ID | Story | Pts |
|---|---|---|
| **E1.US1** | Como utilizador, quero fazer login com Google para não criar mais uma conta | 3 |
| **E1.US2** | Como utilizador, quero que o meu login persista entre sessões | 5 |
| **E1.US3** | Como utilizador, quero revogar acesso facilmente para ter controlo dos meus dados | 3 |
| **E1.US4** | Como dev, quero refresh automático de tokens para evitar 401 em produção | 2 |

**Total:** 13 pts

---

## 3. Requisitos Funcionais (subset do PRD §7)

### RF-1.1 — Login com Google (OAuth 2.0)
Scopes solicitados no consentimento inicial (V1 — **4 scope groups**):
```
openid email profile
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.modify
```
**Notas:**
- `gmail.modify` é **restricted scope** — exige CASA Tier 2 para sair de testing mode (R1 do SPRINT-PLAN §8).
- Scopes `calendar` e `contacts.readonly` **não** são pedidos em V1. Calendar entra só em V2 (decisão PO 2026-04-15 — ver VALIDACAO-INTERNA §5). Se Contacts regressar, entra via incremental authorization.

### RF-1.2 — Sessão persistente (V1 — FastAPI-managed, sem Supabase Auth)
- FastAPI emite **session JWT HS256** assinado com `INTERNAL_API_SHARED_SECRET`, colocado em cookie `__Host-session` (HttpOnly, Secure, SameSite=Lax, **7 dias**).
- PWA envia o cookie automaticamente em cada request ao backend.
- Em reabertura da app, FastAPI valida o JWT; se válido, a sessão é restaurada sem ação do utilizador.
- V2 roadmap: migrar para Supabase Auth quando entrar multi-tenant (coluna `user_id` já preparada em todas as tabelas).

### RF-1.3 — Refresh automático
- **Access token Google** expira em 1h → FastAPI faz refresh transparente antes de cada chamada Gmail. O novo `access_token` é cifrado (AES-256-GCM) e gravado em `google_accounts.access_token_encrypted`.
- **Session JWT FastAPI** expira em 7 dias → renovação silenciosa em cada request autenticado dentro desse período (rolling window).
- Em caso de `invalid_grant` (utilizador revogou no Google Account ou refresh token expirou aos 6 meses), backend apaga `google_accounts`, invalida a session (cookie expira), e força re-login com toast **"Acesso revogado — por favor entra novamente"**.

### RF-1.4 — Revogar acesso
- Ecrã **Definições → Conta Google** mostra botão "Desvincular e apagar conta".
- Ao confirmar (dialog com texto explícito):
  1. Chama `https://oauth2.googleapis.com/revoke` com o refresh token.
  2. Apaga linha `google_accounts` (cascade limpa `email_cache`, `draft_responses`, `voice_sessions`).
  3. Apaga `auth.users` via `supabase.auth.admin.deleteUser()`.
  4. Redireciona para ecrã de login com toast "Conta apagada".

---

## 4. Comportamento esperado

### 4.1 Happy path (primeiro login)

```
[1] Utilizador abre https://per4biz.app
[2] Vê ecrã de boas-vindas + botão único "Entrar com Google"
[3] Clica → redirect para Google OAuth consent screen
[4] Google mostra:
    - Identidade da app (Per4Biz, logo, domínio verificado)
    - **4 scope groups** (identidade + gmail.readonly + gmail.send + gmail.modify) com descrição clara
    - Link para `06-addendum/PRIVACY-POLICY-PT.md` (renderizada em /privacy)
[5] Utilizador aceita → Google redireciona para /auth/google/callback?code=...
[6] Backend (FastAPI):
    - Valida state JWT (HS256, expiry 10min, nonce)
    - **Email gating:** se `id_token.email != ALLOWED_USER_EMAIL` → 403 (V1 single-tenant)
    - Troca `code` por `access_token` + `refresh_token` + `id_token`
    - Cria/atualiza linha `public.users` com UUID fixo do .env `USER_ID`
    - Cifra `refresh_token` + `access_token` com AES-256-GCM (`ENCRYPTION_KEY`)
    - Insere em `google_accounts` com `is_primary=true`
    - Insere linha `consent_log` (`policy_type=privacy`, `policy_version=privacy-v1.0`, `consent_given=true`)
    - Emite session JWT HS256 e define cookie `__Host-session` (HttpOnly, Secure, SameSite=Lax, 7 dias)
[7] Redirect para /inbox
[8] PWA mostra mensagem de onboarding "Vamos buscar os seus emails..."
```

### 4.2 Edge cases

| Cenário | Comportamento esperado |
|---|---|
| Utilizador cancela no Google consent | Redirect para `/` com toast "Login cancelado" |
| Google devolve erro OAuth (`access_denied`, `invalid_request`) | Log (sem PII) + ecrã de erro amigável com "Tentar novamente" |
| `ENCRYPTION_KEY` ausente em runtime | FastAPI falha o boot (fail-fast, não silent) |
| Utilizador já tem conta (reentrou) | Atualiza tokens, não duplica `auth.users` |
| Utilizador revogou manualmente no [myaccount.google.com](https://myaccount.google.com/permissions) | Próxima chamada Gmail dá 401 → FastAPI detecta, limpa `google_accounts`, força re-login, toast "Acesso revogado no Google — por favor entre novamente" |
| Refresh token expira após 6 meses de inatividade (Google Policy) | Mesmo comportamento do ponto anterior |
| Utilizador tenta aceder a `/inbox` sem sessão | Redirect 307 para `/` (protegido via middleware) |
| Ligação de rede cai durante callback | Retry exponencial no backend (2 tentativas, 1s e 2s); se falhar, erro claro |
| Relógio do servidor dessincronizado (JWT `iat`/`exp` inválido) | Log de alerta, rejeita sessão — mas isto é infra, não feature |

---

## 5. Segurança & Privacidade

### 5.1 Armazenamento de tokens
- `refresh_token` **sempre** cifrado AES-256-GCM antes de `INSERT`.
- Formato: `nonce (12 bytes) || ciphertext || tag`.
- Coluna `key_version INT` permite rotação trimestral sem downtime.
- `access_token` também cifrado (menos crítico mas coerência).
- **Nunca** logar tokens, nem em stacktraces Sentry.

### 5.2 Scopes
- Pedir **apenas o mínimo necessário para V1**.
- `gmail.send` + `gmail.modify` são scopes restricted → exigem **CASA Tier 2 Letter of Assessment** para sair de modo "testing" (R1 do [SPRINT-PLAN.md §8](../../04-sprints/SPRINT-PLAN.md)).
- Submeter verificação no **Dia 1 do Sprint 0** (já no checklist).

### 5.3 CSRF / state parameter
- Parâmetro `state` no OAuth URL é um **JWT HS256** assinado com `INTERNAL_API_SHARED_SECRET`, contendo:
  - `nonce` (crypto-random, 16 bytes)
  - `exp` (10 minutos)
  - `redirect_to` (URL de retorno no PWA)
- Callback valida JWT antes de trocar `code` por tokens.

### 5.4 Cookies
- Sessão Supabase em cookie `__Host-` com:
  - `HttpOnly`, `Secure`, `SameSite=Lax`
  - `Path=/`, sem `Domain` (scoped a per4biz.app)

### 5.5 Privacidade (GDPR)
- Consent screen inicial tem checkbox obrigatório:
  > "Li e aceito a [Política de Privacidade](/privacy) e os [Termos de Serviço](/terms). Autorizo o Per4Biz a ler e enviar emails em meu nome, com retenção mínima dos conteúdos (até 24h em cache)."
- Log de consentimento: tabela `consent_log` (user_id, version_id, timestamp, ip_hash).
- Endpoint `DELETE /me` cobre RF-1.4 + `GET /me/export` (JSON dump) — ambos criados neste épico.

---

## 6. UX (referência [03-ui-ux/DESIGN-SPEC.md](../../03-ui-ux/DESIGN-SPEC.md))

### 6.1 Ecrãs envolvidos (sitemap §3 do Design Spec)

- **Welcome** — logo centrado + tagline + CTA "Entrar com Google"
- **Google OAuth consent** — hospedado pela Google (não customizamos)
- **Loading pós-callback** — spinner + texto "A preparar a sua caixa..."
- **Inbox** — destino final (já existe stub no Sprint 1)
- **Definições → Conta Google** — card com email, avatar, botão "Desvincular e apagar conta"

### 6.2 Componentes usados (design system §10)

| Componente | Variante |
|---|---|
| Button | `primary · lg(56px)` — "Entrar com Google" com logo G |
| Card | `default` — card de conta nas definições |
| ListRow | `destructive` — "Desvincular e apagar conta" |
| Toast | `error / success / info` — feedback de cancelamento, sucesso, revogação |
| Modal | `dialog` — confirmação dupla antes de apagar conta |

### 6.3 Estados visuais

- **Welcome idle** — CTA primário azul `#0A84FF`, cor de conta ainda não atribuída
- **Loading callback** — fullscreen, splash brand, sem dismiss
- **Erro OAuth** — ecrã com ícone neutro, texto claro, CTA "Tentar novamente" + link "Reportar problema"
- **Desvinculação** — modal com título "Apagar conta?" + corpo explicativo + 2 botões ("Cancelar" ghost / "Sim, apagar" destructive)

### 6.4 Tom PT-PT

- "Entrar com Google" (não "Login" ou "Fazer login")
- "Desvincular e apagar conta" (não "Delete account")
- Mensagens de erro empáticas: "Algo correu mal ao entrar. Tenta novamente dentro de momentos."

---

## 7. Critérios de aceitação (Gherkin)

### AC-1 — Primeiro login bem-sucedido
```gherkin
Given que não tenho sessão ativa no Per4Biz
And que tenho uma conta Google válida
When clico em "Entrar com Google" na tela Welcome
And autorizo todos os 5 scopes pedidos
Then sou redirecionado para /inbox
And existe uma linha nova em auth.users com o meu email
And existe uma linha em google_accounts com is_primary=true
And o meu refresh_token está cifrado em AES-256-GCM na BD
And vejo o toast "Bem-vindo ao Per4Biz, {nome}"
```

### AC-2 — Login cancelado
```gherkin
Given que estou no Google OAuth consent screen
When clico em "Cancelar"
Then sou redirecionado para /
And vejo o toast "Login cancelado — tens de aceitar para usar o Per4Biz"
And não existe nenhuma linha nova em auth.users
```

### AC-3 — Sessão persiste após reabrir app
```gherkin
Given que fiz login com sucesso há 2 dias
And fechei completamente o browser
When volto a abrir https://per4biz.app
Then sou redirecionado diretamente para /inbox sem tela de login
And a minha sessão é automaticamente refrescada se expirou
```

### AC-4 — Refresh automático de access token
```gherkin
Given que o meu access_token Google expirou (> 1 hora)
And ainda tenho refresh_token válido
When o backend precisa de chamar a Gmail API
Then obtém novo access_token via refresh_token transparentemente
And a chamada Gmail sucede
And o novo access_token é guardado cifrado na BD
```

### AC-5 — Revogação manual pelo utilizador
```gherkin
Given que tenho sessão ativa com conta Google vinculada
When vou a /settings/account
And clico em "Desvincular e apagar conta"
And confirmo no modal digitando "APAGAR"
Then o token é revogado em https://oauth2.googleapis.com/revoke
And todas as minhas linhas em google_accounts, email_cache, draft_responses, voice_sessions são apagadas
And a minha linha em auth.users é apagada
And sou redirecionado para / com toast "Conta apagada com sucesso"
```

### AC-6 — Revogação externa (via myaccount.google.com)
```gherkin
Given que revoguei o acesso do Per4Biz em myaccount.google.com
When a app tenta usar o meu refresh_token
Then a Gmail API responde 401 invalid_grant
And o backend apaga a minha linha google_accounts
And a próxima request no PWA redireciona para / com toast "Acesso revogado — por favor entra novamente"
```

### AC-7 — Segurança: CSRF no callback
```gherkin
Given que um atacante construiu uma URL /auth/google/callback com code válido mas state inválido
When o backend recebe esse callback
Then responde 400 com mensagem "Invalid state"
And nenhuma sessão é criada
And é registado um warning em Axiom (sem PII)
```

### AC-8 — Segurança: tokens nunca em logs
```gherkin
Given que o fluxo OAuth correu e ocorreu qualquer exception
When inspeciono os logs em Sentry e Axiom
Then não encontro nenhum access_token, refresh_token ou id_token em texto claro
And o logger tem um filtro que redacta qualquer chave matching /token$|_key$|secret/i
```

---

## 8. Não-objetivos (explícito, para evitar scope creep)

Esta feature **NÃO** cobre:

- ❌ **Multi-conta Google** — 1 só conta na V1. Multi-conta é o Épico E6 (Sprint 4).
- ❌ **Login com email/password** — Google OAuth exclusivamente.
- ❌ **Magic link / passwordless por email** — sem valor numa app Google-centric.
- ❌ **Social login (Apple, Facebook, GitHub)** — fora do público-alvo profissional.
- ❌ **SSO empresarial (SAML, Google Workspace)** — V2 se houver procura.
- ❌ **2FA / MFA** — a Supabase Auth oferece, mas Google já obriga 2FA na identidade → redundante na V1.
- ❌ **Recuperação de conta** — herdamos da Google (se perdes a Google, perdes o Per4Biz).
- ❌ **Onboarding tour** — será feature separada no Sprint 6.
- ❌ **Permissões granulares por scope** — ou aceita todos ou não entra.
- ❌ **Calendar scope** — adicionado via incremental authorization no Épico E7 (V2).

---

## 9. Dependências técnicas (pré-requisitos de ambiente)

Antes de arrancar tasks desta feature, tem de existir:

- [ ] Projeto no **Google Cloud Console** com OAuth 2.0 Client ID criado (checklist Sprint 0 Dia 1)
- [ ] OAuth consent screen submetido em modo "testing" (Dia 1)
- [ ] Projeto **Supabase** EU region com Auth provider configurado (Dia 2)
- [ ] Variáveis `.env`: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `ENCRYPTION_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `INTERNAL_API_SHARED_SECRET`
- [ ] Migration `0001_initial_schema.sql` aplicada com tabelas `users`, `google_accounts`, `consent_log` + RLS
- [ ] Scaffold FastAPI com middleware de sessão e logging redacted
- [ ] Scaffold Next.js 16 com `@supabase/ssr` configurado

---

## 10. Estimativa & riscos locais

| Item | Estimativa | Risco |
|---|---|---|
| Backend OAuth flow (`/auth/google/start`, `/auth/google/callback`) | 3 pts | Médio — validação CSRF state + AES-GCM |
| Frontend Welcome + loading screens | 2 pts | Baixo |
| Sessão persistente (`@supabase/ssr` middleware) | 3 pts | Médio — cookies em iOS Safari standalone mode são frágeis |
| Refresh automático de access_token Google | 2 pts | Baixo |
| Ecrã de revogação + endpoint DELETE /me | 3 pts | Baixo |

**Total:** 13 pts (coerente com SPRINT-PLAN §3)

**Risco local top 1:** iOS Safari em modo standalone (PWA instalado) por vezes perde cookies quando a app é "limpa" pelo sistema. Mitigação: teste físico no Dia 4 do Sprint 1; fallback em `localStorage` com refresh token encriptado como último recurso (com ADR explicando).

---

## 11. Decisões do PO (2026-04-15)

1. **Logo do provider** → ✅ Logo **"G" oficial** da Google (brand guidelines + confiança)
2. **Política de privacidade PT-PT** → ✅ Baseline em `06-addendum/PRIVACY-POLICY-PT.md` v1.0. Revisão legal antes de V2 público.
3. **Domínio final** → ✅ `per4biz.vercel.app` (default Vercel) em V1. Domínio custom adiado para V1.x se necessário.
4. **Consent transcripts 30d** → ✅ **OPT-IN** (default desligado). Ver VALIDACAO-INTERNA §5.
5. **Endpoint `/me/export`** → ✅ **Incluído** neste épico E1 (completa trilogia GDPR: revoke + export + delete).

## 12. Amendments aplicados em revisão (2026-04-15)

- **A:** Removido scope `contacts.readonly` (é V2/E7, não V1). 4 scope groups no consent screen.
- **B:** §4.1 step 4 "5 scopes" → "4 scopes" (coerente com A).
- **C:** RF-1.2/1.3 + §4.1 step 6 — substituído "Supabase Auth JWT" por "session JWT HS256 assinado com `INTERNAL_API_SHARED_SECRET` em cookie `__Host-session`" (V1 não usa Supabase Auth — ver `07-v1-scope/EXECUTION-NOTES.md`).
- **D:** Nova migration `supabase/migrations/0004_consent_log.sql` — tabela `consent_log` referida em §5.5.
- **E:** `GET /me/export` incluído no escopo do épico E1 (JSON dump dos dados do utilizador).

---

**Fim do SPEC.**

Quando aprovares as 8 secções acima (§1 a §8) e responderes às perguntas §11, o Superpowers avança automaticamente para `writing-plans` → cria `../../plans/e1-auth-google-oauth/PLAN.md` com tasks bite-sized de 2-5 min e TDD explícito.
