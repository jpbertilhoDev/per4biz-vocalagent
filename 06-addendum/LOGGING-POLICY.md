# Logging Policy — Per4Biz

**Documento crítico de privacidade + observabilidade.** Per4Biz processa dados sensíveis (emails pessoais, transcrições de voz, tokens OAuth). Logar mal = incidente GDPR + multa até 4% do turnover.

---

## 1. Princípios

1. **Logar o suficiente para debugar — nunca mais.** Minimização é regra.
2. **PII nunca vai para logs externos.** Nunca. Nem uma única vez. Sentry, Axiom, GitHub Actions logs, CloudWatch, nenhum.
3. **IDs em vez de valores.** Logar `user_id` (UUID), nunca `email`. Logar `message_id` (Gmail), nunca `subject` ou `body`.
4. **Redacção automática > confiança no programador.** Middleware redacta tokens/emails antes de escrever.
5. **Retention mínima.** 90 dias max em Axiom; Sentry já purge em 30 dias.

---

## 2. Categorias — o que logar vs NUNCA logar

### ✅ Logar SEMPRE

| Categoria | Exemplos | Porquê |
|---|---|---|
| **Request metadata** | `request_id`, `path`, `method`, `status_code`, `latency_ms`, `user_agent` | Observabilidade standard |
| **User ID (UUID Supabase)** | `user_id` como UUID | Rastrear user sem expor identidade |
| **Account ID (UUID interno)** | `google_account_id` como UUID | Debug multi-conta sem email |
| **Gmail message ID** | `gmail_message_id` (opaco) | Rastrear sem ler conteúdo |
| **Intent classificado** | `"read_inbox"`, `"reply_email"`, `"create_event"` | Melhorar agente |
| **Latências de pipeline** | `stt_ms`, `intent_ms`, `llm_ms`, `tts_ms`, `total_ms` | SLO monitoring |
| **Códigos de erro (genéricos)** | `"gmail_401"`, `"groq_timeout"`, `"invalid_grant"` | Troubleshooting |
| **Feature flags ativos** | `{voice_agent: true, multi_account: false}` | Debug com contexto |
| **Versão da app** | Git SHA + `package.json` version | Correlacionar bug a release |
| **Device / browser** | `safari/ios-17`, `chrome/android-14` | PWA compat debugging |

### ❌ NUNCA logar

| Categoria | Exemplos | Porquê |
|---|---|---|
| **Corpo de email** | `body_text`, `body_html`, `snippet` | PII máxima — pode conter passwords, dados médicos, legais |
| **Email addresses** | `user@gmail.com`, `ana@empresa.pt` | Identificação direta |
| **Nomes completos** | `display_name`, `from_name`, `to_name` | PII direta |
| **Assuntos de email** | `subject` | Revela contexto pessoal |
| **Transcrições de voz** | Output do STT | PII + expectativa de privacidade forte |
| **Drafts gerados** | `draft_responses.body_text` | Conteúdo pessoal |
| **Tokens OAuth** | `access_token`, `refresh_token`, `id_token` | Credenciais — credential leak = takeover total |
| **API keys internas** | `ANTHROPIC_API_KEY`, etc | Credenciais |
| **JWT assinados** | Supabase JWT raw | Credenciais |
| **IPs completos** | `192.168.1.42` | IP é PII em GDPR — usar hash se necessário |
| **Áudio raw** | Bytes do MediaRecorder | Redundante + pesado + PII |
| **Calendar event details** | Title, description, attendees | PII |
| **Contacts** | Nomes, telefones, emails | PII |

---

## 3. Níveis de log — uso correto

| Nível | Quando usar | Exemplos |
|---|---|---|
| **DEBUG** | Só em desenvolvimento local (`ENVIRONMENT=development`) | Variáveis intermediárias, state transitions |
| **INFO** | Operações normais de produção | Login, logout, email sent, event created |
| **WARNING** | Anormal mas recuperável | Retry em Gmail API, cache miss, fallback STT |
| **ERROR** | Falha que precisa de investigação | API 5xx persistente, encryption failed, unexpected exception |
| **CRITICAL** | Pager/alerta imediato | ENCRYPTION_KEY missing, DB corrupted, auth bypass tentado |

### Regra de ouro

**DEBUG nunca vai para produção.** Configurar logger root:

```python
# backend/app/config.py
import logging
LOG_LEVEL = logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO
```

```typescript
// frontend/lib/logger.ts
const LOG_LEVEL = process.env.NODE_ENV === 'development' ? 'debug' : 'info';
```

