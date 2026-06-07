from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import httpx

from app.config import settings
from app.schemas import ChatMessage, ChatResponse, NailStyle
from app.services.style_catalog import get_style, list_styles, search_styles


def infer_intent(message: str) -> str:
    """Infer user intent from message using taxonomy dimensions."""
    # Occasion-based
    if any(word in message for word in ["婚礼", "伴娘", "正式"]):
        return "occasion_wedding"
    if any(word in message for word in ["通勤", "上班", "低调", "日常"]):
        return "occasion_work"
    if any(word in message for word in ["约会", "温柔", "显白", "拍照"]):
        return "occasion_date"
    if any(word in message for word in ["派对", "酷", "闪", "个性", "节日"]):
        return "occasion_party"
    # Length-based
    if any(word in message for word in ["短甲", "本甲", "自然"]):
        return "length_short"
    if any(word in message for word in ["长甲", "延长", "梯形", "尖甲"]):
        return "length_long"
    # Color-based
    if any(word in message for word in ["显白", "裸色", "清透", "冰透"]):
        return "color_nude_sheer"
    if any(word in message for word in ["红色", "酒红", "复古红"]):
        return "color_red"
    if any(word in message for word in ["粉色", "甜系", "少女"]):
        return "color_pink"
    # Technique-based
    if any(word in message for word in ["法式", "猫眼", "渐变", "魔镜"]):
        return "technique_specific"
    # Style-based
    if any(word in message for word in ["复古", "可爱", "简约", "华丽"]):
        return "style_preference"
    return "style_explore"


SHAPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "方圆型": ("方圆", "方圆型", "圆方", "短甲", "短甲友好", "本甲", "自然甲", "百搭"),
    "杏仁型": ("杏仁", "杏仁型", "椭圆", "修长", "显手长", "优雅"),
    "圆形": ("圆形", "圆润", "自然圆", "圆甲"),
    "尖型": ("尖型", "尖形", "尖甲", "芭蕾", "stiletto", "辣妹", "酷感"),
    "梯型": ("梯型", "梯形", "coffin", "棺材", "长款", "延长甲"),
}

LENGTH_KEYWORDS: dict[str, tuple[str, ...]] = {
    "natural": ("短甲", "短款", "本甲", "自然", "短甲友好"),
    "medium": ("中长", "中长款", "中长甲"),
    "long": ("长甲", "长款", "延长", "超长", "长指甲"),
}

LENGTH_TAXONOMY_BY_CODE = {
    "natural": {"短款", "本甲", "短甲"},
    "medium": {"中长款", "中长甲"},
    "long": {"长款", "长甲", "延长甲"},
}


def _normalize_text(message: str) -> str:
    return message.replace("，", " ").replace(",", " ").strip().lower()


def _detect_length(message: str, selected_styles: list[NailStyle]) -> str | None:
    text = _normalize_text(message)
    # Check transitions if both "长" and "短" are present
    if ("长" in text or "延长" in text) and ("短" in text or "本甲" in text):
        if any(pat in text for pat in ["换成短", "改成短", "做短", "要短", "选短", "做短甲", "换短", "改短", "怕断"]):
            return "natural"
        if any(pat in text for pat in ["换成长", "改成长", "做长", "要长", "选长", "做长甲", "换长", "改长"]):
            return "long"

    for length, keywords in LENGTH_KEYWORDS.items():
        if any(keyword.lower() in text for keyword in keywords):
            return length
    for style in selected_styles:
        taxonomy_lengths = (style.taxonomy or {}).get("lengths", [])
        if any(item in LENGTH_TAXONOMY_BY_CODE["long"] for item in taxonomy_lengths):
            return "long"
        if any(item in LENGTH_TAXONOMY_BY_CODE["medium"] for item in taxonomy_lengths):
            return "medium"
        if any(item in LENGTH_TAXONOMY_BY_CODE["natural"] for item in taxonomy_lengths):
            return "natural"
        if style.nail_length in {"long", "medium", "natural"}:
            return style.nail_length
    return None


