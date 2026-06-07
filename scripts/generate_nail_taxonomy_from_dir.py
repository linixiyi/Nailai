from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_TAXONOMY_PATH = ROOT / "web/src/lib/nailTaxonomy.ts"
WEB_IMPORTED_STYLES_PATH = ROOT / "web/src/lib/importedStyles.ts"
API_TAXONOMY_PATH = ROOT / "ai-service/app/services/nail_taxonomy.py"
API_TAXONOMY_JSON_PATH = ROOT / "ai-service/app/services/nail_taxonomy_data.json"
LIBRARY_IMAGE_DIR = ROOT / "web/public/style-images/library-20260514"

DIMENSION_CONFIG = {
    "1-色系": ("colors", "色系"),
    "2-款式工艺": ("techniques", "款式工艺"),
    "3-甲型": ("shapes", "甲型"),
    "4-风格": ("styles", "风格"),
    "5-适用场景": ("occasions", "适用场景"),
    "6-甲型长短": ("lengths", "甲型长短"),
}

DIMENSION_ORDER = ["colors", "techniques", "shapes", "styles", "occasions", "lengths"]
NOISE_TAGS = ["长甲", "短甲", "实拍", "测试批次", "图库导入", "镜面", "果冻", "猫眼", "渐变", "法式"]
LENGTH_MAP = {
    "短款": "natural",
    "短甲": "natural",
    "中长款": "medium",
    "中长": "medium",
    "长款": "long",
    "长甲": "long",
}

LABEL_NORMALIZATION = {
    "colors": {
        "彩色": ["彩色"],
        "多色": ["多色"],
        "粉色系": ["粉色系"],
        "红色系": ["红色系"],
        "蓝": ["蓝色系"],
        "绿": ["绿色系"],
        "冷色": ["冷色系"],
        "裸色": ["裸色系"],
        "大地色": ["大地色系"],
        "金属": ["金属色系"],
        "金银色": ["金银色"],
        "黑": ["黑色系"],
        "白": ["白色系"],
        "灰": ["灰色系"],
    },
    "techniques": {
        "亮片": ["亮片"],
        "闪粉": ["闪粉"],
        "爆闪": ["爆闪"],
        "动物纹": ["动物纹"],
        "手绘": ["手绘"],
        "花卉": ["花卉"],
        "立体花": ["立体花"],
        "法式及变体": ["法式", "法式变体"],
        "渐变": ["渐变"],
        "腮红": ["腮红"],
        "冰透": ["冰透"],
        "猫眼": ["猫眼"],
        "魔镜": ["魔镜"],
        "极光": ["极光"],
        "纯色": ["纯色"],
        "跳色": ["跳色"],
        "几何": ["几何"],
        "钻饰": ["钻饰"],
        "宝石": ["宝石"],
        "珍珠": ["珍珠"],
    },
    "shapes": {
        "尖型": ["尖型"],
        "方圆型": ["方圆型"],
        "杏仁型": ["杏仁型"],
        "梯型": ["梯型"],
        "椭圆型": ["椭圆型"],
    },
    "styles": {
        "仙气": ["仙气"],
        "温柔": ["温柔"],
        "梦幻": ["梦幻"],
        "复古": ["复古"],
        "老钱": ["老钱"],
        "莫兰迪": ["莫兰迪"],
        "奢华": ["奢华"],
        "巴洛克": ["巴洛克"],
        "千金": ["千金"],
        "日系": ["日系"],
        "清新": ["清新"],
        "可爱": ["可爱"],
        "暗黑": ["暗黑"],
        "朋克": ["朋克"],
        "酷感": ["酷感"],
        "极简": ["极简"],
        "冷淡": ["冷淡"],
        "INS": ["INS"],
        "欧美": ["欧美"],
        "辣妹": ["辣妹"],
        "Y2K": ["Y2K"],
        "高级感": ["高级感"],
        "轻奢": ["轻奢"],
        "气质": ["气质"],
    },
    "occasions": {
        "婚礼": ["婚礼"],
        "新娘": ["新娘"],
        "宴会": ["宴会"],
        "日常": ["日常"],
        "通勤": ["通勤"],
        "百搭": ["百搭"],
        "春夏": ["春夏"],
        "度假": ["度假"],
        "清凉": ["清凉"],
        "派对": ["派对"],
        "蹦迪": ["蹦迪"],
        "晚宴": ["晚宴"],
        "秋冬": ["秋冬"],
        "约会": ["约会"],
        "节日(新年": ["节日", "新年"],
        "圣诞)": ["圣诞"],
    },
    "lengths": {
        "中长款": ["中长款"],
        "短款": ["短款"],
        "长款": ["长款"],
    },
}

PNG_NAME_RE = re.compile(r"美甲(\d+)\.png$")
DISPLAY_NAME_RE = re.compile(r'"([^"]+)": "([^"]+)"')

