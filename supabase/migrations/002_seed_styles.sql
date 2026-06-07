insert into nail_styles (id, name, color, finish, occasion, tags, palette, prompt, difficulty, price_level)
values
  ('milk-tea-glaze-1', '奶茶琉璃 细闪', '奶茶', '透亮', array['通勤','约会'], array['显白','温柔','短甲友好','细闪','春日'], array['#d7b89b','#f3e3d2','#b98064'], 'milk tea glossy manicure with subtle shimmer', 'easy', '¥¥'),
  ('rose-cat-eye-1', '玫瑰猫眼 细闪', '玫瑰', '猫眼', array['约会','派对'], array['氛围感','闪','中长甲','细闪','春日'], array['#9f4155','#e7a3b1','#602735'], 'rose cat eye manicure, glossy salon quality', 'medium', '¥¥¥'),
  ('french-pearl-1', '珍珠法式 细闪', '白色', '珍珠', array['婚礼','通勤'], array['优雅','低调','法式','细闪','春日'], array['#fffaf0','#d8c7ad','#f6e8d8'], 'pearl french manicure, elegant wedding style', 'medium', '¥¥¥')
on conflict (id) do nothing;