def _detect_shape(message: str, selected_styles: list[NailStyle], target_length: str | None) -> str | None:
    text = _normalize_text(message)
    for shape, keywords in SHAPE_KEYWORDS.items():
        if any(keyword.lower() in text for keyword in keywords):
            return shape

    for style in selected_styles:
        taxonomy_shapes = (style.taxonomy or {}).get("shapes", [])
        if taxonomy_shapes:
            return taxonomy_shapes[0]

    if target_length == "natural":
        return "方圆型"
    if target_length == "medium":
        return "杏仁型"
    if target_length == "long":
        return "梯型"
    return None


def _length_taxonomy_match(style: NailStyle, target_length: str | None) -> bool:
    if not target_length:
        return True
    taxonomy_lengths = (style.taxonomy or {}).get("lengths", [])
    if target_length == "natural":
        return style.nail_length == "natural" or any(item in LENGTH_TAXONOMY_BY_CODE["natural"] for item in taxonomy_lengths)
    if target_length == "medium":
        return style.nail_length == "medium" or any(item in LENGTH_TAXONOMY_BY_CODE["medium"] for item in taxonomy_lengths)
    if target_length == "long":
        return style.nail_length == "long" or any(item in LENGTH_TAXONOMY_BY_CODE["long"] for item in taxonomy_lengths)
    return True


def _shape_taxonomy_match(style: NailStyle, target_shape: str | None) -> bool:
    if not target_shape:
        return True
    taxonomy_shapes = (style.taxonomy or {}).get("shapes", [])
    if target_shape in taxonomy_shapes:
        return True
    normalized_shape = target_shape.replace("型", "")
    return any(normalized_shape and normalized_shape in item for item in taxonomy_shapes)


def _rank_local_styles(message: str, selected_style_ids: list[str]) -> tuple[list[NailStyle], str, str | None]:
    selected_styles = [get_style(style_id) for style_id in selected_style_ids if style_id]
    target_length = _detect_length(message, selected_styles)
    target_shape = _detect_shape(message, selected_styles, target_length)

    topical_styles = search_styles(message, limit=12)
    candidate_map: dict[str, NailStyle] = {}
    for style in [*selected_styles, *topical_styles, *list_styles()]:
        candidate_map.setdefault(style.id, style)

    topical_rank = {style.id: index for index, style in enumerate(topical_styles)}

    def _sort_key(style: NailStyle):
        shape_penalty = 0 if _shape_taxonomy_match(style, target_shape) else 1
        length_penalty = 0 if _length_taxonomy_match(style, target_length) else 1
        selected_bonus = 0 if style.id in selected_style_ids else 1
        topical_bonus = topical_rank.get(style.id, 999)
        stock_gap = max((style.stock_total or 0) - (style.stock_reserved or 0), 0)
        return (selected_bonus, shape_penalty, length_penalty, topical_bonus, -stock_gap, style.name)

    ranked = sorted(candidate_map.values(), key=_sort_key)
    filtered = [style for style in ranked if _shape_taxonomy_match(style, target_shape) and _length_taxonomy_match(style, target_length)]
    if len(filtered) >= 4:
        ranked = filtered

    return ranked[:5], target_shape or "方圆型", target_length


