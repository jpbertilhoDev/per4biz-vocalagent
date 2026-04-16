# Per4Biz — Especificação de Design Mobile (PWA)

**Produto:** Per4Biz — Agente vocal de email multi-conta Google
**Plataforma:** PWA (iOS/Android) — mobile-first
**Persona:** Profissional 20–40 anos, multitasker, responde email em deslocamento
**Versão do documento:** 2.0 — 2026-04-16 (pivot chat-first + redesign visual)

> **Mudança v2.0:** Pivot de inbox-first para chat-first. O agente **Vox** é a tela principal. Inbox vira tab secundária. Paleta mudou de iOS-native para Arc+Raycast (dark-first, violet+cyan). Onboarding redesenhado.

---

## 1. Design Principles

1. **Chat-first, voice-native.** O agente Vox é o centro do produto. O utilizador abre o app e fala — não precisa de navegar menus. A inbox existe como referência, não como ponto de entrada.
2. **Vox é o interface.** Reduzir camadas: em vez de tocar → abrir → ler → responder, o fluxo é falar → Vox age. Tudo o que Vox pode fazer por voz não precisa de botão.
3. **One-thumb reachable.** Ações primárias sempre na zona inferior (último terço da tela). O botão de microfone é o elemento mais importante do ecrã.
4. **Glass depth, not flatness.** Superfícies com vidro fosco (frost glass) criam hierarquia visual sem sombras pesadas. Profundidade comunica estado — glass ativo = processando, glass opaco = idle.
5. **Dark-first confidence.** Fundo escuro `#0A0A0F` com accents saturados (violet para UI, cyan exclusivamente para voz). O dark não é "modo escuro" — é a identidade.
6. **Multi-conta sem fricção.** O utilizador nunca pergunta "em qual conta estou?" — Vox sabe, sugere, e o contexto é visível no card de acção.

---

## 2. Sistema Visual

### Direção visual: Arc + Raycast

- **Arc:** curvas ousadas, gradients saturados, micro-animações fluidas
- **Raycast:** dark + vidro fosco, cores saturadas pontuais, espaçamento generoso, sombras fortes
- **Resultado:** inovador + premium — tecnológico sem ser frio, curvo sem ser infantil

### Paleta de cores (dark-first, sem tema claro em V1)

**Base**
- Background: `#0A0A0F` (quase preto azulado)
- Surface: `#14141B` (elevação nível 1)
- Surface elevated: `#1E1E28` (elevação nível 2 — glass cards)
- Surface frost: `#1E1E28` a 72% opacity + `backdrop-filter: blur(20px)` (vidro fosco)
- Divider: `#2A2A35`

**Accent**
- Primária: `#6C5CE7` (violet — CTAs, navegação, seleccionado)
- Primária hover: `#7D6FF0`
- Primária muted: `#6C5CE7` a 20% (backgrounds subtis)
- Voz/Audio: `#00CEFF` (cyan — exclusivamente para microfone, waveform, TTS playing, Vox avatar ring)
- Voz glow: `0 0 20px rgba(0, 206, 255, 0.35)` (botão mic quando listening)

**Semânticas**
- Sucesso: `#34D399`
- Erro: `#FF453A`
- Aviso: `#F59E0B`
- Info: `#00CEFF` (partilhado com voz — faz sentido: voz = informação a fluir)

**Texto**
- Primário: `#F0F0F5`
- Secundário: `#9090A0`
- Terciário: `#5A5A6E`
- Inverso (sobre accent): `#FFFFFF`

**Cores de conta (multi-conta tinting)** — 6 hues atribuídas automaticamente:
`#6C5CE7 · #FF9500 · #AF52DE · #34D399 · #FF375F · #5AC8FA`

### Tipografia

- **Fonte UI:** Inter (variable), fallback para `-apple-system, SF Pro, Roboto`
- **Fonte transcript/código:** JetBrains Mono (monospace — usada para transcrição STT em tempo real e snippets de email)

**Escala (Inter):**
- Display: 32px / 700 / -0.5 tracking
- Title: 22px / 600
- Headline: 17px / 600 (assunto de email, títulos de card)
- Body: 15px / 400 (snippet, corpo de email)
- Subhead: 13px / 500 (metadados, timestamps)
- Caption: 11px / 500 / uppercase +0.5 tracking (badges, estados)