SOURCE_DISPLAY_NAMES = {
    1: "酒红蝴蝶结法式",
    2: "奶牛纹豆沙法式",
    3: "玫瑰金魔镜尖甲",
    4: "莫兰迪灰蓝亮片",
    5: "巴洛克爱心堆钻",
    6: "暗黑星芒辣妹甲",
    7: "白月光渐变流苏",
    8: "抹茶奶茶跳色",
    9: "彩色小花格纹",
    10: "裸银豹纹辣妹",
    11: "彩色波点腮红",
    12: "黑银爆闪法式",
    13: "豹纹重工堆钻",
    14: "银灰魔镜短甲",
    15: "香槟金宴会堆钻",
    16: "白月光猫眼杏仁",
    17: "黑白几何法式",
    18: "裸粉腮红微雕",
    19: "奶白老钱通勤",
    20: "粉色立体雕花",
    21: "裸粉星芒 Y2K",
    22: "摩卡重工钻饰",
    23: "珍珠方钻新娘",
    24: "静谧蓝金箔跳色",
    25: "薄荷鸡蛋花度假",
    26: "豆沙红反向法式",
    27: "极光粉果冻短甲",
    28: "裸粉纯欲杏仁",
    29: "白色镜面极简",
    30: "芥末绿燕麦跳色",
}

DEFAULT_PALETTES = [
    ["#7a1020", "#f2ccd5", "#ffffff"],
    ["#111111", "#f3d5dc", "#ffffff"],
    ["#b8735f", "#f7d6cf", "#5b2731"],
    ["#6f8797", "#f4cbd7", "#ffffff"],
    ["#f5c4d6", "#b87a8e", "#ffffff"],
    ["#1b171c", "#d7bcae", "#ffffff"],
    ["#f6f6f6", "#d7c2a7", "#b4a18e"],
    ["#8a9a64", "#ddc8aa", "#fff6e8"],
    ["#d34257", "#f2c840", "#3f79ba"],
    ["#c6b5aa", "#a9a9a9", "#2c2424"],
]

STYLE_OVERRIDES: dict[str, dict] = {
    "library-20260514-004": {
        "color": "蓝色系 / 灰色系",
        "finish": "亮片",
        "nail_length": "natural",
        "taxonomy": {
            "colors": ["蓝色系", "灰色系"],
            "techniques": ["亮片"],
            "shapes": ["方圆型"],
            "styles": ["莫兰迪"],
            "occasions": ["日常"],
            "lengths": ["短款"],
        },
    },
    "library-20260514-008": {
        "color": "蓝色系 / 白色系",
        "finish": "渐变",
        "nail_length": "long",
        "taxonomy": {
            "colors": ["蓝色系", "白色系", "绿色系", "冷色系"],
            "techniques": ["渐变", "腮红", "冰透", "手绘", "花卉"],
            "shapes": ["椭圆型"],
            "styles": ["仙气", "温柔", "梦幻"],
            "occasions": ["春夏", "度假", "清凉"],
            "lengths": ["长款"],
        },
    },
    "library-20260514-025": {
        "color": "蓝色系 / 裸色系",
        "finish": "法式",
        "nail_length": "natural",
        "taxonomy": {
            "colors": ["蓝色系", "裸色系"],
            "techniques": ["法式", "跳色"],
            "shapes": ["方圆型"],
            "styles": ["清新", "极简"],
            "occasions": ["日常", "通勤"],
            "lengths": ["短款"],
        },
    },
    "library-20260514-026": {
        "color": "蓝色系 / 绿色系",
        "finish": "手绘",
        "nail_length": "long",
        "taxonomy": {
            "colors": ["蓝色系", "绿色系", "白色系"],
            "techniques": ["手绘", "花卉", "立体花"],
            "shapes": ["椭圆型"],
            "styles": ["仙气", "温柔", "梦幻"],
            "occasions": ["春夏", "度假", "清凉"],
            "lengths": ["长款"],
        },
    },
    "library-20260514-030": {
        "color": "裸色系 / 大地色系",
        "finish": "纯色",
        "nail_length": "natural",
        "taxonomy": {
            "colors": ["裸色系", "大地色系"],
            "techniques": ["纯色"],
            "shapes": ["方圆型"],
            "styles": ["复古", "老钱", "极简"],
            "occasions": ["日常", "通勤", "百搭"],
            "lengths": ["短款"],
        },
    },
}


def apply_style_overrides(record: dict) -> dict:
    override = STYLE_OVERRIDES.get(record["id"])
    if not override:
        return record

    updated = dict(record)
    taxonomy = dict(updated.get("taxonomy", {}))
    for key, value in override.get("taxonomy", {}).items():
        taxonomy[key] = value
    updated["taxonomy"] = taxonomy
    for field in ["color", "finish", "nail_length"]:
        if field in override:
            updated[field] = override[field]
    updated["tags"] = compact_tags_from_taxonomy(taxonomy)
    updated["prompt"] = (
        f"{updated['name']} manicure. Taxonomy: {', '.join(updated['tags'])}. "
        f"Required nail shape: {', '.join(taxonomy.get('shapes', [])) or 'follow reference'}. "
        f"Required nail length: {', '.join(taxonomy.get('lengths', [])) or 'follow reference'}"
    )
    return updated


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def read_existing_display_names() -> dict[str, str]:
    text = WEB_TAXONOMY_PATH.read_text(encoding="utf-8")
    names: dict[str, str] = {}
    for key, value in DISPLAY_NAME_RE.findall(text):
        names[key] = value
    return names


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_image_mapping(source_root: Path) -> tuple[dict[int, str], list[str]]:
    source_by_index: dict[int, Path] = {}
    for path in source_root.rglob("*.png"):
        match = PNG_NAME_RE.fullmatch(path.name)
        if not match:
            continue
        index = int(match.group(1))
        source_by_index.setdefault(index, path)

    source_hash_to_index = {sha256(path): index for index, path in source_by_index.items()}
    mapping: dict[int, str] = {}
    unmatched_library_ids: list[str] = []

    for library_path in sorted(LIBRARY_IMAGE_DIR.glob("library-20260514-*.png")):
        image_hash = sha256(library_path)
        source_index = source_hash_to_index.get(image_hash)
        if source_index is None:
            unmatched_library_ids.append(library_path.stem.replace("library-20260514-", ""))
            continue
        mapping[source_index] = library_path.stem.replace("library-20260514-", "")

    return mapping, unmatched_library_ids