def _build_shape_first_reply(message: str, selected_style_ids: list[str]) -> ChatResponse:
    recommended_styles, target_shape, target_length = _rank_local_styles(message, selected_style_ids)
    intent = infer_intent(message)

    length_label = {
        "natural": "短甲",
        "medium": "中长甲",
        "long": "长甲",
    }.get(target_length or "natural", "短甲")

    style_names = "、".join(style.name for style in recommended_styles[:3]) if recommended_styles else "几款库存现货"
    reply = (
        f"我先把甲型锁定为「{target_shape}」，再从库存里挑了 {style_names} 这几款。"
        f"它们都更贴近{length_label}的使用场景，也更容易把甲型做对。"
    )
    if recommended_styles:
        reply += f" 如果你想换成别的甲型，我可以继续按「甲型优先」重新筛。"
    follow_up_questions = [
        "你更想要方圆型、杏仁型还是圆形？",
        "想继续偏短甲还是中长甲？",
        "颜色上要显白的裸色系还是更有存在感的彩色系？",
    ]
    if target_shape:
        follow_up_questions[0] = f"要不要就先定「{target_shape}」？"

    return ChatResponse(
        reply=reply,
        intent=intent if intent != "style_explore" else "shape_first_recommendation",
        recommended_styles=recommended_styles,
        follow_up_questions=follow_up_questions,
        channel="local-shape-first",
        model=None,
    )


def _compact_style(style: NailStyle) -> dict[str, Any]:
    return {
        "id": style.id,
        "name": style.name,
        "color": style.color,
        "finish": style.finish,
        "occasion": style.occasion,
        "tags": style.tags[:5],
        "taxonomy": style.taxonomy,
        "nail_length": style.nail_length,
        "price_level": style.price_level,
        "stock_total": style.stock_total,
        "image_url": style.image_url,
    }


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, re.S)
    if match:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("Qwen chat response did not contain valid JSON")


def _fallback_chat(message: str, selected_style_ids: list[str]) -> ChatResponse:
    intent = infer_intent(message)
    selected_styles = [get_style(style_id) for style_id in selected_style_ids if style_id]
    recommended_styles = selected_styles or search_styles(message, limit=5)
    names = "、".join(style.name for style in recommended_styles[:3])

    # Build taxonomy-aware reply
    taxonomy_hints = []
    for style in recommended_styles[:2]:
        if style.taxonomy:
            colors = style.taxonomy.get("colors", [])
            techniques = style.taxonomy.get("techniques", [])
            if colors:
                taxonomy_hints.append(colors[0])
            if techniques:
                taxonomy_hints.append(techniques[0])

    hint_text = ""
    if taxonomy_hints:
        hint_text = f"方向上偏向{'、'.join(taxonomy_hints[:3])}这类风格。"

    reply = (
        f"我先按你的描述推荐了 {names}。{hint_text}"
        "可以试戴看看效果，也可以继续告诉我你更偏哪种甲型或颜色。"
    )
    return ChatResponse(
        reply=reply,
        intent=intent,
        recommended_styles=recommended_styles,
        follow_up_questions=["你更偏短甲还是中长甲？", "这次是日常、约会还是正式场合？", "颜色上偏好裸色系还是彩色系？"],
        channel="local-fallback",
        model=None,
    )


def _build_candidate_styles(message: str, selected_style_ids: list[str]) -> list[NailStyle]:
    selected_styles = [get_style(style_id) for style_id in selected_style_ids if style_id]
    discovered_styles = search_styles(message, limit=8)
    merged: list[NailStyle] = []
    seen: set[str] = set()
    for style in [*selected_styles, *discovered_styles, *list_styles()[1:]]:
        if style.id in seen:
            continue
        merged.append(style)
        seen.add(style.id)
        if len(merged) >= 12:
            break
    return merged


