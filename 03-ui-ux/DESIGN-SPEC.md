# Per4Biz — Especificação de Design Mobile (PWA)

**Produto:** Copiloto vocal de email e agenda multi-conta Google
**Plataforma:** PWA (iOS/Android) — mobile-first
**Persona:** Profissional 20–40 anos, multitasker, responde email em deslocamento
**Versão do documento:** 1.0 — 2026-04-15

---

## 1. Design Principles

1. **Voice-first, touch-fallback.** A voz é o input primário. Todo fluxo crítico (ler, responder, agendar) tem caminho vocal de 1 toque; o toque existe como fallback silencioso (metrô, reunião).
2. **Glance-able inbox.** 3 segundos para entender o que importa. Hierarquia brutal: remetente → assunto → snippet → conta. Nada decorativo.
3. **One-thumb reachable.** Ações primárias sempre na zona inferior (último terço da tela). Thumb zone é sagrado.
4. **Multi-conta sem fricção.** O usuário nunca pergunta "em qual conta estou respondendo?" — o contexto é visível, mudável em 1 gesto, e o AI escolhe a conta certa por default.
5. **Silent confidence.** Feedback visual sutil, háptico generoso, som apenas quando essencial (início/fim de gravação). Um app de produtividade não grita.

---

## 2. Sistema Visual

### Paleta de cores

**Tema claro**
- Primária: `#0A84FF` (azul elétrico, CTA, voice button)
- Secundária: `#1C1C1E` (texto principal)
- Background: `#FFFFFF` / Surface: `#F2F2F7` / Divider: `#E5E5EA`
- Accent (voz ativa): `#FF375F` (rosa vibrante — só durante gravação)
- Sucesso: `#34C759` · Erro: `#FF3B30` · Info/Aviso: `#FF9500`
- Texto secundário: `#6E6E73` · Texto terciário: `#AEAEB2`

**Tema escuro**
- Primária: `#0A84FF` (mantém)
- Background: `#000000` / Surface: `#1C1C1E` / Surface elevada: `#2C2C2E`
- Accent: `#FF6482` · Sucesso: `#30D158` · Erro: `#FF453A`
- Texto: `#FFFFFF` / `#EBEBF5` a 60% / `#EBEBF5` a 30%

**Cores de conta (multi-conta tinting)** — 6 hues atribuídas automaticamente:
`#0A84FF · #FF9500 · #AF52DE · #34C759 · #FF375F · #5AC8FA`

### Tipografia

- **Fonte:** Inter (variable), fallback para `-apple-system, SF Pro, Roboto`
- **Escala:**
  - Display: 32px / 700 / -0.5 tracking
  - Title: 22px / 600
  - Headline: 17px / 600 (assunto de email)
  - Body: 15px / 400 (snippet, corpo)
  - Subhead: 13px / 500 (metadados)
  - Caption: 11px / 500 / uppercase +0.5 tracking (badges, timestamps)
- Line-height: 1.4 para body, 1.2 para títulos

### Espaçamento

Sistema base **4px**. Tokens: `4, 8, 12, 16, 20, 24, 32, 48, 64`.
Padding de tela padrão: **20px lateral**, **16px vertical entre seções**.

### Shape e elevação

- Radius: `sm=8px · md=12px · lg=16px · xl=24px · pill=999px`
- Cards: radius 16px, background surface, sem borda no dark mode
- Sombras (apenas tema claro):
  - Elevation-1: `0 1px 2px rgba(0,0,0,0.04)`
  - Elevation-2: `0 4px 12px rgba(0,0,0,0.08)` (cards flutuantes)
  - Voice button: `0 8px 24px rgba(10,132,255,0.35)`
- No dark mode, elevação via cor de surface, não sombra.

### Iconografia

**Lucide Icons** (stroke 1.5–2, consistente com a leveza da tipografia). Tamanhos: 16, 20, 24, 28px. Evitar Heroicons (estilo conflita com Inter).

---

## 3. Arquitetura de Telas (Sitemap)

