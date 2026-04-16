# frontend/ — Per4Biz PWA

Next.js 16 App Router + PWA (next-pwa/Serwist) + TypeScript strict + Tailwind v4 + shadcn/ui.

## Estado

**Vazio.** Scaffold a criar no **Sprint 0 — Dia 2** (ver [../04-sprints/SPRINT-PLAN.md §9](../04-sprints/SPRINT-PLAN.md)).

## Scaffold esperado (Sprint 0)

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── (auth)/
│   ├── (app)/
│   │   ├── inbox/
│   │   ├── voice/
│   │   └── settings/
│   └── api/                        ← BFF Route Handlers (proxy para FastAPI)
├── components/
│   ├── ui/                         ← shadcn primitives
│   ├── voice/                      ← VoiceButton, Waveform, TranscriptText
│   ├── email/                      ← EmailListItem, EmailDetail
│   └── account/                    ← AccountBadge, AccountSelector
├── lib/
│   ├── supabase/                   ← clients (browser + server)
│   ├── api/                        ← cliente TypeScript gerado do OpenAPI
│   └── utils/
├── public/
│   ├── manifest.json
│   ├── icons/                      ← 192, 512, maskable-512
│   └── sw.js                       ← gerado pelo next-pwa
├── tests/
│   ├── unit/                       ← vitest
│   └── e2e/                        ← playwright
├── next.config.mjs
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── vitest.config.ts
```

## Comandos (quando scaffold existir)

```bash
npm run dev        # porta 3000
npm test           # vitest watch
npm run test:run   # vitest single run
npm run test:e2e   # playwright
npm run lint
npm run typecheck
npm run build
```

## Referências

- Design tokens e componentes: [../03-ui-ux/DESIGN-SPEC.md](../03-ui-ux/DESIGN-SPEC.md)
- Requisitos funcionais: [../01-prd/PRD-MASTER.md §7](../01-prd/PRD-MASTER.md)
- PWA config (manifest, SW strategy): [../02-ultraplan/ULTRAPLAN-tecnico.md §8](../02-ultraplan/ULTRAPLAN-tecnico.md)