def normalize_label(dimension: str, label: str) -> list[str]:
    normalized = LABEL_NORMALIZATION.get(dimension, {}).get(label)
    if normalized:
        return normalized
    if dimension == "colors" and label.endswith("系"):
        return [label]
    return [label]


def collect_profiles(source_root: Path) -> dict[int, dict]:
    profiles: dict[int, dict[str, object]] = {}

    for path in source_root.rglob("*.png"):
        match = PNG_NAME_RE.fullmatch(path.name)
        if not match:
            continue

        source_index = int(match.group(1))
        relative_parts = path.relative_to(source_root).parts
        dimension_dir = relative_parts[0]
        if dimension_dir not in DIMENSION_CONFIG:
            continue
        dimension_key, _ = DIMENSION_CONFIG[dimension_dir]
        labels = relative_parts[1:-1]

        profile = profiles.setdefault(
            source_index,
            {
                "styleId": f"source-{source_index:03d}",
                "sourceFilename": path.name,
                "taxonomy": {key: [] for key in DIMENSION_ORDER},
            },
        )
        taxonomy = profile["taxonomy"]
        assert isinstance(taxonomy, dict)
        existing = list(taxonomy[dimension_key])
        for label in labels:
            existing.extend(normalize_label(dimension_key, label))
        taxonomy[dimension_key] = dedupe(existing)

    for source_index, profile in profiles.items():
        taxonomy = profile["taxonomy"]
        assert isinstance(taxonomy, dict)
        raw_tags: list[str] = []
        for key in DIMENSION_ORDER:
            raw_tags.extend(taxonomy[key])
        raw_tags = dedupe(raw_tags)
        profile["rawTags"] = raw_tags
        profile["searchText"] = " ".join(raw_tags)

    return profiles


def source_display_name(source_index: int, existing_names: dict[str, str] | None = None) -> str:
    if source_index in SOURCE_DISPLAY_NAMES:
        return SOURCE_DISPLAY_NAMES[source_index]
    if existing_names:
        return existing_names.get(f"library-20260514-{source_index:03d}", f"美甲{source_index:02d}")
    return f"美甲{source_index:02d}"


def nail_length_from_taxonomy(taxonomy: dict[str, list[str]]) -> str:
    for value in taxonomy.get("lengths", []):
        if value in LENGTH_MAP:
            return LENGTH_MAP[value]
    return "natural"


def occasion_from_taxonomy(taxonomy: dict[str, list[str]]) -> list[str]:
    occasions = taxonomy.get("occasions", [])
    return occasions if occasions else ["日常"]


def compact_tags_from_taxonomy(taxonomy: dict[str, list[str]]) -> list[str]:
    tags: list[str] = []
    for key in DIMENSION_ORDER:
        values = taxonomy.get(key, [])
        if values:
            tags.append(values[0])
    return dedupe(tags)


def canonical_record_for_source(
    source_index: int,
    library_suffix: str,
    profile: dict,
    existing_names: dict[str, str] | None = None,
) -> dict:
    taxonomy = profile["taxonomy"]
    assert isinstance(taxonomy, dict)
    raw_tags = profile.get("rawTags", [])
    assert isinstance(raw_tags, list)
    name = source_display_name(source_index, existing_names)
    colors = taxonomy.get("colors", [])
    techniques = taxonomy.get("techniques", [])
    prompt_parts = [
        f"{name} manicure",
        "six-dimensional taxonomy constrained nail style",
        f"taxonomy tags: {', '.join(raw_tags)}",
    ]
    if taxonomy.get("shapes"):
        prompt_parts.append(f"required nail shape: {', '.join(taxonomy['shapes'])}")
    if taxonomy.get("lengths"):
        prompt_parts.append(f"required nail length: {', '.join(taxonomy['lengths'])}")
    return apply_style_overrides({
        "id": f"library-20260514-{library_suffix}",
        "name": name,
        "color": " / ".join(colors[:2]) if colors else "综合色系",
        "finish": techniques[0] if techniques else "亮面",
        "occasion": occasion_from_taxonomy(taxonomy),
        "tags": compact_tags_from_taxonomy(taxonomy),
        "palette": DEFAULT_PALETTES[(source_index - 1) % len(DEFAULT_PALETTES)],
        "prompt": ". ".join(prompt_parts),
        "difficulty": "hard" if len(raw_tags) >= 18 else "medium",
        "price_level": "¥¥¥" if len(raw_tags) >= 18 else "¥¥",
        "image_url": f"/style-images/library-20260514/library-20260514-{library_suffix}.png",
        "nail_length": nail_length_from_taxonomy(taxonomy),
        "taxonomy": taxonomy,
        "stock_total": 15,
        "stock_reserved": (source_index - 1) % 4,
    })