```
Onboarding
├─ Welcome
├─ Google Sign-in (1ª conta)
├─ Permissões (Gmail, Calendar, microfone, notificações)
└─ Tutorial vocal (30s)

App (pós-login)
├─ Inbox unificada  [tela home]
│  ├─ Detalhe do email
│  │  └─ Composer (reply contextual)
│  └─ Composer vocal (FAB)
├─ Agenda
│  ├─ Dia / Semana / Mês
│  └─ Detalhe do evento → Criar evento vocal
├─ Contatos
│  └─ Detalhe do contato
└─ Configurações
   ├─ Contas Google (lista, adicionar, renomear, cor, remover)
   ├─ Voz (idioma, wake-word, sensibilidade)
   ├─ Notificações
   ├─ Aparência (tema, densidade)
   └─ Sobre / Privacidade

Overlays globais
├─ Seletor rápido de conta ativa (pull-down do topo)
├─ Composer vocal (modal full-screen)
└─ Comando vocal global (long-press no FAB em qualquer tela)
```

---

## 4. Wireframes Descritivos

### 4.1 Inbox Unificada (Home)

```
┌─────────────────────────────┐
│ ≡   Todas as contas  ▾   🔍 │  ← header 56px, safe-area top
├─────────────────────────────┤
│ ● Ana Costa        14:32  ● │  ← dot azul = conta 1
│   Proposta Q2                │
│   Olha, revisei e acho que…  │
├─────────────────────────────┤
│ ● Banco XP         13:10  ● │  ← dot laranja = conta 2
│   Extrato disponível         │
├─────────────────────────────┤
│ ○ João Silva       11:45    │  ← ○ = já lido
│   Re: reunião terça          │
├─────────────────────────────┤
│           …                 │
│                             │
│                       ┌───┐ │
│                       │ 🎙 │ │  ← FAB voice (64px, bottom-right)
│                       └───┘ │
└─────────────────────────────┘
```

- Header sticky com nome da conta ativa (ou "Todas"), dropdown, busca
- Lista de emails: 72px de altura cada, swipe gestures habilitados
- Dot colorido à esquerda = conta de origem (4px de largura vertical)
- FAB voice: 64px, cor primária, sombra elevada, always-on-top
- Pull-to-refresh com animação de waveform (não spinner genérico)

### 4.2 Composer Vocal (Tela-estrela) — ver seção 5

### 4.3 Detalhe do Email

```
┌─────────────────────────────┐
│ ←                    ⋯      │
├─────────────────────────────┤
│ Proposta Q2                 │  ← Title 22/600
│                             │
│ 👤 Ana Costa                │  ← avatar 40px
│ para: você (conta pessoal)  │  ← caption, mostra conta
│ 14:32 · hoje                │
├─────────────────────────────┤
│                             │
│  Corpo do email com         │
│  tipografia confortável     │
│  em 15px, line-height 1.5   │
│                             │
├─────────────────────────────┤
│ ┌─────────────────────────┐ │
│ │ 🎙  Responder por voz   │ │  ← CTA primário 56px
│ └─────────────────────────┘ │
│  Encaminhar · Arquivar      │  ← ações secundárias
└─────────────────────────────┘
```

### 4.4 Agenda

- Toggle segmentado no topo: Dia | Semana | Mês (pill style)
- Visualização Dia: timeline vertical, blocos coloridos por conta
- FAB mantém composer vocal (entende "agendar reunião amanhã às 10")
- Hoje destacado com barra vertical primária

### 4.5 Configurações → Contas Google

- Lista de cards, cada card com: avatar, email, nickname editável, cor atribuída, toggle "ativa na inbox unificada"
- Botão "+ Adicionar conta Google" (pill, primário)
- Swipe left no card revela "Remover" destrutivo

---

## 5. Tela-estrela: Composer Vocal

Modal **full-screen**, apresentação com slide-up + scale do FAB (250ms ease-out).