def search_nail_styles(
    query: str | None = None,
    color: str | None = None,
    finish: str | None = None,
    nail_length: str | None = None,
) -> list[dict[str, Any]]:
    """
    Search styles from catalog based on tags extracted by LLM.
    """
    all_styles = list_styles()
    scored_styles = []

    # Detect intended length from both the parameter and query text (to handle negative/transition contexts)
    intended_length = nail_length
    if query:
        norm_q = query.lower()
        if ("长" in norm_q or "延长" in norm_q) and ("短" in norm_q or "本甲" in norm_q):
            if any(pat in norm_q for pat in ["换成短", "改成短", "做短", "要短", "选短", "做短甲", "换短", "改短", "怕断"]):
                intended_length = "natural"
            elif any(pat in norm_q for pat in ["换成长", "改成长", "做长", "要长", "选长", "做长甲", "换长", "改长"]):
                intended_length = "long"
        elif not intended_length:
            if any(kw in norm_q for kw in ["短甲", "短款", "本甲", "短指甲", "短的", "短甲友好"]):
                intended_length = "natural"
            elif any(kw in norm_q for kw in ["中长", "中长款", "中长甲", "中等"]):
                intended_length = "medium"
            elif any(kw in norm_q for kw in ["长甲", "长款", "延长", "超长", "长指甲", "长的"]):
                intended_length = "long"

    for style in all_styles:
        # Exclude styles with conflicting length targets
        if intended_length:
            style_length = style.nail_length
            style_tags_text = " ".join(style.tags or []).lower() + " " + style.name.lower()
            if intended_length == "natural":
                if style_length == "long" or any(kw in style_tags_text for kw in ["长甲", "长款", "延长", "超长", "长指甲"]):
                    continue
            elif intended_length == "long":
                if style_length == "natural" or any(kw in style_tags_text for kw in ["短甲", "短款", "本甲", "短指甲"]):
                    continue

        score = 0
        
        # Color match
        if color:
            norm_c = color.replace("色", "").replace("系", "").strip()
            if norm_c:
                if norm_c in style.color or (style.taxonomy and any(norm_c in c for c in style.taxonomy.get("colors", []))):
                    score += 5
                
        # Finish / Element match
        if finish:
            norm_f = finish.strip()
            if norm_f:
                if norm_f in style.finish or (style.taxonomy and any(norm_f in t for t in style.taxonomy.get("techniques", []))):
                    score += 5

        # Nail Length match
        if nail_length:
            norm_l = nail_length.lower().strip()
            if norm_l:
                if style.nail_length == norm_l:
                    score += 3
                elif style.taxonomy:
                    # Match taxonomy tags
                    lengths = style.taxonomy.get("lengths", [])
                    if norm_l == "natural" and any(item in LENGTH_TAXONOMY_BY_CODE["natural"] for item in lengths):
                        score += 3
                    elif norm_l == "medium" and any(item in LENGTH_TAXONOMY_BY_CODE["medium"] for item in lengths):
                        score += 3
                    elif norm_l == "long" and any(item in LENGTH_TAXONOMY_BY_CODE["long"] for item in lengths):
                        score += 3

        # Query word matching in name, tags, description
        if query:
            # Tokenize by space and Chinese commas
            words = [w.strip() for w in re.split(r"[\s,，、]+", query) if w.strip()]
            for word in words:
                if not word:
                    continue
                if word in style.name:
                    score += 4
                if style.tags and any(word in tag for tag in style.tags):
                    score += 3
                if style.prompt and word in style.prompt:
                    score += 2
                if style.taxonomy:
                    for val_list in style.taxonomy.values():
                        if any(word in val for val in val_list):
                            score += 2
                            break
            
            # Substring matching for known terms on continuous query text
            for style_tag in style.tags or []:
                if style_tag and style_tag.lower() in query.lower():
                    # Skip matching negative/conflicting keywords
                    if style_tag.lower() in ["长甲", "长款", "延长", "超长", "长指甲"] and intended_length == "natural":
                        continue
                    if style_tag.lower() in ["短甲", "短款", "本甲", "短指甲"] and intended_length == "long":
                        continue
                    score += 3

        if score > 0 or not any([query, color, finish, nail_length]):
            scored_styles.append((style, score))

    # Sort candidates by score descending
    scored_styles.sort(key=lambda x: x[1], reverse=True)

    results = []
    for style, score in scored_styles[:6]:
        results.append({
            "id": style.id,
            "name": style.name,
            "color": style.color,
            "finish": style.finish,
            "nail_length": style.nail_length,
            "tags": style.tags[:5],
            "price_level": style.price_level,
        })
    return results