def build_canonical_records(
    existing_names: dict[str, str],
    profiles: dict[int, dict],
    source_to_library: dict[int, str],
) -> list[dict]:
    return [
        canonical_record_for_source(source_index, source_to_library[source_index], profiles[source_index], existing_names)
        for source_index in sorted(profiles)
        if source_index in source_to_library
    ]


def build_imported_styles_file(records: list[dict]) -> str:
    records_json = json.dumps(records, ensure_ascii=False, indent=2)
    return f"""// Generated from nail six-dimensional taxonomy directory.\n// Keep this file deterministic: update source taxonomy, then regenerate.\nimport type {{ NailStyle }} from "./types";\n\nexport const importedStyles: NailStyle[] = {records_json};\n"""


def build_ts_file(
    existing_names: dict[str, str],
    profiles: dict[int, dict],
    source_to_library: dict[int, str],
) -> str:
    style_display_names: dict[str, str] = {}
    nail_tag_profiles: dict[str, dict] = {}

    for source_index in sorted(profiles):
        profile = profiles[source_index]
        display_name = source_display_name(source_index, existing_names)
        library_suffix = source_to_library.get(source_index)
        if library_suffix is not None:
            library_id = f"library-20260514-{library_suffix}"
            style_display_names[library_id] = display_name
            nail_tag_profiles[library_id] = {**profile, "styleId": library_id}

        seed_id = f"seed-{source_index:03d}"
        style_display_names[seed_id] = display_name
        nail_tag_profiles[seed_id] = {**profile, "styleId": seed_id}

    dimensions_json = json.dumps(
        {key: label for key, label in (DIMENSION_CONFIG[d] for d in DIMENSION_CONFIG)},
        ensure_ascii=False,
        indent=2,
    )
    names_json = json.dumps(style_display_names, ensure_ascii=False, indent=2)
    profiles_json = json.dumps(nail_tag_profiles, ensure_ascii=False, indent=2)

    return f'''// Generated from nail taxonomy directory.
// Keep this file deterministic: update source taxonomy, then regenerate.
import type {{ NailStyle, NailTaxonomy }} from "./types";

export type NailTagProfile = {{
  styleId: string;
  sourceFilename: string;
  rawTags: string[];
  taxonomy: NailTaxonomy;
  searchText: string;
}};

export const nailTaxonomyDimensions = {dimensions_json} as const;

export const nailStyleDisplayNames: Record<string, string> = {names_json};

export const nailTagProfiles: Record<string, NailTagProfile> = {profiles_json};

const lengthMap: Record<string, NailStyle["nail_length"]> = {{
  "短款": "natural",
  "短甲": "natural",
  "中长款": "medium",
  "中长": "medium",
  "长款": "long",
  "长甲": "long",
}};

function styleLookupId(styleId: string) {{
  if (nailTagProfiles[styleId] || nailStyleDisplayNames[styleId]) return styleId;
  if (styleId.startsWith("seed-")) {{
    const seedKey = styleId.slice(0, "seed-001".length);
    if (nailTagProfiles[seedKey] || nailStyleDisplayNames[seedKey]) return seedKey;
    const libraryKey = `library-20260514-${{seedKey.replace("seed-", "")}}`;
    if (nailTagProfiles[libraryKey] || nailStyleDisplayNames[libraryKey]) return libraryKey;
  }}
  return styleId;
}}

function dedupe(values: Array<string | undefined | null>) {{
  return values.filter((value, index, array): value is string => Boolean(value) && array.indexOf(value) === index);
}}

function compactTaxonomyTags(taxonomy: NailTaxonomy): string[] {{
  return dedupe([
    taxonomy.colors[0],
    taxonomy.techniques[0],
    taxonomy.shapes[0],
    taxonomy.styles[0],
    taxonomy.occasions[0],
    taxonomy.lengths[0],
  ]);
}}

export function taxonomyTokensForStyle(style: NailStyle): string[] {{
  const profile = nailTagProfiles[styleLookupId(style.id)];
  const taxonomy = style.taxonomy ?? profile?.taxonomy;
  return dedupe([
    ...(profile?.rawTags ?? []),
    ...(taxonomy?.colors ?? []),
    ...(taxonomy?.techniques ?? []),
    ...(taxonomy?.shapes ?? []),
    ...(taxonomy?.styles ?? []),
    ...(taxonomy?.occasions ?? []),
    ...(taxonomy?.lengths ?? []),
  ]);
}}

export function applyTaxonomyToStyle(style: NailStyle): NailStyle {{
  const lookupId = styleLookupId(style.id);
  const profile = nailTagProfiles[lookupId];
  if (!profile) return {{ ...style, name: nailStyleDisplayNames[lookupId] ?? style.name }};
  const taxonomy = profile.taxonomy;
  const taxonomyTagTokens = dedupe([
    ...profile.rawTags,
    ...taxonomy.colors,
    ...taxonomy.techniques,
    ...taxonomy.shapes,
    ...taxonomy.styles,
    ...taxonomy.occasions,
    ...taxonomy.lengths,
  ]);
  const nailLength = taxonomy.lengths.map((item) => lengthMap[item]).find(Boolean) ?? style.nail_length;
  return {{
    ...style,
    name: nailStyleDisplayNames[lookupId] ?? style.name,
    color: taxonomy.colors.slice(0, 2).join(" / ") || style.color,
    finish: taxonomy.techniques[0] ?? style.finish,
    occasion: taxonomy.occasions.length ? taxonomy.occasions : ["日常"],
    tags: compactTaxonomyTags(taxonomy),
    taxonomy,
    nail_length: nailLength,
    prompt: `${{style.name}} manicure. Taxonomy: ${{taxonomyTagTokens.join(", ")}}. Required nail shape: ${{taxonomy.shapes.join(", ") || "follow reference"}}. Required nail length: ${{taxonomy.lengths.join(", ") || "follow reference"}}`,
  }};
}}
'''