```
┌─────────────────────────────┐
│ ✕                  Pessoal▾ │  ← fechar + seletor de conta
├─────────────────────────────┤
│                             │
│   Para: Ana Costa           │  ← chip, editável
│                             │
│   "Oi Ana, tudo bem? Sobre  │  ← transcrição live
│    a proposta que você…"    │     em 22px/500
│                             │
│   ╱╲╱╲╱╲╱╲╱╲╱╲╱╲╱╲          │  ← waveform animado
│                             │
├─────────────────────────────┤
│        ┌─────────┐          │
│        │   ■     │          │  ← botão grande 96px
│        └─────────┘          │     vermelho pulsante
│   Toque para pausar         │
└─────────────────────────────┘
```

**Botão principal:** push-to-talk tap (toque inicia, toque finaliza). Long-press ativa modo contínuo. Wake-word "Ei Per4" opcional (configurável).

**Estados:**

| Estado | Visual | Háptico | Som |
|---|---|---|---|
| **idle** | Botão azul, ícone 🎙 estático | — | — |
| **listening** | Botão vermelho `#FF375F`, pulsação 1.5s, waveform reativo ao volume | Impact light ao iniciar | Bip curto (opcional) |
| **processing** | Botão azul, spinner circular ao redor, "Gerando resposta…" | Selection | — |
| **draft-ready** | Card com draft editável, 2 CTAs: "Enviar" / "Refazer" | Success notif | — |
| **sending** | Botão vira barra de progresso horizontal | — | — |
| **sent** | Checkmark verde em 400ms, auto-dismiss após 800ms | Success impact | Bip de confirmação |

**Transcrição em tempo real:** aparece no centro da tela em tipografia 22px/500, com palavras confirmadas em preto e palavras em hipótese em cinza (60% opacity). Fade-in de 120ms por palavra.

**Draft AI:** após processing, transcrição é substituída por card com o email gerado (assunto + corpo). Editável por:
- **Voz:** "Muda o tom para mais formal", "Remove a última frase", "Adiciona um cumprimento"
- **Toque:** tap no texto abre teclado, edição inline

**Seletor de conta no composer:** dropdown no header mostra conta que enviará. AI sugere por default baseado em: (a) conta que recebeu o original (se reply), (b) contato conhecido, (c) última conta usada.

---

## 6. Interações e Microinterações

**Swipe actions na inbox (72px de altura):**
- Swipe right curto (25%): marcar lido/não-lido (cinza)
- Swipe right longo (60%): arquivar (verde `#34C759`)
- Swipe left curto (25%): responder por voz (azul primário) — abre composer já endereçado
- Swipe left longo (60%): deletar (vermelho, com confirmação haptic heavy)

**Háptico (via Vibration API + iOS Haptic Engine quando disponível):**
- Tap em botão primário: light (10ms)
- Início de gravação: medium
- Envio bem-sucedido: success notification pattern
- Erro: error notification pattern
- Swipe ultrapassando threshold: selection

**Animações:**
- Transições entre telas: slide lateral 280ms `cubic-bezier(0.32, 0.72, 0, 1)` (iOS-like)
- Modal composer: slide-up + fade 250ms
- Lista: stagger de 30ms entre items no primeiro load
- **`prefers-reduced-motion`:** substitui slides por crossfade de 150ms, remove pulsações, mantém waveform (é informativo)

**Pull-to-refresh:** threshold 80px, resistência progressiva, libera para sincronizar. Animação de waveform horizontal (3 ondas) em vez de spinner. Haptic light ao passar do threshold.

---

## 7. Multi-conta — Experiência Visual

**Percepção de conta ativa:**
- Barra colorida vertical de 4px na lateral esquerda de cada item (cor da conta)
- No header: nome da conta + chevron (ou "Todas as contas" na inbox unificada)
- No composer: chip "De: [conta]" sempre visível no topo

**Seletor rápido:**
- **Gesto primário:** swipe down de 40px no header da inbox abre overlay com lista de contas (chips grandes, tap para filtrar)
- **Gesto secundário:** long-press no avatar do header (600ms) abre o mesmo overlay
- Overlay fecha com swipe up ou tap no fundo

**Inbox unificada:**
- Por default mostra todas as contas
- Cada email: barra colorida à esquerda + micro-avatar 16px da conta no canto inferior direito do item (opcional em modo denso)
- Badge de contagem por conta no seletor

