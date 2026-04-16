# SPEC — E2+E3 Gmail Inbox (read-only)

**Feature ID:** `e2-e3-gmail-inbox`
**Autor:** JP + rapid-fire approval
**Data:** 2026-04-15
**Status:** ✅ aprovado pelo PO
**Aprovação:** ✅ §1 · ✅ §2 · ✅ §3 · ✅ §4 · ✅ §5 · ✅ §6 · ✅ §7

> Consolida E2.US1/US2 + E3.US1/US2/US3 do SPRINT-PLAN. Pós-login, exibe os 50 emails mais recentes e permite abrir um email individual no mobile. Sem send/compose (E4).

---

## 1. Problema

Após login E1 bem-sucedido, o user é redirecionado para `/inbox` mas a página retorna 404. Não há inbox renderizada. Precisamos de listar os 50 emails mais recentes do Gmail do user e permitir abrir cada um para leitura completa (prep para voice agent em E4).

## 2. User Stories

| ID | Pts | História |
|---|---|---|
| E2.US1 | 5 | Backend `GET /emails/list?limit=50` paginado |
| E2.US2 | 3 | Backend `GET /emails/{id}` com corpo parseado HTML→texto |
| E3.US1 | 5 | Frontend lista com sender/subject/snippet |
| E3.US2 | 3 | Pull-to-refresh |
| E3.US3 | 5 | Detail view fullscreen mobile |

**Total: 21 pts**

## 3. Requisitos Funcionais

### RF-2.1 — Gmail API client
- `google-api-python-client` + `google-auth` (já em pyproject)
- Flow por request: decrypt `refresh_token_encrypted` (crypto.decrypt) → `Credentials.from_authorized_user_info(...)` → se access_token expirou, refresh → call Gmail API
- Access token atualizado é re-cifrado e gravado em `google_accounts.access_token_encrypted` com novo `access_token_expires_at`

### RF-2.2 — Cache estratégia
- **Metadata (from, subject, snippet, received_at):** cached em `email_cache` table indefinidamente (apagado só em revoke cascade)
- **Body (`body_cached`):** cached apenas quando requisitado via `GET /emails/{id}`, TTL 24h (cron 0002 já limpa)
- Lista usa dados de `email_cache` + sync delta via Gmail history API no Sprint 2.x (em V1 Sprint 1 extension, simples refetch)

### RF-2.3 — Paginação
- Nativa Gmail: query param `?page_token=abc...` → backend passa a `pageToken` na Gmail API call
- Response: `{emails: [...], next_page_token: "..." | null}`

### RF-2.4 — Rate limiting
- Upstash Redis counter por `user_id`: max 10 calls a `/emails/list` por minuto
- Excede → 429 Too Many Requests
- V2 adicionar circuit breaker + retry com backoff exponencial

### RF-2.5 — Frontend TanStack Query
- Provider em `app/layout.tsx`
- Query `["emails", "list"]` com staleTime 60s
- Mutation `invalidateQueries` no pull-to-refresh
- Infinite scroll preparado mas desativado em V1 (só primeira página 50)

### RF-2.6 — Data shape

```typescript
// GET /emails/list response
{
  emails: [{
    id: string,               // gmail_message_id
    from_name: string | null, // "João Silva"
    from_email: string,       // "joao@example.com"
    subject: string,
    snippet: string,          // ≤ 200 chars
    received_at: string,      // ISO 8601
    is_unread: boolean,
  }],
  next_page_token: string | null,
}

// GET /emails/:id response
{
  id: string,
  from_name: string | null,
  from_email: string,
  to_emails: string[],
  cc_emails: string[],
  subject: string,
  body_text: string,          // HTML stripped, ready for voice
  received_at: string,
  is_unread: boolean,
}
```

## 4. Segurança & Privacidade

- **Auth obrigatória:** `Depends(current_user)` em ambos endpoints
- **Multi-conta isolation:** V1 single account, usa `settings.USER_ID`; multi-account em E6/V2
- **TTL 24h:** cron 0002 apaga `body_cached` > 24h
- **Logging:** zero logs de subjects, bodies, email addresses (AC-8). Só IDs + `status_code` + `email_count`
- **Revoke cascade:** DELETE `users` cascade apaga `google_accounts` cascade apaga `email_cache`
- **HTML sanitization:** body HTML → texto puro via `html.parser.HTMLParser` stdlib (sem risco de XSS no frontend)