**Escala (JetBrains Mono):**
- Transcript live: 16px / 400 (texto a aparecer em tempo real durante STT)
- Email snippet: 13px / 400 (dentro de cards do agente)

- Line-height: 1.4 para body, 1.2 para títulos

### Espaçamento

Sistema base **4px**. Tokens: `4, 8, 12, 16, 20, 24, 32, 48, 64`.
Padding de tela padrão: **20px lateral**, **16px vertical entre seções**.
Espaçamento generoso entre cards no chat: **24px** (Raycast influence — respira).

### Shape e elevação

- Radius: `sm=8px · md=12px · lg=16px · xl=24px · pill=999px`
- Cards: radius 16px, background surface frost (glass blur)
- Sombras (dark mode — usadas selectivamente para depth):
  - Elevation-1: `0 2px 8px rgba(0,0,0,0.3)` (cards padrão)
  - Elevation-2: `0 8px 32px rgba(0,0,0,0.5)` (modais, bottom sheets)
  - Glow violet: `0 0 24px rgba(108,92,231,0.25)` (CTA button)
  - Glow cyan: `0 0 24px rgba(0,206,255,0.35)` (mic button listening)

### Gradient signature

- **Hero gradient:** `linear-gradient(135deg, #6C5CE7, #00CEFF)` — usado em splash, onboarding highlights, e momentos de "wow"
- **Glass gradient:** `linear-gradient(180deg, rgba(30,30,40,0.72), rgba(20,20,27,0.92))` — backdrop de modais e overlays

### Iconografia

**Lucide Icons** (stroke 1.5–2). Tamanhos: 16, 20, 24, 28px.
Cores: primário `#F0F0F5` default, `#6C5CE7` quando activo/seleccionado, `#00CEFF` para ícones de voz.

---

## 3. Arquitetura de Telas (Sitemap)

```
Onboarding (primeira vez)
├─ Splash (logo Per4Biz + glow violet)
├─ Ecrã 1: "Fala com os teus emails" (illustração + copy)
├─ Ecrã 2: "O teu agente vocal" (demonstração Vox)
├─ Google Sign-in (1ª conta)
└─ Chat com Vox → guia permissões (mic, notificações) via cards

App (pós-login)
├─ Chat (Vox)  [tela home ★]
│  ├─ Cards de acção do agente
│  ├─ Linhas de input do utilizador
│  ├─ Botão microfone (tap-to-toggle + auto-silêncio 2s)
│  └─ Inline actions (editar draft, confirmar envio)
├─ Inbox (tab secundária)
│  ├─ Lista de emails (últimos 50)
│  ├─ Detalhe do email
│  └─ Swipe → acções rápidas
├─ Agenda (V2 placeholder — empty state "Disponível em breve")
│  └─ Illustração + "Vox vai gerir a tua agenda"
└─ Settings
   ├─ Contas Google (lista, adicionar, renomear, cor, remover)
   ├─ Voz (idioma, sensibilidade auto-silêncio)
   ├─ Notificações
   └─ Sobre / Privacidade

Overlays globais
├─ Seletor rápido de conta ativa (pull-down do topo de qualquer tab)
└─ Notificações toast (success/error/info)
```

### Bottom Navbar

```
┌─────────────────────────────────────────┐
│                                         │
│              [conteúdo da tab]          │
│                                         │
├─────────────────────────────────────────┤
│   💬      📥      📅      ⚙️           │
│  Chat    Inbox   Agenda  Settings       │
│   ●                                 ← tab activa = dot violet
└─────────────────────────────────────────┘
```

- Altura: 56px + `env(safe-area-inset-bottom)`
- Tab activa: label + dot violet `#6C5CE7`
- Tab inactiva: ícone apenas em `#5A5A6E`
- Fundo: surface frost (glass blur)
- Ícones: Lucide — `MessageCircle` · `Inbox` · `Calendar` · `Settings`

---

## 4. Wireframes Descritivos

### 4.1 Chat com Vox (Home ★)

