create table if not exists bounties (
  id text primary key,
  title text not null,
  budget text not null,
  status text not null default '待接单',
  image text not null,
  participants integer not null default 0,
  deadline text not null,
  description text,
  selected_variant_id text,
  answers jsonb,
  shop_id uuid references shops(id) on delete set null,
  created_at timestamptz not null default now()
);

-- Seed some default bounties into bounties table
insert into bounties (id, title, budget, status, image, participants, deadline, description)
values 
  ('bounty-aurora', '复刻极光蝴蝶款', '¥150-250', '竞价中', '/modao-assets/modao-05.jpg', 8, '2天后截止', '希望保留紫蓝偏光和蝴蝶翅膀质感，接受轻微改色。'),
  ('bounty-pearl', '珍珠花瓣通勤改良', '¥120-180', '待确认', '/modao-assets/modao-20.jpg', 5, '明晚截止', '想要更低调一点，适合上班和周末约会。'),
  ('bounty-rainbow', '彩虹琉璃短甲版', '¥200-300', '竞价中', '/modao-assets/modao-22.jpg', 12, '3天后截止', '短甲也要有玻璃感，颜色可以按肤色微调。')
on conflict (id) do nothing;
