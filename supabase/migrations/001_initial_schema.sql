create extension if not exists "uuid-ossp";
create extension if not exists vector;

create table if not exists nail_styles (
  id text primary key,
  name text not null,
  color text not null,
  finish text not null,
  occasion text[] not null default '{}',
  tags text[] not null default '{}',
  palette text[] not null default '{}',
  prompt text not null,
  difficulty text not null check (difficulty in ('easy', 'medium', 'hard')),
  price_level text not null,
  embedding vector(512),
  created_at timestamptz not null default now()
);

create table if not exists try_on_jobs (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid,
  style_id text references nail_styles(id),
  source_image_url text,
  result_image_url text,
  mask_image_url text,
  status text not null default 'queued' check (status in ('queued', 'running', 'succeeded', 'failed')),
  channel text,
  hand_confidence numeric(4, 3),
  quality_score numeric(4, 3),
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists chat_sessions (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid,
  title text,
  created_at timestamptz not null default now()
);

create table if not exists chat_messages (
  id uuid primary key default uuid_generate_v4(),
  session_id uuid references chat_sessions(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  recommended_style_ids text[] not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists shops (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  address text,
  longitude numeric(10, 7),
  latitude numeric(10, 7),
  rating numeric(2, 1) not null default 4.8,
  contact jsonb not null default '{}',
  facilities jsonb not null default '{}',
  active_score numeric(4, 3) not null default 0.7,
  created_at timestamptz not null default now()
);

create table if not exists shop_styles (
  shop_id uuid references shops(id) on delete cascade,
  style_id text references nail_styles(id) on delete cascade,
  primary key (shop_id, style_id)
);

create index if not exists idx_nail_styles_tags on nail_styles using gin(tags);
create index if not exists idx_nail_styles_occasion on nail_styles using gin(occasion);
create index if not exists idx_try_on_jobs_user_created on try_on_jobs(user_id, created_at desc);
create index if not exists idx_chat_messages_session_created on chat_messages(session_id, created_at);
