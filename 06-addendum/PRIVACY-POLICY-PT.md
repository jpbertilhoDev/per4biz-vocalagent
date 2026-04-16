# Política de Privacidade — Per4Biz

**Versão:** 1.0 (baseline) · **Data:** 2026-04-15 · **Idioma:** pt-PT

Esta política explica como o **Per4Biz** recolhe, usa e protege os teus dados. Segue o RGPD (Regulamento (UE) 2016/679) e a Lei n.º 58/2019 (execução nacional).

> ⚠️ **Estado baseline:** este documento é um rascunho técnico. Antes do lançamento público (V2, > 100 utilizadores), deve ser revisto por advogado especializado em privacidade digital. Para V1 (beta fechado até 10 utilizadores) funciona como declaração operacional.

---

## 1. Quem é o responsável pelo tratamento

- **Responsável:** João Pedro Bertilho
- **Email de contacto:** jpbertilhopt@gmail.com
- **Estabelecimento:** Portugal
- **V1 (single-tenant):** o Per4Biz é operado num modelo de um único utilizador (o próprio responsável). Esta política reflete o estado V2+ onde haverá utilizadores adicionais.

## 2. Que dados recolhemos

### 2.1 Identidade (via Google OAuth)
- Email Google, nome, foto de perfil, identificador único Google (`sub`)

### 2.2 Dados de email (via Gmail API, sob tua autorização explícita)
- Metadados das últimas 50 mensagens: remetente, destinatários, assunto, data, labels
- Corpo das mensagens que abres ou respondes (**cache com TTL 24h**)
- Identificadores Gmail (`message_id`, `thread_id`)

### 2.3 Dados de interação vocal
- Áudio da tua voz quando gravas uma resposta (**retenção 7 dias**)
- Transcrição (texto) desse áudio (**session-only por defeito**; 30 dias se fizeres opt-in)
- Resposta gerada pelo modelo de linguagem
- Áudio de síntese (TTS) reproduzido para ti
- Métricas de latência (ms em cada etapa do pipeline)

### 2.4 Dados técnicos
- Endereço IP (SHA-256 hash, nunca plaintext)
- User agent do browser (família, sem PII)
- Timestamps de eventos (login, envio, revoke)

**Não recolhemos:** dados bancários, localização GPS, contactos externos ao Google, dados de menores de 16 anos.

## 3. Para que usamos os dados

| Finalidade | Dados usados | Base legal (RGPD Art. 6) |
|---|---|---|
| Autenticar-te na app | Identidade Google | Consentimento (1(a)) + Execução do contrato (1(b)) |
| Listar os teus emails | Metadados + corpo (24h cache) | Execução do contrato |
| Gerar resposta por voz | Áudio + transcrição + LLM | Execução do contrato |
| Enviar email em teu nome | Corpo do rascunho | Execução do contrato (só com **confirmação explícita tua**) |
| Logs de segurança | IP hashed, timestamps | Interesse legítimo (1(f)) — prevenção de fraude |
| Melhorar qualidade vocal (opcional) | Transcrições 30d | Consentimento explícito (1(a)); opt-in em Definições |

**Confirmação obrigatória antes de enviar:** nunca enviamos email sem aprovares explicitamente o rascunho.

## 4. Partilha com terceiros (sub-processadores)

| Fornecedor | Dados partilhados | Finalidade | Localização |
|---|---|---|---|
| **Google** (Gmail API) | Leitura/envio de emails em teu nome | Funcionalidade core | UE |
| **Groq** (Whisper v3 + Llama 3.3) | Áudio + texto transcrito + conteúdo do rascunho | STT + classificação + geração | EUA (SCC) |
| **ElevenLabs** (TTS) | Texto da resposta | Síntese de voz PT-PT | EUA (SCC) |
| **Supabase** (BD + Storage) | Identidade + metadados + cache | Armazenamento operacional | UE (Frankfurt) |
| **Vercel** (frontend) | Metadados de requisição | Servir o PWA | UE/global edge |
| **Fly.io** (backend) | Metadados de requisição | Correr o microserviço Python | UE (Madrid) |
| **Sentry** (V1.x+) | Stack traces com PII redactada | Observabilidade de falhas | UE |
| **Axiom** (V1.x+) | Logs estruturados com PII redactada | Observabilidade | UE |