```
┌─────────────────────────────────┐
│  Vox                     ▾conta │  ← header 56px, nome Vox + seletor conta
├─────────────────────────────────┤
│                                 │
│  ┌─────────────────────────┐    │  ← card glass do agente
│  │ 📧 Ana Costa            │    │     tipo de acção + remetente
│  │ Proposta Q2             │    │     assunto
│  │ "Olha, revisei e acho   │    │     snippet do email
│  │  que podemos avançar…"   │    │
│  │                   ▶ Ouvir│    │     CTA inline
│  └─────────────────────────┘    │
│                                 │
│         "Lê esse email"    14:32│  ← user input (texto simples, dir.)
│                                 │
│  ┌─────────────────────────┐    │  ← card resposta Vox
│  │ 🎤 Transcrição:         │    │     tipo: voz
│  │ "Obrigado Ana, vamos    │    │     transcript do que user disse
│  │  avançar com a proposta" │    │
│  │                          │    │
│  │ 📝 Draft gerado:        │    │     LLM polish
│  │ "Cara Ana, obrigada…    │    │
│  │  [Ver completo]"         │    │
│  │                          │    │
│  │  [✏️ Editar] [📤 Enviar] │    │     CTAs inline no card
│  └─────────────────────────┘    │
│                                 │
│  ┌─────────────────────────┐    │  ← card confirmação
│  │ ✅ Enviado para Ana Costa│    │     tipo: sucesso
│  │ "Proposta Q2"      14:33│    │
│  └─────────────────────────┘    │
│                                 │
├─────────────────────────────────┤
│         ┌───────────┐           │
│         │    🎙     │           │  ← botão mic 64px
│         │           │           │     idle = violet glow
│         └───────────┘           │     listening = cyan glow + pulse
│    "Toca para falar"            │
├─────────────────────────────────┤
│   💬      📥      📅      ⚙️   │  ← bottom navbar
│    ●                           │
└─────────────────────────────────┘
```

**Estrutura do card Vox:**
- Header: ícone de tipo (📧 email lido / 🎤 voz / 📝 draft / ✅ enviado / ❌ erro) + titulo/identificador
- Body: conteúdo relevante (snippet, transcript, draft)
- Footer: CTAs contextuais (Ouvir, Editar, Enviar, Refazer, Cancelar)
- Visual: surface frost (glass blur), radius 16px, elevation-1, border `1px solid rgba(108,92,231,0.15)`

**Tipos de card Vox:**

| Tipo | Ícone | Quando aparece | CTAs |
|---|---|---|---|
| **Email lido** | 📧 | Vox lê email a pedido do user | Ouvir (TTS) · Responder · Arquivar |
| **Transcrição** | 🎤 | User fala, STT completa | Refazer · Gerar draft |
| **Draft** | 📝 | LLM poliu a resposta | Editar (voz/texto) · Enviar · Refazer |
| **Confirmação** | ✅ | Email enviado com sucesso | Ver na inbox · Desfazer (5s) |
| **Erro** | ❌ | Falha em qualquer passo | Tentar de novo · Cancelar |
| **Agenda (V2)** | 📅 | Vox cria/edita evento | Confirmar · Editar · Cancelar |

**Input do utilizador:**
- Texto simples alinhado à direita
- Se input foi voz: mostra transcrição em JetBrains Mono 13px
- Se input foi texto: mostra texto digitado em Inter 15px
- Timestamp à direita em caption

### 4.2 Inbox (Tab secundária)

```
┌─────────────────────────────────┐
│  Inbox                   🔍  ▾  │  ← header com busca + seletor conta
├─────────────────────────────────┤
│ ● Ana Costa          14:32   ● │  ← dot violet = conta 1
│   Proposta Q2                   │
│   Olha, revisei e acho que…     │
├─────────────────────────────────┤
│ ● Banco XP           13:10   ● │  ← dot laranja = conta 2
│   Extrato disponível            │
├─────────────────────────────────┤
│ ○ João Silva         11:45     │  ← ○ = já lido, texto terciário
│   Re: reunião terça             │
├─────────────────────────────────┤
│           …                     │
├─────────────────────────────────┤
│   💬      📥      📅      ⚙️   │
│          ●                      │
└─────────────────────────────────┘
```

- Header sticky com nome da conta ativa (ou "Todas"), dropdown, busca
- Lista de emails: 72px de altura cada, swipe gestures habilitados
- Dot colorido à esquerda = conta de origem (4px de largura vertical)
- Pull-to-refresh com animação de waveform (cyan)
- Sem FAB voice — o chat é a tab ao lado