def build_ts_file_legacy(
    existing_names: dict[str, str],
    profiles: dict[int, dict],
    source_to_library: dict[int, str],
) -> str:
    source_display_names = {
        index: source_display_name(index, existing_names)
        for index in profiles
    }

    style_display_names: dict[str, str] = {}
    nail_tag_profiles: dict[str, dict] = {}

    for source_index in sorted(profiles):
        profile = profiles[source_index]
        display_name = source_display_names[source_index]
        library_suffix = source_to_library.get(source_index)
        if library_suffix is not None:
            library_id = f"library-20260514-{library_suffix}"
            style_display_names[library_id] = display_name
            nail_tag_profiles[library_id] = {
                **profile,
                "styleId": library_id,
            }

        seed_id = f"seed-{source_index:03d}"
        style_display_names[seed_id] = display_name
        nail_tag_profiles[seed_id] = {
            **profile,
            "styleId": seed_id,
        }

    if "library-20260514-032" in existing_names:
        style_display_names["library-20260514-032"] = existing_names["library-20260514-032"]
    if "seed-031" in existing_names:
        style_display_names["seed-031"] = existing_names["seed-031"]
    if "seed-032" in existing_names:
        style_display_names["seed-032"] = existing_names["seed-032"]

    data = {
        "nailTaxonomyDimensions": {key: label for key, label in (DIMENSION_CONFIG[d] for d in DIMENSION_CONFIG)},
        "nailStyleDisplayNames": style_display_names,
        "nailTagProfiles": nail_tag_profiles,
    }

    dimensions_json = json.dumps(data["nailTaxonomyDimensions"], ensure_ascii=False, indent=2)
    names_json = json.dumps(data["nailStyleDisplayNames"], ensure_ascii=False, indent=2)
    profiles_json = json.dumps(data["nailTagProfiles"], ensure_ascii=False, indent=2)

    return f"""// Generated from nail taxonomy directory.\n// Keep this file deterministic: update source taxonomy, then regenerate.\nimport type {{ NailStyle, NailTaxonomy }} from "./types";\n\nexport type NailTagProfile = {{\n  styleId: string;\n  sourceFilename: string;\n  rawTags: string[];\n  taxonomy: NailTaxonomy;\n  searchText: string;\n}};\n\nexport const nailTaxonomyDimensions = {dimensions_json} as const;\n\nexport const nailStyleDisplayNames: Record<string, string> = {names_json};\n\nexport const nailTagProfiles: Record<string, NailTagProfile> = {profiles_json};\n\nconst lengthMap: Record<string, NailStyle["nail_length"]> = {{\n  "短款": "natural",\n  "短甲": "natural",\n  "中长款": "medium",\n  "中长": "medium",\n  "长款": "long",\n  "长甲": "long",\n}};\n\nconst importedLibraryNoiseTags = new Set({json.dumps(NOISE_TAGS, ensure_ascii=False)});\n\nfunction styleLookupId(styleId: string) {{\n  if (nailTagProfiles[styleId] || nailStyleDisplayNames[styleId]) return styleId;\n  if (styleId.startsWith("seed-")) {{\n    const seedKey = styleId.slice(0, "seed-001".length);\n    if (nailTagProfiles[seedKey] || nailStyleDisplayNames[seedKey]) return seedKey;\n    const libraryKey = `library-20260514-${{seedKey.replace("seed-", "")}}`;\n    if (nailTagProfiles[libraryKey] || nailStyleDisplayNames[libraryKey]) return libraryKey;\n  }}\n  return styleId;\n}}\n\nfunction dedupe(values: Array<string | undefined | null>) {{\n  return values.filter((value, index, array): value is string => Boolean(value) && array.indexOf(value) === index);\n}}\n\nexport function taxonomyTokensForStyle(style: NailStyle): string[] {{\n  const profile = nailTagProfiles[styleLookupId(style.id)];\n  const taxonomy = style.taxonomy ?? profile?.taxonomy;\n  return dedupe([\n    profile?.searchText,\n    ...(profile?.rawTags ?? []),\n    ...(taxonomy?.colors ?? []),\n    ...(taxonomy?.techniques ?? []),\n    ...(taxonomy?.shapes ?? []),\n    ...(taxonomy?.styles ?? []),\n    ...(taxonomy?.occasions ?? []),\n    ...(taxonomy?.lengths ?? []),\n  ]);\n}}\n\nexport function applyTaxonomyToStyle(style: NailStyle): NailStyle {{\n  const lookupId = styleLookupId(style.id);\n  const profile = nailTagProfiles[lookupId];\n  if (!profile) return {{ ...style, name: nailStyleDisplayNames[lookupId] ?? style.name }};\n  const taxonomy = profile.taxonomy;\n  const taxonomyTagTokens = dedupe([\n    ...profile.rawTags,\n    ...taxonomy.colors,\n    ...taxonomy.techniques,\n    ...taxonomy.shapes,\n    ...taxonomy.styles,\n    ...taxonomy.occasions,\n    ...taxonomy.lengths,\n  ]);\n  const nailLength = taxonomy.lengths.map((item) => lengthMap[item]).find(Boolean) ?? style.nail_length;\n  return {{\n    ...style,\n    name: nailStyleDisplayNames[lookupId] ?? style.name,\n    color: taxonomy.colors.slice(0, 2).join(" / ") || style.color,\n    finish: taxonomy.techniques[0] ?? style.finish,\n    occasion: dedupe([...style.occasion, ...taxonomy.occasions]),\n    tags: dedupe([...style.tags.filter((tag) => !importedLibraryNoiseTags.has(tag)), ...taxonomyTagTokens]),\n    taxonomy,\n    nail_length: nailLength,\n    prompt: `${{style.prompt}}. Taxonomy: ${{taxonomyTagTokens.join(", ")}}`,\n  }};\n}}\n"""


