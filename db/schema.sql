-- Run in the Supabase SQL editor. Requires the auth schema (built into every Supabase project).

create table profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  full_name text,
  created_at timestamptz not null default now()
);

create table resumes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  storage_path text not null,
  extracted_text text,
  created_at timestamptz not null default now()
);

create table applications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  resume_id uuid references resumes (id) on delete set null,
  job_title text,
  company text,
  job_posting_text text,
  status text not null default 'pending'
    check (status in ('pending', 'running', 'awaiting_approval', 'completed', 'failed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table agent_runs (
  id uuid primary key default gen_random_uuid(),
  application_id uuid not null references applications (id) on delete cascade,
  agent_name text not null,
  attempt int not null default 1,
  input_summary jsonb,
  output jsonb,
  critic_feedback text,
  quality_score numeric,
  started_at timestamptz,
  finished_at timestamptz,
  status text
);

create table artifacts (
  id uuid primary key default gen_random_uuid(),
  application_id uuid not null references applications (id) on delete cascade,
  kind text not null
    check (kind in ('job_analysis', 'match_report', 'cover_letter', 'interview_prep')),
  content jsonb,
  version int not null default 1,
  approved boolean not null default false,
  created_at timestamptz not null default now()
);

-- Row Level Security: every table restricts rows to their owning user.
alter table profiles enable row level security;
alter table resumes enable row level security;
alter table applications enable row level security;
alter table agent_runs enable row level security;
alter table artifacts enable row level security;

create policy "profiles: owner access" on profiles
  for all using (id = auth.uid()) with check (id = auth.uid());

create policy "resumes: owner access" on resumes
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "applications: owner access" on applications
  for all using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy "agent_runs: owner access via application" on agent_runs
  for all using (
    exists (
      select 1 from applications
      where applications.id = agent_runs.application_id
        and applications.user_id = auth.uid()
    )
  );

create policy "artifacts: owner access via application" on artifacts
  for all using (
    exists (
      select 1 from applications
      where applications.id = artifacts.application_id
        and applications.user_id = auth.uid()
    )
  );

-- Storage bucket for uploaded resumes (private; access via signed URLs / service role only).
insert into storage.buckets (id, name, public)
values ('resumes', 'resumes', false)
on conflict (id) do nothing;

create policy "resumes bucket: owner access" on storage.objects
  for all using (
    bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text
  ) with check (
    bucket_id = 'resumes' and (storage.foldername(name))[1] = auth.uid()::text
  );
