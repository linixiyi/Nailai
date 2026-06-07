-- Match imported inventory display names to curated manicure tags.
update nail_styles set name = '酒红蝴蝶结法式' where id = 'library-20260514-001';
update nail_styles set name = '奶牛纹豆沙法式' where id = 'library-20260514-002';
update nail_styles set name = '玫瑰金镜面尖甲' where id = 'library-20260514-003';
update nail_styles set name = '莫兰迪灰蓝亮片' where id = 'library-20260514-004';
update nail_styles set name = '巴洛克爱心堆钻' where id = 'library-20260514-005';
update nail_styles set name = '暗黑星芒辣妹甲' where id = 'library-20260514-006';
update nail_styles set name = '白月光渐变流苏' where id = 'library-20260514-007';
update nail_styles set name = '抹茶奶茶跳色' where id = 'library-20260514-008';
update nail_styles set name = '彩色小花格纹' where id = 'library-20260514-009';
update nail_styles set name = '裸银豹纹辣妹' where id = 'library-20260514-010';
update nail_styles set name = '彩色波点腮红' where id = 'library-20260514-011';
update nail_styles set name = '黑银爆闪法式' where id = 'library-20260514-012';
update nail_styles set name = '豹纹重工堆钻' where id = 'library-20260514-013';
update nail_styles set name = '银灰镜面短甲' where id = 'library-20260514-014';
update nail_styles set name = '香槟金宴会堆钻' where id = 'library-20260514-015';
update nail_styles set name = '白月光猫眼杏仁' where id = 'library-20260514-016';
update nail_styles set name = '黑白几何法式' where id = 'library-20260514-017';
update nail_styles set name = '裸粉腮红微雕' where id = 'library-20260514-018';
update nail_styles set name = '奶白老钱通勤' where id = 'library-20260514-019';
update nail_styles set name = '粉色立体雕花' where id = 'library-20260514-020';
update nail_styles set name = '裸粉星芒 Y2K' where id = 'library-20260514-021';
update nail_styles set name = '摩卡重工钻饰' where id = 'library-20260514-022';
update nail_styles set name = '珍珠方钻新娘' where id = 'library-20260514-023';
update nail_styles set name = '静谧蓝金箔跳色' where id = 'library-20260514-024';
update nail_styles set name = '薄荷鸡蛋花度假' where id = 'library-20260514-025';
update nail_styles set name = '豆沙红反向法式' where id = 'library-20260514-026';
update nail_styles set name = '极光粉果冻短甲' where id = 'library-20260514-027';
update nail_styles set name = '裸粉纯欲杏仁' where id = 'library-20260514-028';
update nail_styles set name = '白色镜面极简' where id = 'library-20260514-029';
update nail_styles set name = '芥末绿燕麦跳色' where id = 'library-20260514-030';

-- Corrections after name/tag consistency audit.
update nail_styles set name = '玫瑰金魔镜尖甲' where id = 'library-20260514-003';
update nail_styles set name = '银灰魔镜短甲' where id = 'library-20260514-014';
update nail_styles set taxonomy = jsonb_set(taxonomy, '{occasions}', '["婚礼", "新娘", "宴会"]'::jsonb, true) where id = 'library-20260514-023';
update nail_styles set taxonomy = jsonb_set(taxonomy, '{shapes}', '["椭圆型"]'::jsonb, true) where id = 'library-20260514-025';
update nail_styles set taxonomy = jsonb_set(taxonomy, '{lengths}', '["长款"]'::jsonb, true) where id = 'library-20260514-025';
update nail_styles set taxonomy = jsonb_set(taxonomy, '{techniques}', '["纯色", "冰透"]'::jsonb, true) where id = 'library-20260514-028';
update nail_styles set taxonomy = jsonb_set(taxonomy, '{techniques}', '["纯色", "魔镜", "镜面"]'::jsonb, true) where id = 'library-20260514-029';

-- Technique ordering corrections for display finish.
update nail_styles set taxonomy = jsonb_set(taxonomy, '{techniques}', '["魔镜", "猫眼", "极光"]'::jsonb, true), finish = '魔镜' where id = 'library-20260514-003';
update nail_styles set taxonomy = jsonb_set(taxonomy, '{techniques}', '["魔镜", "纯色", "跳色", "几何", "猫眼", "极光"]'::jsonb, true), finish = '魔镜' where id = 'library-20260514-014';
update nail_styles set taxonomy = jsonb_set(taxonomy, '{techniques}', '["纯色", "镜面", "魔镜"]'::jsonb, true), finish = '纯色' where id = 'library-20260514-029';
