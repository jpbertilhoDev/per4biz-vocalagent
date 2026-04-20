"""
Factory do Supabase admin client (service_role — V1 sem Auth/RLS).

Em V1 single-tenant o backend detém a `SUPABASE_SERVICE_ROLE_KEY` e confia no
gating `ALLOWED_USER_EMAIL` (SPEC §4.1 passo 6, CLAUDE.md §3 regra 8). Este
módulo centraliza a criação do cliente para permitir mock em testes via
`mocker.patch("app.services.supabase_client.get_supabase_admin")`.
"""
from __future__ import annotations

from supabase import Client, create_client

from app.config import get_settings


def get_supabase_admin() -> Client:
    """Constrói e devolve um `supabase.Client` com a service_role key.

    Returns:
        Cliente Supabase autenticado como service_role. A construção é barata
        (apenas um dict de headers); chamá-la repetidamente é aceitável em V1.
    """
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