def build_py_file(
    existing_names: dict[str, str],
    profiles: dict[int, dict],
    source_to_library: dict[int, str],
) -> str:
    style_display_names: dict[str, str] = {}
    style_taxonomy_by_id: dict[str, dict] = {}

    for source_index in sorted(profiles):
        profile = profiles[source_index]
        display_name = source_display_name(source_index, existing_names)
        library_suffix = source_to_library.get(source_index)
        if library_suffix is not None:
            library_id = f"library-20260514-{library_suffix}"
            style_display_names[library_id] = display_name
            style_taxonomy_by_id[library_id] = {**profile, "styleId": library_id}

        seed_id = f"seed-{source_index:03d}"
        style_display_names[seed_id] = display_name
        style_taxonomy_by_id[seed_id] = {**profile, "styleId": seed_id}

    style_taxonomy_json = json.dumps(style_taxonomy_by_id, ensure_ascii=False, indent=2)
    display_names_json = json.dumps(style_display_names, ensure_ascii=False, indent=2)
    length_map_json = json.dumps(LENGTH_MAP, ensure_ascii=False, indent=2)

    return f'''# Generated from nail taxonomy directory.
# Keep this file deterministic: update source taxonomy, then regenerate.

from __future__ import annotations

from copy import deepcopy

STYLE_TAXONOMY_BY_ID: dict[str, dict] = {style_taxonomy_json}

STYLE_DISPLAY_NAMES: dict[str, str] = {display_names_json}

LENGTH_MAP = {length_map_json}


def _style_lookup_id(style_id: str) -> str:
    if style_id in STYLE_TAXONOMY_BY_ID:
        return style_id
    if style_id in STYLE_DISPLAY_NAMES:
        return style_id
    if style_id.startswith("seed-") and len(style_id) >= len("seed-001"):
        seed_key = style_id[: len("seed-001")]
        if seed_key in STYLE_TAXONOMY_BY_ID or seed_key in STYLE_DISPLAY_NAMES:
            return seed_key
        library_key = f"library-20260514-{{seed_key.removeprefix('seed-')}}"
        if library_key in STYLE_TAXONOMY_BY_ID or library_key in STYLE_DISPLAY_NAMES:
            return library_key
    return style_id


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        result.append(value)
        seen.add(value)
    return result


def _has_taxonomy(taxonomy: object) -> bool:
    if not isinstance(taxonomy, dict):
        return False
    for key in ["colors", "techniques", "shapes", "styles", "occasions", "lengths"]:
        values = taxonomy.get(key)
        if isinstance(values, list) and values:
            return True
    return False


def _compact_taxonomy_tags(taxonomy: dict) -> list[str]:
    tags: list[str] = []
    for key in ["colors", "techniques", "shapes", "styles", "occasions", "lengths"]:
        values = taxonomy.get(key) or []
        if values:
            tags.append(values[0])
    return _dedupe(tags)


def taxonomy_tokens_for_style_dict(style: dict) -> list[str]:
    lookup_id = _style_lookup_id(style.get("id", ""))
    profile = STYLE_TAXONOMY_BY_ID.get(lookup_id)
    taxonomy = style.get("taxonomy") if _has_taxonomy(style.get("taxonomy")) else profile.get("taxonomy", {{}}) if profile else {{}}

    tokens: list[str] = []
    if profile:
        tokens.extend(profile.get("rawTags", []))
    for key in ["colors", "techniques", "shapes", "styles", "occasions", "lengths"]:
        tokens.extend(taxonomy.get(key, []))
    return _dedupe([token for token in tokens if token])


def enrich_style_dict(style: dict) -> dict:
    style_id = style.get("id", "")
    lookup_id = _style_lookup_id(style_id)
    profile = STYLE_TAXONOMY_BY_ID.get(lookup_id)

    if not _has_taxonomy(style.get("taxonomy")) and not profile:
        if lookup_id in STYLE_DISPLAY_NAMES:
            enriched = deepcopy(style)
            enriched["name"] = STYLE_DISPLAY_NAMES[lookup_id]
            return enriched
        return style

    enriched = deepcopy(style)
    taxonomy = deepcopy(style.get("taxonomy")) if _has_taxonomy(style.get("taxonomy")) else deepcopy(profile["taxonomy"])
    raw_tags = profile.get("rawTags", []) if profile else []
    tokens = _dedupe([
        *raw_tags,
        *taxonomy.get("colors", []),
        *taxonomy.get("techniques", []),
        *taxonomy.get("shapes", []),
        *taxonomy.get("styles", []),
        *taxonomy.get("occasions", []),
        *taxonomy.get("lengths", []),
    ])

    enriched["taxonomy"] = taxonomy
    enriched["name"] = STYLE_DISPLAY_NAMES.get(lookup_id, enriched.get("name", ""))
    enriched["tags"] = _compact_taxonomy_tags(taxonomy)
    enriched["occasion"] = taxonomy.get("occasions", []) or ["日常"]

    if taxonomy.get("colors"):
        enriched["color"] = " / ".join(taxonomy["colors"][:2])
    if taxonomy.get("techniques"):
        enriched["finish"] = taxonomy["techniques"][0]
    if taxonomy.get("lengths"):
        enriched["nail_length"] = next((LENGTH_MAP[item] for item in taxonomy["lengths"] if item in LENGTH_MAP), enriched.get("nail_length", "natural"))

    enriched["prompt"] = (
        f"{{enriched.get('name', '')}} manicure. Taxonomy: {{', '.join(tokens)}}. "
        f"Required nail shape: {{', '.join(taxonomy.get('shapes', [])) or 'follow reference'}}. "
        f"Required nail length: {{', '.join(taxonomy.get('lengths', [])) or 'follow reference'}}"
    )

    return enriched
'''