### 4.3 Detalhe do Email (a partir da Inbox)

```
┌─────────────────────────────────┐
│ ←                      ⋯        │
├─────────────────────────────────┤
│ Proposta Q2                     │  ← Title 22/600
│                                 │
│ 👤 Ana Costa                    │  ← avatar 40px
│ para: você (conta pessoal)      │  ← caption, mostra conta
│ 14:32 · hoje                    │
├─────────────────────────────────┤
│                                 │
│  Corpo do email com             │
│  tipografia confortável         │
│  em 15px, line-height 1.5       │
│                                 │
├─────────────────────────────────┤
│ ┌─────────────────────────────┐ │
│ │ 🎤  Dizer ao Vox           │ │  ← CTA primário violet
│ └─────────────────────────────┘ │
│  Encaminhar · Arquivar          │  ← ações secundárias
└─────────────────────────────────┘
```

- CTA "Dizer ao Vox" redireciona para tab Chat com contexto do email

### 4.4 Agenda (V2 placeholder)

```
┌─────────────────────────────────┐
│  Agenda                         │
├─────────────────────────────────┤
│                                 │
│         📅                      │
│                                 │
│   Disponível em breve           │
│                                 │
│   Vox vai gerir a tua agenda.   │
│   Diz "agenda" no chat para     │
│   ser notificado.               │
│                                 │
├─────────────────────────────────┤
│   💬      📥      📅      ⚙️   │
│                 ●               │
└─────────────────────────────────┘
```

### 4.5 Settings

- Lista de ListRow components (56px altura cada)
- Contas Google: cards com avatar, email, nickname editável, cor atribuída, toggle "ativa na inbox unificada"
- Botão "+ Adicionar conta Google" (pill, violet)
- Voz: sensibilidade auto-silêncio slider (1s-5s), idioma PT-PT
- Sobre: versão, privacidade, logout

---

## 5. Tela-estrela: Chat com Vox

O chat **é** o produto. Cada conversa com Vox é uma sessão contínua — não há "nova conversa" como no ChatGPT. O histórico persiste.

### Botão Microfone

- Posição: centro do fundo do chat, acima da bottom navbar
- Tamanho: 64px circular
- Corpo: surface elevated `#1E1E28`
- Ícone: Lucide `Mic` (24px)

**Estados:**

| Estado | Visual | Háptico | Som |
|---|---|---|---|
| **idle** | Ícone Mic violet `#6C5CE7`, glow violet subtil | — | — |
| **listening** | Ícone Mic cyan `#00CEFF`, glow cyan forte `0 0 24px rgba(0,206,255,0.35)`, pulsação 1.5s, ring animado a crescer | Impact medium ao iniciar | Bip curto (opcional) |
| **silence-detected** | Mic transition de cyan → violet (300ms), "A processar…" | Selection | — |
| **processing** | Mic violet, spinner circular cyan ao redor, label "Vox a pensar…" | — | — |
| **speaking** (TTS) | Ring cyan animado tipo equalizer, label "Vox a falar…" | — | Áudio TTS |
| **error** | Mic vermelho `#FF453A` flash 200ms, volta a idle | Error | — |

### Input de voz: Tap-to-toggle + auto-silêncio

1. User toca no mic → listening inicia
2. User fala — transcrição aparece em tempo real acima do botão
3. Após **2s de silêncio** → auto-stop → processamento começa
4. User pode tocar manualmente para parar antes do auto-silêncio
5. Toque durante processing → cancela (com confirmação háptica)

**Transcrição em tempo real:** aparece acima do botão mic em JetBrains Mono 16px, com palavras confirmadas em `#F0F0F5` e palavras em hipótese em `#5A5A6E`. Fade-in de 120ms por palavra. Máximo 3 linhas visíveis — scroll interno se exceder.

### Edição de draft por voz

Dentro do card de draft, o user pode dizer:
- "Muda o tom para mais formal"
- "Remove a última frase"
- "Adiciona um cumprimento"
- "Refaz tudo"

Estas instruções aparecem como input do user no chat, e Vox responde com card atualizado.

### Seletor de conta no chat

