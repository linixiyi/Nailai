# NailAI 美甲款式分类数据说明

## 数据来源

- `nail_tags(1).csv`：每个库存款式的人工标签，字段为 `filename,tags`。
- `美甲六维分类(1).zip`：同一批款式按六个维度分类后的目录结构。
- 当前项目使用的生成脚本：`scripts/generate_nail_taxonomy_from_dir.py`。

当前已覆盖 `美甲01.png` 到 `美甲30.png`，对应库存款式 ID：

```text
美甲01.png -> library-20260514-001
美甲30.png -> library-20260514-030
```

## 六维分类结构

每个款式都会被整理成 `taxonomy`：

```json
{
  "colors": ["粉色系", "红色系"],
  "techniques": ["手绘", "法式", "钻饰"],
  "shapes": ["方圆型"],
  "styles": ["复古", "老钱"],
  "occasions": ["约会", "节日"],
  "lengths": ["中长款"]
}
```

维度含义：

- `colors`：色系，例如粉色系、红色系、金属色系。
- `techniques`：款式工艺，例如法式、猫眼、渐变、钻饰、手绘。
- `shapes`：甲型，例如方圆型、尖型、杏仁型、梯型。
- `styles`：风格，例如日系、复古、轻奢、Y2K。
- `occasions`：适用场景，例如日常、通勤、婚礼、派对、节日。
- `lengths`：甲长分类，例如短款、中长款、长款。

## 代码落点

- 前端分类数据：`web/src/lib/nailTaxonomy.ts`
- 前端库存融合：`web/src/lib/styles.ts`
- 后端分类数据：`ai-service/app/services/nail_taxonomy.py`
- 后端库存融合：`ai-service/app/services/style_catalog.py`
- 数据库迁移：`supabase/migrations/005_style_taxonomy_20260526.sql`

## 生成规则

- 以六维目录为唯一分类源，生成前端和后端的 `taxonomy` 映射。
- `library-20260514-006` 和 `library-20260514-032` 目前没有对应六维分类，已作为公开目录的隐藏项处理。
- 重新整理目录后，优先运行 `python3 scripts/generate_nail_taxonomy_from_dir.py "<六维分类目录>"` 再检查前后端输出。

## 推荐链路怎么使用

1. 前端和后端都会把 `taxonomy` 合并进 `NailStyle`。
2. `searchStyles()` / `search_styles()` 会同时检索款式名、色系、工艺、甲型、风格、场景、甲长和人工标签。
3. Chat 推荐候选款式会把 `taxonomy` 一起传给聊天模型，模型可以按用户描述选择库存款式。
4. 已过滤导入噪声标签，例如 `实拍`、`测试批次`、`图库导入`，避免影响推荐。

## 后续扩展建议

- 新增库存款式时，先补 CSV 标签，再按六维目录归类。
- Chat 推荐可以继续加权：场景和甲长权重最高，色系和风格次之，工艺用于细化排序。
- 如果接 Supabase 生产库，先执行 `005_style_taxonomy_20260526.sql`，并确认 `taxonomy` JSONB 字段和 GIN 索引存在。