---

## 4. Redacção automática — implementação

### Backend Python (middleware)

```python
# backend/app/logging/redactor.py
import re
import logging

REDACT_PATTERNS = [
    (re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+'), '<email>'),
    (re.compile(r'ya29\.[a-zA-Z0-9_-]+'), '<google_access_token>'),
    (re.compile(r'1//[a-zA-Z0-9_-]+'), '<google_refresh_token>'),
    (re.compile(r'Bearer [a-zA-Z0-9._-]+'), 'Bearer <redacted>'),
    (re.compile(r'eyJ[a-zA-Z0-9._-]+'), '<jwt>'),
]

class RedactFilter(logging.Filter):
    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern, replacement in REDACT_PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        if record.args:
            record.args = tuple(
                self._redact(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True

    def _redact(self, s):
        for pattern, replacement in REDACT_PATTERNS:
            s = pattern.sub(replacement, s)
        return s

# Instalar globalmente
logging.getLogger().addFilter(RedactFilter())
```

### Frontend TypeScript (Sentry beforeSend)

```typescript
// frontend/lib/sentry.ts
import * as Sentry from '@sentry/nextjs';

const EMAIL_RE = /[\w.+-]+@[\w-]+\.[\w.-]+/g;
const TOKEN_RE = /(ya29\.[a-zA-Z0-9_-]+|1\/\/[a-zA-Z0-9_-]+|eyJ[a-zA-Z0-9._-]+)/g;

function redact(s: string): string {
  return s.replace(EMAIL_RE, '<email>').replace(TOKEN_RE, '<token>');
}

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENV,
  beforeSend(event) {
    if (event.message) event.message = redact(event.message);
    if (event.extra) {
      Object.keys(event.extra).forEach(k => {
        if (typeof event.extra![k] === 'string') {
          event.extra![k] = redact(event.extra![k] as string);
        }
      });
    }
    return event;
  },
  denyUrls: [/^chrome-extension:/],
  // Drop breadcrumbs que podem conter body
  beforeBreadcrumb(breadcrumb) {
    if (breadcrumb.category === 'fetch' && breadcrumb.data?.url?.includes('/emails/')) {
      delete breadcrumb.data.response_body;
      delete breadcrumb.data.request_body;
    }
    return breadcrumb;
  },
});
```

---

## 5. Structured logging format

Sempre JSON para facilitar queries em Axiom:

```python
# ✅ Correcto
logger.info(
    "email_sent",
    extra={
        "user_id": user_id,
        "account_id": account_id,
        "gmail_message_id": result.id,
        "latency_ms": elapsed_ms,
    }
)

# ❌ Errado — PII + não estruturado
logger.info(f"Sent email from {user.email} to {to_addr} about '{subject}'")
```

Output esperado em Axiom:

```json
{
  "timestamp": "2026-04-15T12:34:56Z",
  "level": "INFO",
  "message": "email_sent",
  "user_id": "uuid-aqui",
  "account_id": "uuid-aqui",
  "gmail_message_id": "18abcd...",
  "latency_ms": 234,
  "request_id": "req-xyz",
  "service": "backend",
  "version": "sha-abc123"
}
```

---

## 6. Eventos canónicos a instrumentar

### Autenticação (E1)

| Evento | Nível | Campos |
|---|---|---|
| `oauth_flow_started` | INFO | `user_id` (se existente), `redirect_to` |
| `oauth_callback_received` | INFO | `state_valid`, `has_code` |
| `account_linked` | INFO | `user_id`, `account_id`, `scopes` (array) |
| `token_refreshed` | INFO | `account_id`, `expires_in` |
| `token_refresh_failed` | WARNING | `account_id`, `error_code` (ex: `invalid_grant`) |
| `account_revoked` | INFO | `user_id`, `account_id`, `triggered_by` (`user_action` / `invalid_grant`) |
| `csrf_state_invalid` | WARNING | `origin_ip_hash` |
| `encryption_key_missing` | CRITICAL | — |

### Email (E2/E3/E5)

| Evento | Nível | Campos |
|---|---|---|
| `inbox_fetched` | INFO | `user_id`, `account_id`, `count`, `from_cache` (bool), `latency_ms` |
| `email_opened` | INFO | `user_id`, `account_id`, `gmail_message_id` |
| `draft_generated` | INFO | `user_id`, `account_id`, `llm_model`, `tokens_in`, `tokens_out`, `latency_ms` |
| `draft_approved` | INFO | `draft_id` |
| `email_sent` | INFO | `user_id`, `account_id`, `gmail_message_id`, `latency_ms` |
| `email_send_failed` | ERROR | `user_id`, `account_id`, `error_code`, `retry_count` |
| `gmail_api_retry` | WARNING | `account_id`, `endpoint`, `attempt`, `http_status` |