- Header do chat mostra "Vox" + chip da conta ativa (cor + nickname)
- Tap no chip → dropdown com contas disponíveis
- Vox sugere conta por default baseado em: (a) conta que recebeu o email original, (b) contacto conhecido, (c) última conta usada

---

## 6. Interações e Microinterações

**Swipe actions na inbox (72px de altura):**
- Swipe right curto (25%): marcar lido/não-lido (cinza)
- Swipe right longo (60%): arquivar (verde `#34D399`)
- Swipe left curto (25%): abrir no Vox (violet `#6C5CE7`) — salta para chat com contexto
- Swipe left longo (60%): deletar (vermelho, com confirmação haptic heavy)

**Háptico (via Vibration API + iOS Haptic Engine):**
- Tap em botão primário: light (10ms)
- Início de gravação: medium
- Auto-silêncio detectado: selection
- Envio bem-sucedido: success notification pattern
- Erro: error notification pattern
- Swipe threshold: selection

**Animações:**
- Transições entre tabs: crossfade 200ms (não slide — tabs são independentes)
- Cards Vox a aparecer: slide-up + fade-in 250ms, stagger 80ms entre cards
- Mic listening pulse: `scale(1.0 → 1.08)` em 1.5s ease-in-out infinite
- Mic glow: `box-shadow` expande/contrai com pulse
- Card success: checkmark verde 400ms, auto-dismiss após 800ms com fade-out
- **`prefers-reduced-motion`:** crossfade 150ms, sem pulsações, sem glow animado, mantém waveform estático

**Pull-to-refresh (inbox):** threshold 80px, animação de waveform horizontal em cyan (3 ondas). Haptic light ao passar do threshold.

---

## 7. Multi-conta — Experiência Visual

**Percepção de conta ativa:**
- Barra colorida vertical de 4px na lateral esquerda de cada item da inbox (cor da conta)
- No chat header: chip com nickname + cor da conta
- No card Vox: footer mostra "via [nickname]" com dot colorido

**Seletor rápido:**
- No chat: tap no chip de conta no header
- Na inbox: tap no chevron do header
- Overlay com lista de contas (chips grandes com cor + nickname + email)
- Overlay fecha com tap fora ou swipe down

**Cores de conta:** auto-atribuídas da palette de 6, editáveis em Settings.

---

## 8. Onboarding (B+C)

**Fluxo completo:**

1. **Splash** (2s) — fundo `#0A0A0F`, logo Per4Biz centralizado 120px com glow violet animado, hero gradient subtil por trás
2. **Ecrã 1** (swipeable) — ilustração de ondas sonoras em cyan/violet, título "Fala com os teus emails", subtitulo "O Vox lê, responde e organiza — só com a tua voz"
3. **Ecrã 2** (swipeable) — mockup simplificado do chat, título "O teu agente vocal", subtitulo "Diz ao Vox o que precisas. Ele trata do resto."
4. **Google Sign-in** — botão "Ligar Gmail" violet, card glass com explicação de permissões
5. **Chat com Vox** — Vox envia primeiro card: "Olá! Sou o Vox. 🎤 Preciso de acesso ao teu microfone para começar." → Botão "Ativar microfone" inline. Depois: "Perfeito! Já tens 12 emails. Queres que eu leia os mais recentes?"

Cada passo do onboarding pós-login é um card no chat — o user aprende o UX enquanto usa.

---

## 9. Acessibilidade (WCAG AA+)

- **Contraste:** todos os pares texto/background ≥ 4.5:1 (body) e ≥ 3:1 (títulos grandes). Testado contra `#0A0A0F` e `#14141B`.
- **Touch targets:** mínimo **48×48px**. Mic button: 64px. Bottom navbar items: 56px.
- **Screen readers:** todos os elementos têm `aria-label` em PT-PT. Estados do Vox anunciados via `aria-live="polite"`. Cards do agente têm `role="article"` com `aria-label` tipo "Vox leu email de Ana Costa".
- **Focus visible:** ring violet `#6C5CE7` de 3px com offset de 2px.
- **Fontes escaláveis:** respeita `Dynamic Type` iOS e `font-size` do sistema Android (até 200%).
- **Transcrição sempre visível** durante gravação — beneficia surdos e ambientes ruidosos.
- **Auto-silêncio desactivável** em Settings > Voz (pessoas com pausas longas de fala).

---

