-- Add active status column to nail_styles
alter table nail_styles add column if not exists is_active boolean not null default true;

-- Create style analytics table
create table if not exists style_analytics (
  style_id text primary key references nail_styles(id) on delete cascade,
  views integer not null default 0,
  try_ons integer not null default 0,
  interests integer not null default 0,
  bookings integer not null default 0,
  updated_at timestamptz not null default now()
);
