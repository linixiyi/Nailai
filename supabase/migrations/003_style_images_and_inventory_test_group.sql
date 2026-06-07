alter table nail_styles
  add column if not exists image_url text,
  add column if not exists stock_total integer not null default 0,
  add column if not exists stock_reserved integer not null default 0,
  add column if not exists source_batch text;

insert into nail_styles (
  id, name, color, finish, occasion, tags, palette, prompt, difficulty, price_level,
  image_url, stock_total, stock_reserved, source_batch
) values
  (
    'cherry-mirror-1', '樱桃镜面 细闪', '红色', '镜面',
    array['新年','约会'],
    array['复古','气色','亮面','细闪','春日'],
    array['#b8152f','#ffced8','#7a0f20'],
    'cherry mirror manicure with subtle shimmer, realistic salon quality',
    'medium', '¥¥¥',
    '/style-images/group-20260514-212714/1.png', 12, 1, 'group-20260514-212714'
  ),
  (
    'cherry-mirror-2', '樱桃镜面 法式边', '红色', '镜面',
    array['新年','约会'],
    array['复古','气色','亮面','法式边','夏日'],
    array['#b8152f','#ffced8','#7a0f20'],
    'cherry mirror french edge manicure, realistic salon quality',
    'medium', '¥¥¥',
    '/style-images/group-20260514-212714/2.png', 12, 2, 'group-20260514-212714'
  ),
  (
    'cherry-mirror-3', '樱桃镜面 贝壳片', '红色', '镜面',
    array['新年','约会'],
    array['复古','气色','亮面','贝壳片','秋冬'],
    array['#b8152f','#ffced8','#7a0f20'],
    'cherry mirror shell accents manicure, realistic salon quality',
    'medium', '¥¥¥',
    '/style-images/group-20260514-212714/3.png', 12, 3, 'group-20260514-212714'
  ),
  (
    'cherry-mirror-4', '樱桃镜面 水晶点缀', '红色', '镜面',
    array['新年','约会'],
    array['复古','气色','亮面','水晶点缀','节日'],
    array['#b8152f','#ffced8','#7a0f20'],
    'cherry mirror crystal accents manicure, realistic salon quality',
    'medium', '¥¥¥',
    '/style-images/group-20260514-212714/4.png', 12, 4, 'group-20260514-212714'
  ),
  (
    'cherry-mirror-5', '樱桃镜面 微晕染', '红色', '镜面',
    array['新年','约会'],
    array['复古','气色','亮面','微晕染','日常'],
    array['#b8152f','#ffced8','#7a0f20'],
    'cherry mirror soft gradient manicure, realistic salon quality',
    'medium', '¥¥¥',
    '/style-images/group-20260514-212714/5.png', 12, 4, 'group-20260514-212714'
  )
on conflict (id) do update set
  name = excluded.name,
  image_url = excluded.image_url,
  stock_total = excluded.stock_total,
  stock_reserved = excluded.stock_reserved,
  source_batch = excluded.source_batch;