**Nomeação:** usuário pode renomear ("Pessoal", "Trabalho", "Freelance") em Configurações. Cor é auto-atribuída mas editável.

---

## 8. Acessibilidade (WCAG AA+)

- **Contraste:** todos os pares texto/background ≥ 4.5:1 (body) e ≥ 3:1 (títulos grandes). Testado nos dois temas.
- **Touch targets:** mínimo **48×48px** (superamos 44×44 exigido). FAB voice: 64px. Botão de gravação: 96px.
- **Screen readers:** todos os elementos têm `aria-label` em português. Estados do composer anunciados via `aria-live="polite"` (ironicamente crítico — usuário cego usa este app tanto quanto usuário vidente).
- **Focus visible:** ring azul `#0A84FF` de 3px com offset de 2px em todos os interativos quando navegação por teclado (PWA em desktop com teclado externo).
- **Fontes escaláveis:** respeita `Dynamic Type` iOS e `font-size` do sistema Android (até 200%).
- **Transcrição sempre visível** durante gravação (não só áudio) — beneficia surdos e ambientes ruidosos.

---

## 9. PWA Specifics

- **Splash screen:** background `#0A84FF` (claro) ou `#000000` (escuro), logo centralizado 120px, sem texto (mais rápido).
- **Ícone adaptativo:** SVG mascarável com safe zone de 40%. Fundo sólido primário, símbolo em branco (ondas sonoras estilizadas).
- **Manifest:** `display: "standalone"`, `orientation: "portrait"`, `theme_color` dinâmico (claro/escuro), `background_color` igual ao splash.
- **Safe-areas iOS:**
  - Header usa `env(safe-area-inset-top)` (padding adicional)
  - FAB voice posicionado com `bottom: calc(24px + env(safe-area-inset-bottom))`
  - Modal composer respeita notch (dynamic island) com top padding 54px em devices novos
- **Offline:** inbox cacheada (últimos 50 emails por conta), composer funciona offline com fila de envio, sincroniza ao reconectar (indicador sutil no header).
- **Install prompt:** banner educativo após 3ª sessão, dismissível, nunca invasivo.

---

## 10. Componentes Reutilizáveis (Design System Mini)

| Componente | Variantes | Notas |
|---|---|---|
| **Button** | primary, secondary, ghost, destructive · sm(36px) md(44px) lg(56px) | Radius 12px; loading state com spinner inline |
| **VoiceButton** | fab(64px), hero(96px), inline(48px) · idle/listening/processing | Estado domina o visual; pulsação CSS 1.5s |
| **Card** | default, elevated, selectable | Radius 16px, padding 16px |
| **EmailListItem** | unread, read, selected, swiping | Barra colorida left 4px, altura 72px |
| **AccountBadge** | dot(8px), chip(com label), avatar-ring(colorido) | Cor da conta sempre consistente |
| **Chip** | filter, input, suggestion | Radius pill, altura 32px |
| **Toast** | success, error, info, voice-hint | Slide-up bottom, auto-dismiss 3s |
| **Waveform** | live(reativo), static(placeholder), mini(16px inline) | Canvas ou SVG animado |
| **TranscriptText** | confirmed, hypothesis, edited | Cinza → preto fade |
| **Modal** | bottom-sheet, full-screen, dialog | Drag-handle no topo do bottom-sheet |
| **Avatar** | 24, 32, 40, 64px · com ring de conta ou sem | Fallback iniciais |
| **Segmented Control** | 2, 3, 4 opções | Usado em agenda (dia/semana/mês) |
| **ListRow** | default, with-icon, with-toggle, destructive | Altura 56px, usado em settings |

**Tokens globais a exportar:** `colors`, `spacing`, `radius`, `shadows`, `motion` (durations + easings), `typography` (escalas).

---

**Próximos passos recomendados:** validar composer vocal em protótipo Figma clicável com 5 usuários da persona antes de codar; priorizar testes de latência do ASR (<400ms idealmente) porque impacta mais a percepção de qualidade do que qualquer escolha visual deste documento.