## 10. PWA Specifics

- **Splash screen:** background `#0A0A0F`, logo centralizado 120px com glow violet, sem texto.
- **Ícone adaptativo:** SVG mascarável com safe zone de 40%. Fundo `#0A0A0F`, símbolo Vox em violet+cyan gradient (ondas sonoras estilizadas).
- **Manifest:** `display: "standalone"`, `orientation: "portrait"`, `theme_color: "#0A0A0F"`, `background_color: "#0A0A0F"`.
- **Safe-areas iOS:**
  - Chat header usa `env(safe-area-inset-top)`
  - Mic button: `bottom: calc(72px + env(safe-area-inset-bottom))` (acima da navbar)
  - Bottom navbar: `padding-bottom: env(safe-area-inset-bottom)`
- **Offline:** inbox cacheada (últimos 50 emails), chat mostra histórico, mic funciona mas indica "sem ligação — a resposta será enviada ao reconectar"
- **Install prompt:** card do Vox após 3ª sessão — "Queres instalar o Per4Biz no ecrã principal?"

---

## 11. Componentes Reutilizáveis (Design System Mini)

| Componente | Variantes | Notas |
|---|---|---|
| **Button** | primary(violet), secondary(glass), ghost, destructive · sm(36px) md(44px) lg(56px) | Radius 12px; primary tem glow violet |
| **MicButton** | idle, listening, processing, speaking, error · 64px | Centro do chat; glow muda por estado |
| **VoxCard** | email-read, transcription, draft, confirmation, error, agenda | Glass frost, radius 16px, border violet subtil |
| **UserInput** | voice(transcript mono), text(Inter) | Alinhado direita, simples |
| **EmailListItem** | unread, read, selected, swiping | Barra colorida left 4px, altura 72px |
| **AccountChip** | dot(8px), chip(com label), avatar-ring(colorido) | Cor da conta sempre consistente |
| **Chip** | filter, input, suggestion | Radius pill, altura 32px |
| **Toast** | success, error, info | Slide-up bottom, auto-dismiss 3s, glass frost |
| **Waveform** | live(reativo cyan), static(placeholder), mini(16px inline) | Canvas ou SVG animado |
| **TranscriptText** | confirmed(`#F0F0F5`), hypothesis(`#5A5A6E`), edited | JetBrains Mono, fade-in por palavra |
| **Modal** | bottom-sheet, full-screen, dialog | Glass backdrop, drag-handle |
| **Avatar** | 24, 32, 40, 64px · com ring de conta ou sem | Fallback iniciais |
| **BottomNavbar** | 4 tabs (Chat·Inbox·Agenda·Settings) | Glass frost fundo, dot violet tab activa |
| **SegmentedControl** | 2, 3, 4 opções | Usado em agenda V2 |
| **ListRow** | default, with-icon, with-toggle, destructive | Altura 56px, settings |
| **OnboardingSlide** | illustration + title + subtitle | Swipeable, dots indicator |

**Tokens globais a exportar:** `colors`, `spacing`, `radius`, `shadows`, `glows`, `motion` (durations + easings), `typography` (escalas Inter + JetBrains Mono), `glass` (blur values + opacities).

---

## 12. Spec do Agente Vox

| Propriedade | Valor |
|---|---|
| **Nome** | Vox |
| **Personalidade** | Eficiente, directo, proactivo. Fala PT-PT conciso. Não usa emojis excessivos. |
| **Voz TTS** | Feminina PT-PT (ElevenLabs, voice_id a escolher) |
| **STT** | Groq Whisper v3 (PT-PT) |
| **LLM** | Groq Llama 3.3 70B Versatile |
| **Wake-word (V2)** | "Ei Vox" |
| **Avatar** | Ícone de ondas sonoras em cyan, ring glow quando speaking |
| **Comportamento** | Sempre mostra card de acção antes de executar. Nunca envia sem confirmação. Pede esclarecimento se comando ambíguo. |

---

**Próximos passos recomendados:**
1. Implementar bottom navbar + chat layout como primeiro componente funcional
2. Prototipar o MicButton com estados (idle/listening/processing) e testar latência auto-silêncio
3. Validar paleta violet/cyan em dispositivo real OLED (contraste e glow)
4. Criar SPEC para feature "chat-first architecture" em `specs/`