### Voice Agent (E4)

| Evento | Nível | Campos |
|---|---|---|
| `voice_session_started` | INFO | `user_id`, `session_id` |
| `stt_completed` | INFO | `session_id`, `provider` (`groq` / `openai`), `duration_ms`, `latency_ms` |
| `intent_classified` | INFO | `session_id`, `intent`, `confidence`, `latency_ms` |
| `llm_draft_generated` | INFO | `session_id`, `model`, `tokens_in`, `tokens_out`, `latency_ms` |
| `tts_streaming_started` | INFO | `session_id`, `provider` (`elevenlabs` / `web_speech`), `character_count` |
| `voice_session_completed` | INFO | `session_id`, `total_latency_ms`, `intent` |
| `voice_fallback_triggered` | WARNING | `session_id`, `original`, `fallback`, `reason` |

### Segurança / privacy

| Evento | Nível | Campos |
|---|---|---|
| `rls_violation_attempt` | ERROR | `user_id`, `attempted_resource`, `endpoint` |
| `rate_limit_hit` | WARNING | `user_id`, `limit_type`, `window` |
| `encryption_rotation_triggered` | INFO | `old_key_version`, `new_key_version`, `rows_migrated` |
| `gdpr_export_requested` | INFO | `user_id` |
| `gdpr_delete_requested` | INFO | `user_id` |

---

## 7. Sampling em alto volume

Se um evento ocorre > 10k/hora → usar sampling para reduzir custo Axiom:

```python
import random

def should_sample(rate: float = 0.1) -> bool:
    return random.random() < rate

if should_sample(0.1):  # 10% das requests
    logger.info("inbox_fetched", extra={...})
```

**Eventos CRITICAL e ERROR nunca são sampled.**

---

## 8. Retention & compliance

| Storage | Retention | Justificação |
|---|---|---|
| Axiom (logs estruturados) | 90 dias | GDPR Art. 5(1)(e) minimização; suficiente para debugging |
| Sentry (exceptions) | 30 dias (default) | Incidentes resolvidos < 30 dias |
| GitHub Actions logs | 90 dias (auto-purge) | CI debugging |
| Fly.io logs | 7 dias (live) | Short-term debugging |
| Supabase logs | 7 dias (free) / 28 dias (pro) | Query debugging |
| `voice_sessions.audio_url` | 7 dias | ADR — minimização forte |
| `email_cache.body_cached` | 24h | ADR-005 |
| `voice_sessions.transcript` | 30 dias (se user opt-in); sessão apenas caso contrário | Opt-in claro |
| `consent_log` | 7 anos (GDPR audit) | Legal — proof of consent |

---

## 9. Alertas

### Críticos (paging imediato — Slack/email ao JP)

- `encryption_key_missing` — bloqueia boot da app
- `rls_violation_attempt` — potencial security incident
- CRITICAL logs em geral
- Sentry crash rate > 1% em 5 min
- p95 voice latency > 8s em 15 min
- Gmail 5xx rate > 10% em 15 min

### Warnings (notificação, não paging)

- Custo LLM diário > €10 (cap suave)
- Rate limit hits > 100/dia (pode indicar scaling)
- Token refresh failures > 5%/hora
- Groq quota 80% usado

---

## 10. Auditoria anual

Uma vez por ano (Q1), percorrer sample aleatório de 1% dos logs em Axiom e validar:

- [ ] Nenhum log contém email address em texto claro
- [ ] Nenhum log contém token OAuth em texto claro
- [ ] Nenhum log contém corpo de email ou draft
- [ ] Nenhum log contém transcript de voz
- [ ] Redacção automática está ativa em todos os workers

Se algum item falhar → incident report imediato + remediation plan.

---

## 11. Checklist antes de cada release

Antes de fazer merge para `main`:

- [ ] Nenhum `console.log()` / `print()` novo com variáveis sensíveis
- [ ] Eventos novos seguem nomeação canónica (snake_case)
- [ ] Campos novos não incluem PII
- [ ] Middleware de redacção cobre qualquer novo formato de token
- [ ] Sentry `beforeSend` continua a redactar tudo o que é esperado
- [ ] Nenhum endpoint novo loga `request.body` sem filtro

Adicionar ao checklist da skill `requesting-code-review`.
