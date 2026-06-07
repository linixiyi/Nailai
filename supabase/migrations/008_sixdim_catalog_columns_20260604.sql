alter table nail_styles
  add column if not exists nail_length text,
  add column if not exists taxonomy jsonb not null default '{}'::jsonb,
  add column if not exists source_batch text;

create index if not exists idx_nail_styles_taxonomy on nail_styles using gin(taxonomy);