def build_py_file_legacy(
    existing_names: dict[str, str],
    profiles: dict[int, dict],
    source_to_library: dict[int, str],
) -> str:
    source_display_names = {
        index: existing_names.get(f"library-20260514-{index:03d}", f"美甲{index:02d}")
        for index in profiles
    }

    style_display_names: dict[str, str] = {}
    style_taxonomy_by_id: dict[str, dict] = {}

    for source_index in sorted(profiles):
        profile = profiles[source_index]
        display_name = source_display_names[source_index]
        library_suffix = source_to_library.get(source_index)
        if library_suffix is not None:
            library_id = f"library-20260514-{library_suffix}"
            style_display_names[library_id] = display_name
            style_taxonomy_by_id[library_id] = {
                **profile,
                "styleId": library_id,
            }

        seed_id = f"seed-{source_index:03d}"
        style_display_names[seed_id] = display_name
        style_taxonomy_by_id[seed_id] = {
            **profile,
            "styleId": seed_id,
        }

    if "library-20260514-032" in existing_names:
        style_display_names["library-20260514-032"] = existing_names["library-20260514-032"]
    if "seed-031" in existing_names:
        style_display_names["seed-031"] = existing_names["seed-031"]
    if "seed-032" in existing_names:
        style_display_names["seed-032"] = existing_names["seed-032"]

    style_taxonomy_json = json.dumps(style_taxonomy_by_id, ensure_ascii=False, indent=2)
    display_names_json = json.dumps(style_display_names, ensure_ascii=False, indent=2)

    return f"""# Generated from nail taxonomy directory.\n# Keep this file deterministic: update source taxonomy, then regenerate.\n\nfrom __future__ import annotations\n\nfrom copy import deepcopy\n\nSTYLE_TAXONOMY_BY_ID: dict[str, dict] = {style_taxonomy_json}\n\nSTYLE_DISPLAY_NAMES: dict[str, str] = {display_names_json}\n\nLENGTH_MAP = {json.dumps(LENGTH_MAP, ensure_ascii=False, indent=2)}\n\nIMPORTED_LIBRARY_NOISE_TAGS = {set(NOISE_TAGS)!r}\n\n\ndef _style_lookup_id(style_id: str) -> str:\n    if style_id in STYLE_TAXONOMY_BY_ID:\n        return style_id\n    if style_id in STYLE_DISPLAY_NAMES:\n        return style_id\n    if style_id.startswith(\"seed-\") and len(style_id) >= len(\"seed-001\"):\n        seed_key = style_id[: len(\"seed-001\")]\n        if seed_key in STYLE_TAXONOMY_BY_ID or seed_key in STYLE_DISPLAY_NAMES:\n            return seed_key\n        library_key = f\"library-20260514-{{seed_key.removeprefix('seed-')}}\"\n        if library_key in STYLE_TAXONOMY_BY_ID or library_key in STYLE_DISPLAY_NAMES:\n            return library_key\n    return style_id\n\n\ndef _dedupe(values: list[str]) -> list[str]:\n    seen: set[str] = set()\n    result: list[str] = []\n    for value in values:\n        if not value or value in seen:\n            continue\n        result.append(value)\n        seen.add(value)\n    return result\n\n\ndef taxonomy_tokens_for_style_dict(style: dict) -> list[str]:\n    lookup_id = _style_lookup_id(style.get(\"id\", \"\"))\n    profile = STYLE_TAXONOMY_BY_ID.get(lookup_id)\n\n    db_taxonomy = style.get(\"taxonomy\")\n    has_db_taxonomy = False\n    if isinstance(db_taxonomy, dict):\n        for key in [\"colors\", \"techniques\", \"shapes\", \"styles\", \"occasions\", \"lengths\"]:\n            if db_taxonomy.get(key) and isinstance(db_taxonomy[key], list) and len(db_taxonomy[key]) > 0:\n                has_db_taxonomy = True\n                break\n\n    if has_db_taxonomy:\n        taxonomy = db_taxonomy\n    elif profile:\n        taxonomy = profile.get(\"taxonomy\", {{}})\n    else:\n        taxonomy = {{}}\n\n    tokens: list[str] = []\n    if profile:\n        tokens.extend(profile.get(\"rawTags\", []))\n        tokens.append(profile.get(\"searchText\", \"\"))\n    for key in [\"colors\", \"techniques\", \"shapes\", \"styles\", \"occasions\", \"lengths\"]:\n        tokens.extend(taxonomy.get(key, []))\n    return _dedupe([token for token in tokens if token])\n\n\ndef enrich_style_dict(style: dict) -> dict:\n    style_id = style.get(\"id\", \"\")\n    lookup_id = _style_lookup_id(style_id)\n    profile = STYLE_TAXONOMY_BY_ID.get(lookup_id)\n\n    db_taxonomy = style.get(\"taxonomy\")\n    has_db_taxonomy = False\n    if isinstance(db_taxonomy, dict):\n        for key in [\"colors\", \"techniques\", \"shapes\", \"styles\", \"occasions\", \"lengths\"]:\n            if db_taxonomy.get(key) and isinstance(db_taxonomy[key], list) and len(db_taxonomy[key]) > 0:\n                has_db_taxonomy = True\n                break\n\n    if not has_db_taxonomy and not profile:\n        if lookup_id in STYLE_DISPLAY_NAMES:\n            enriched = deepcopy(style)\n            enriched[\"name\"] = STYLE_DISPLAY_NAMES[lookup_id]\n            return enriched\n        return style\n\n    enriched = deepcopy(style)\n\n    if has_db_taxonomy:\n        taxonomy = deepcopy(db_taxonomy)\n        raw_tags = profile.get(\"rawTags\", []) if profile else []\n    else:\n        taxonomy = deepcopy(profile[\"taxonomy\"])\n        raw_tags = profile.get(\"rawTags\", [])\n\n    tokens = _dedupe([\n        *raw_tags,\n        *taxonomy.get(\"colors\", []),\n        *taxonomy.get(\"techniques\", []),\n        *taxonomy.get(\"shapes\", []),\n        *taxonomy.get(\"styles\", []),\n        *taxonomy.get(\"occasions\", []),\n        *taxonomy.get(\"lengths\", []),\n    ])\n\n    enriched[\"taxonomy\"] = taxonomy\n    enriched[\"name\"] = STYLE_DISPLAY_NAMES.get(lookup_id, enriched.get(\"name\", \"\"))\n\n    base_tags = [tag for tag in enriched.get(\"tags\", []) if tag not in IMPORTED_LIBRARY_NOISE_TAGS]\n    enriched[\"tags\"] = _dedupe([*base_tags, *raw_tags, *tokens])\n    enriched[\"occasion\"] = _dedupe([*enriched.get(\"occasion\", []), *taxonomy.get(\"occasions\", [])])\n\n    if taxonomy.get(\"colors\"):\n        enriched[\"color\"] = \" / \".join(taxonomy[\"colors\"][:2])\n    if taxonomy.get(\"techniques\"):\n        enriched[\"finish\"] = taxonomy[\"techniques\"][0]\n    if taxonomy.get(\"lengths\"):\n        enriched[\"nail_length\"] = next((LENGTH_MAP[item] for item in taxonomy[\"lengths\"] if item in LENGTH_MAP), enriched.get(\"nail_length\", \"natural\"))\n\n    base_prompt = enriched.get(\"prompt\", \"\")\n    if \"Taxonomy:\" in base_prompt:\n        base_prompt = base_prompt.split(\". Taxonomy:\")[0]\n    enriched[\"prompt\"] = f\"{{base_prompt}}. Taxonomy: {{', '.join(tokens)}}\"\n\n    return enriched\n"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", help="Path to taxonomy directory")
    args = parser.parse_args()

    source_root = Path(args.source_dir).expanduser().resolve()
    existing_names = read_existing_display_names()
    source_to_library, unmatched_library_ids = build_image_mapping(source_root)
    profiles = collect_profiles(source_root)
    canonical_records = build_canonical_records(existing_names, profiles, source_to_library)

    WEB_TAXONOMY_PATH.write_text(
        build_ts_file(existing_names, profiles, source_to_library),
        encoding="utf-8",
    )
    WEB_IMPORTED_STYLES_PATH.write_text(
        build_imported_styles_file(canonical_records),
        encoding="utf-8",
    )
    API_TAXONOMY_JSON_PATH.write_text(
        json.dumps(canonical_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    API_TAXONOMY_PATH.write_text(
        build_py_file(existing_names, profiles, source_to_library),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "source_count": len(profiles),
                "canonical_style_count": len(canonical_records),
                "mapped_source_to_library": source_to_library,
                "unmatched_library_ids": unmatched_library_ids,
                "web_output": str(WEB_TAXONOMY_PATH),
                "imported_styles_output": str(WEB_IMPORTED_STYLES_PATH),
                "api_taxonomy_json_output": str(API_TAXONOMY_JSON_PATH),
                "api_output": str(API_TAXONOMY_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