## 5. UX (wireframe mental)

### `/inbox`
```
┌─────────────────────────────┐
│ Caixa de entrada            │  ← header sticky
│ 12 não lidos                │
├─────────────────────────────┤
│ ● J  João Silva       há 2h │
│      Proposta nova...       │  ← item não-lido (bullet)
│      Vi a proposta e acho...│
├─────────────────────────────┤
│   M  Maria Pinto    ontem   │
│      Reunião 2026-04-16     │
│      A confirmar horário... │
├─────────────────────────────┤
│   ... (até 50)              │
└─────────────────────────────┘
   [Pull down to refresh]
```

### `/email/[id]`
```
┌─────────────────────────────┐
│ ← Voltar                    │
├─────────────────────────────┤
│ João Silva                  │
│ joao@example.com            │
│ 15 Abr · 14:32              │
│                             │
│ Assunto:                    │
│ Proposta nova para parceria │
├─────────────────────────────┤
│                             │
│ Bom dia JP,                 │
│                             │
│ Gostaria de propor...       │  ← body_text scrollable
│ (HTML convertido para texto)│
│                             │
└─────────────────────────────┘
```

### Componentes
- `<InboxList />` client component com TanStack Query
- `<EmailItem />` card click → navigate
- `<EmailDetail />` client component com `use` hook para fetch
- `<EmailSkeleton />` placeholder durante loading
- `<PullToRefresh />` wrapper (simples: touchstart/touchmove; biblioteca só se necessário)

### PT-PT copy
- "Caixa de entrada"
- "não lidos" / "não lido"
- "Sem emails"
- "A carregar…"
- "Voltar"
- "há N minutos/horas", "ontem", "dd MMM"
- Erros: "Não foi possível carregar. Puxa para tentar de novo."

## 6. Aceitação (Gherkin)

### AC-2.1: Listar 50 emails recentes
```gherkin
Dado que user autenticado com cookie __Host-session válido
Quando chama GET /emails/list
Então recebe 200 com JSON {emails: array tamanho <= 50, next_page_token}
E cada email tem {id, from_name, from_email, subject, snippet, received_at, is_unread}
E o backend não loga subject nem snippet em texto livre
```

### AC-2.2: Abrir email específico
```gherkin
Dado que user autenticado
E existe um email com gmail_message_id = "abc123" na sua conta
Quando chama GET /emails/abc123
Então recebe 200 com body_text como string (HTML strippado)
E body_cached é persistido em email_cache com created_at = now
```

### AC-2.3: Inbox renderiza após login
```gherkin
Dado que user faz login completo via E1
E é redirecionado para /inbox
Quando a página carrega
Então fetch a /emails/list com credentials: include
E os 50 items são renderizados em < 2s
```

### AC-2.4: Pull-to-refresh
```gherkin
Dado que user está em /inbox com lista carregada
Quando faz pull-down gesture no topo
Então TanStack Query invalida cache de ["emails", "list"]
E a lista atualiza com spinner visível
```

### AC-2.5: Abrir email detail
```gherkin
Dado que user clica num item da inbox
Quando navegação completa
Então URL é /email/{gmail_message_id}
E body_text está visível scrollable
E header mostra from, subject, data formatada PT-PT
```

### AC-2.6: Token refresh silencioso
```gherkin
Dado que user tem access_token expirado (> 1h)
Quando chama GET /emails/list
Então backend faz refresh automático com refresh_token
E atualiza access_token_encrypted + access_token_expires_at
E response é 200 (user não vê nada de diferente)
```

### AC-2.7: Refresh token revogado externamente
```gherkin
Dado que user revogou acesso em myaccount.google.com
Quando chama GET /emails/list
Então Gmail API retorna invalid_grant
E backend apaga google_accounts do user
E retorna 401
E cookie __Host-session é cleared
E frontend redireciona para /
```

### AC-2.8: Rate limit
```gherkin
Dado que user já fez 10 calls a /emails/list no último minuto
Quando faz a 11ª call
Então recebe 429 com Retry-After header
```

## 7. Não-Objetivos (adiados)

- Attachments download/preview
- Labels, starred, important filters
- Full-text search
- Thread view (só 1ª mensagem do thread em V1)
- Compose / reply / forward (E4/E5)
- Archive / delete / spam marking
- Gmail push notifications (E8 V2)
- Multi-account switching (E6 V2)
- Offline queue (E8 V2)

---

**Fim do SPEC.**
