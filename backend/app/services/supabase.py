"""Backend Supabase client using the service-role key.
Bypasses RLS — only use for operations already authorized by verify_jwt."""

from functools import lru_cache

from supabase import Client, create_client

from app.config import settings


@lru_cache
def get_supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