async def _call_qwen_chat(
    message: str,
    selected_style_ids: list[str],
    history: list[ChatMessage],
) -> ChatResponse:
    base_url = (
        settings.qwen_chat_api_url
        or settings.openai_compatible_base_url
        or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ).rstrip("/")
    api_key = settings.qwen_chat_api_key or settings.openai_compatible_api_key or settings.image2_api_key
    if not api_key:
        raise ValueError("Missing QWEN_CHAT_API_KEY")

    # 1. Define standard tools for Function Calling
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_nail_styles",
                "description": "根据用户描述的美甲偏好、季节、颜色、元素等标签，在当前数据库中搜索匹配的美甲款式候选列表。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索偏好或偏向的场景/主观款式描述，例如：婚礼、上班、温柔、海边"
                        },
                        "color": {
                            "type": "string",
                            "description": "主色系偏好，例如：裸色、粉色、红色、酒红、黑色"
                        },
                        "finish": {
                            "type": "string",
                            "description": "表面效果或装饰工艺，例如：猫眼、碎钻、渐变、闪粉、法式"
                        },
                        "nail_length": {
                            "type": "string",
                            "description": "指甲长度，只能是：natural (短甲/短款), medium (中长甲/中长款), long (长甲/长款)"
                        }
                    },
                    "required": []
                }
            }
        }
    ]

    # 2. Define System Prompt
    system_prompt = (
        "你是一个懂时尚、懂审美、像闺蜜一样亲切贴心的美甲推荐师。"
        "你的任务是根据用户偏好推荐库存美甲款式。对于多轮对话，请基于用户的新增偏好，推荐最贴合的款式。\n"
        "你必须始终以规范的 JSON 对象形式进行最终的答复，千万不要输出 Markdown 代码块，不要包含 ```json 等标记，不要附加解释文本。\n"
        "最终的 JSON 响应格式必须是：\n"
        '{"reply": "给用户的一段极具亲和力、闺蜜般温暖自然的中文推荐回复（介绍具体推荐的款式和推荐理由，并鼓励用户进行试戴或到店制作）", '
        '"intent": "一个简短意图标签（如 occasion_party, length_short, retro_style 等）", '
        '"recommended_style_ids": ["候选款式 id1", "候选款式 id2"], '
        '"follow_up_questions": ["追问1", "追问2"]}\n'
        "约束条件：\n"
        "1. 如果用户输入了具体的设计要求（颜色、长度、配饰等），请调用 search_nail_styles 工具检索数据库。\n"
        "2. 工具返回的候选款式具有 id, name, color, finish, nail_length 等属性。你在最终推荐时，推荐的 id 必须严格限制在工具检索返回的结果中，严禁捏造不存在的 id。\n"
        "3. 如果用户只是进行简单打招呼、日常闲聊或者未表达特定偏好，无需调用工具，但在最终响应中也请遵循上述 JSON 格式（其中 recommended_style_ids 留空）。"
    )

    # 3. Build messages list including chat history
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-6:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": message})

    # 4. First API call
    payload = {
        "model": settings.qwen_chat_model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.5,
        "top_p": 0.9,
    }

    async with httpx.AsyncClient(timeout=settings.chat_timeout_seconds) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if response.status_code >= 400:
        try:
            body = response.json()
        except Exception:
            body = response.text
        raise RuntimeError(f"Qwen chat first call failed: {body}")

    data = response.json()
    choice = data.get("choices", [{}])[0]
    message_obj = choice.get("message", {})
    tool_calls = message_obj.get("tool_calls")

    # 5. If tool call is requested
    if tool_calls:
        # Append the assistant message with tool calls to history
        messages.append(message_obj)
        
        # Execute tool calls
        for tool_call in tool_calls:
            function_name = tool_call.get("function", {}).get("name")
            function_args = tool_call.get("function", {}).get("arguments") or "{}"
            
            if function_name == "search_nail_styles":
                try:
                    args = json.loads(function_args)
                except Exception:
                    args = {}
                
                # Run the search style function
                search_results = search_nail_styles(
                    query=args.get("query"),
                    color=args.get("color"),
                    finish=args.get("finish"),
                    nail_length=args.get("nail_length")
                )
                
                # Append tool result message
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "name": "search_nail_styles",
                    "content": json.dumps(search_results, ensure_ascii=False)
                })

        # Second API call to generate final answer
        payload_final = {
            "model": settings.qwen_chat_model,
            "messages": messages,
            "temperature": 0.4,
            "top_p": 0.9,
        }
        
        async with httpx.AsyncClient(timeout=settings.chat_timeout_seconds) as client:
            response_final = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload_final,
            )
            
        if response_final.status_code >= 400:
            try:
                body = response_final.json()
            except Exception:
                body = response_final.text
            raise RuntimeError(f"Qwen chat second call failed: {body}")
            
        data_final = response_final.json()
        content = data_final.get("choices", [{}])[0].get("message", {}).get("content", "")
    else:
        content = message_obj.get("content", "")

    if not content:
        raise ValueError("Qwen chat returned empty content")

    # 6. Parse structured JSON from LLM content
    parsed = _extract_json(content)
    reply = str(parsed.get("reply") or "").strip()
    intent = str(parsed.get("intent") or infer_intent(message)).strip() or infer_intent(message)
    style_ids = parsed.get("recommended_style_ids") or []
    if not isinstance(style_ids, list):
        style_ids = []

    recommended_styles: list[NailStyle] = []
    seen: set[str] = set()
    for style_id in style_ids:
        if not isinstance(style_id, str):
            continue
        style = get_style(style_id)
        if style and style.id not in seen:
            recommended_styles.append(style)
            seen.add(style.id)
            if len(recommended_styles) >= 5:
                break

    if not recommended_styles:
        recommended_styles = search_styles(message, limit=5)

    follow_up_questions = parsed.get("follow_up_questions") or []
    if not isinstance(follow_up_questions, list):
        follow_up_questions = []
    follow_up_questions = [str(item).strip() for item in follow_up_questions if str(item).strip()]
    if not follow_up_questions:
        follow_up_questions = ["你更偏短甲还是中长甲？", "这次是日常、约会还是正式场合？", "颜色上偏好裸色系还是彩色系？"]

    if not reply:
        reply = f"亲爱的，我为你挑选了「{recommended_styles[0].name}」等几款款式，你觉得怎么样？可以继续告诉我你偏爱的甲型或颜色哦！"

    return ChatResponse(
        reply=reply,
        intent=intent,
        recommended_styles=recommended_styles,
        follow_up_questions=follow_up_questions,
        channel="qwen-chat",
        model=settings.qwen_chat_model,
    )


async def recommend(message: str, selected_style_ids: list[str], history: list[ChatMessage]) -> ChatResponse:
    try:
        return await _call_qwen_chat(message, selected_style_ids, history)
    except Exception as exc:
        import logging
        import traceback
        logging.warning(f"Failed to call Qwen chat for recommendation, using shape-first fallback. Error: {exc}\nTraceback:\n{traceback.format_exc()}")
        return _build_shape_first_reply(message, selected_style_ids)


async def stream_recommend(message: str, selected_style_ids: list[str], history: list[ChatMessage]):
    response = await recommend(message, selected_style_ids, history)
    yield {"event": "meta", "data": {"channel": response.channel, "model": response.model, "intent": response.intent}}
    text = response.reply or ""
    for index in range(0, len(text), 12):
        chunk = text[index:index + 12]
        if chunk:
            yield {"event": "delta", "data": {"text": chunk}}
            await asyncio.sleep(0.02)
    yield {
        "event": "done",
        "data": {
            "reply": response.reply,
            "intent": response.intent,
            "recommended_styles": [style.model_dump() for style in response.recommended_styles],
            "follow_up_questions": response.follow_up_questions,
            "channel": response.channel,
            "model": response.model,
        },
    }