**Não vendemos, alugamos ou cedemos dados a terceiros com fins comerciais.**

## 5. Retenção de dados

| Tipo | Retenção | Motivo |
|---|---|---|
| Corpo de email em cache | **24h máximo** | Minimização (RGPD Art. 5(1)(c)) |
| Metadados de email | Enquanto a conta estiver ativa | Operacional |
| Áudio de gravações vocais | **7 dias** | Debugging + recurso curto |
| Transcrições de voz | **Session-only** (default) · 30d se fizeres opt-in | Escolha tua |
| Rascunhos enviados | Enquanto a conta estiver ativa | Histórico |
| Logs de segurança | 90 dias | Deteção de abuso |
| Dados após apagares conta | **0** (cascade delete + Google revoke imediatos) | RGPD Art. 17 |

## 6. Os teus direitos (RGPD Cap. III)

Podes exercer qualquer um destes direitos diretamente na app ou contactando-nos:

- **Aceder** aos teus dados → `Definições → Conta Google → Exportar dados` (JSON)
- **Corrigir** dados incorretos → editar em Definições
- **Apagar** a tua conta → `Definições → Conta Google → Desvincular e apagar conta` (irreversível)
- **Limitar** o tratamento → desligar funcionalidades em Definições (voz, transcripts, sync)
- **Portabilidade** → export JSON em formato standard
- **Opor-te** a tratamentos baseados em interesse legítimo → contacta-nos
- **Retirar consentimento** em qualquer momento (ex: desligar transcripts 30d) → Definições
- **Reclamar à CNPD** → [www.cnpd.pt](https://www.cnpd.pt)

Resposta a pedidos em até **30 dias** (RGPD Art. 12).

## 7. Cookies

Usamos apenas cookies **estritamente necessários**:

| Cookie | Finalidade | Flags | Duração |
|---|---|---|---|
| `__Host-session` | Autenticação | HttpOnly, Secure, SameSite=Lax | 7 dias |

**Não usamos** cookies de tracking, publicidade ou analítica externa em V1.

## 8. Segurança

- **Cifra em trânsito:** TLS 1.3 em todas as comunicações
- **Cifra em repouso:** refresh tokens Google cifrados com AES-256-GCM antes de gravar na BD
- **Controlo de acesso:** `ALLOWED_USER_EMAIL` gating no backend em V1 (single-tenant)
- **Auditoria:** logs estruturados com PII redactada automaticamente
- **Rotação de chaves:** `key_version` permite rotação trimestral sem downtime

Em caso de **incidente de segurança**, notificamos-te em até **72 horas** (RGPD Art. 33/34).

## 9. Transferências internacionais

Groq e ElevenLabs estão sediados nos EUA. As transferências são protegidas por:
- **Standard Contractual Clauses (SCC)** aprovadas pela Comissão Europeia
- **Data Processing Addendum (DPA)** assinado com cada fornecedor

## 10. Crianças

O Per4Biz não se destina a menores de 16 anos. Se descobrires que uma conta foi criada por um menor, contacta-nos para apagamento imediato.

## 11. Alterações a esta política

Versionamos esta política em `consent_log`. Alterações materiais exigem o teu consentimento renovado antes de continuar a usar a app.

| Versão | Data | Alterações |
|---|---|---|
| 1.0 (baseline) | 2026-04-15 | Criação inicial para V1 beta |

## 12. Contacto

- Email: **jpbertilhopt@gmail.com**
- Assunto sugerido: `[Per4Biz Privacy]`

---

*Baseline técnico escrito pelo squad mkt-agency. Para lançamento público V2, rever com advogado especializado em RGPD.*
