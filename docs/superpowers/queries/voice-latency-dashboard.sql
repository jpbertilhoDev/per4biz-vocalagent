-- E10 Voice Latency Dashboard — rolling 7 days, p50/p95/p99 per phase.
-- Corrida manual em Supabase SQL Editor. Ver spec §4.
-- Tabela origem: public.voice_latency_events (E10 migration 0005).

select
  phase,
  count(*)                                                               as sessions,
  round(avg(ms)::numeric, 0)                                             as avg_ms,
  percentile_cont(0.50) within group (order by ms)::int                  as p50,
  percentile_cont(0.95) within group (order by ms)::int                  as p95,
  percentile_cont(0.99) within group (order by ms)::int                  as p99,
  sum(case when status='error' then 1 else 0 end)                        as errors,
  sum(case when status='timeout' then 1 else 0 end)                      as timeouts
from public.voice_latency_events
where created_at > now() - interval '7 days'
group by phase
order by p95 desc;
