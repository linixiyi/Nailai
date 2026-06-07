from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from io import BytesIO
from typing import Any

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from app.config import settings
from app.schemas import DiyBountyAnswers, DiyBountyVariant
from app.services.image2_client import _ensure_data_url, _normalize_image_bytes


def build_diy_bounty_prompt(answers: DiyBountyAnswers, variant_index: int = 0, has_hand_image: bool = False) -> str:
    colors = "、".join(answers.colors) if answers.colors else "按参考图主色"
    decorations = "、".join(answers.decorations) if answers.decorations else "少量精致装饰"
    variant_focus = ["低调可做版", "保留参考图版", "加强设计版", "短甲/日常适配版"][variant_index % 4]
    user_p = f"用户补充需求：{answers.user_prompt}。\n" if getattr(answers, "user_prompt", None) else ""
    if has_hand_image:
        return (
            "NAIL, strict image editing task, close-up manicure, salon quality, realistic nail art.\n"
            "这是一张严格图片编辑任务。第一张图片是用户的真实手部照片，它是唯一的画布。\n"
            "你只能修改指甲区域的色彩、图案、材质和装饰，必须严格保留：\n"
            "- 手型、手指长度和粗细\n"
            "- 手部姿势和角度\n"
            "- 肤色、光照、阴影\n"
            "- 背景和构图\n"
            "第二张图是灵感参考图，只提取其中的颜色、图案、材质和装饰信息，不要把参考图的手型或姿势带入。\n"
            f"方案方向：{variant_focus}。\n"
            f"使用场景：{answers.occasion}。\n"
            f"甲长：{answers.nail_length}。甲型：{answers.nail_shape}。\n"
            f"整体风格：{answers.style}。颜色：{colors}。装饰工艺：{decorations}。\n"
            f"预算：{answers.budget}。允许改动范围：{answers.change_policy}。\n"
            f"{user_p}"
            "要求：只改指甲，不改手；输出与第一张图尺寸和构图一致的手部近景；"
            "不要生成对比图、说明文字、水印、界面截图、价格标签或多余边框。"
        )
    return (
        "NAIL, close-up manicure design, salon quality, realistic nail art.\n"
        "你是 NailAI 的 DIY 悬赏美甲方案生成器。输入图片是用户上传的美甲/灵感参考图，"
        "不是用户手部试戴图。请结合参考图和以下选择题结果，生成一张可给美甲店执行的美甲方案图。\n"
        f"方案方向：{variant_focus}。\n"
        f"使用场景：{answers.occasion}。\n"
        f"甲长：{answers.nail_length}。甲型：{answers.nail_shape}。\n"
        f"整体风格：{answers.style}。颜色：{colors}。装饰工艺：{decorations}。\n"
        f"预算：{answers.budget}。允许改动范围：{answers.change_policy}。\n"
        f"{user_p}"
        "要求：生成完整美甲设计参考图，可以是手部近景或甲片方案展示，但必须专业、清晰、适合发布悬赏；"
        "保留参考图的核心颜色、图案和材质灵感，同时根据选择题调整甲长、甲型和复杂度；"
        "不要生成对比图、说明文字、水印、界面截图、价格标签或多余边框；"
        "画面应突出指甲设计本身，真实沙龙质感，高级但可执行。"
    )


def _extract_image_results(body: dict[str, Any]) -> list[str]:
    output = body.get("output")
    if isinstance(output, dict):
        choices = output.get("choices")
        if isinstance(choices, list):
            results: list[str] = []
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                content = choice.get("message", {}).get("content", [])
                if not isinstance(content, list):
                    continue
                for item in content:
                    if isinstance(item, dict) and isinstance(item.get("image"), str) and item["image"]:
                        results.append(item["image"])
            if results:
                return results

    images = body.get("images")
    if isinstance(images, list):
        return [item for item in images if isinstance(item, str) and item]

    results: list[str] = []
    data = body.get("data")
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                value = item.get("url") or item.get("image_url") or item.get("result_image_url")
                if isinstance(value, str) and value:
                    results.append(value)
                b64_value = item.get("b64_json") or item.get("image_base64")
                if isinstance(b64_value, str) and b64_value:
                    results.append(f"data:image/png;base64,{b64_value}")
    if results:
        return results

    return []


def _mock_diy_variant(
    reference_image_bytes: bytes,
    answers: DiyBountyAnswers,
    index: int,
    hand_image_bytes: bytes | None = None,
) -> str:
    if hand_image_bytes:
        try:
            # 1. Open hand image and resize
            hand_img = Image.open(BytesIO(hand_image_bytes))
            hand_img = ImageOps.exif_transpose(hand_img).convert("RGB")
            hand_img = ImageOps.fit(hand_img, (1024, 1024))
            
            # 2. Draw mock nails on the hand
            overlay = Image.new("RGBA", hand_img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            colors = answers.colors if answers.colors else ["#ff5c74", "#ffd8df", "#2b0d1b"]
            palette = []
            for c in colors:
                palette.append(c)
            if len(palette) < 3:
                palette += ["#ff5c74", "#ffd8df", "#2b0d1b"]
                
            for nail_index in range(5):
                x = 286 + nail_index * 112
                y = 430
                color = palette[(nail_index + index) % len(palette)]
                draw.rounded_rectangle((x - 25, y - 56, x + 25, y + 62), radius=20, fill=color, outline="#ffffff", width=3)
                draw.ellipse((x - 10, y - 38, x + 10, y - 18), fill="#ffffff44")
                
            overlay = overlay.filter(ImageFilter.GaussianBlur(0.3))
            combined = Image.alpha_composite(hand_img.convert("RGBA"), overlay).convert("RGB")
            
            # 3. Paste reference image inset in top-right
            try:
                ref_img = Image.open(BytesIO(reference_image_bytes))
                ref_img = ImageOps.exif_transpose(ref_img).convert("RGB")
                ref_img.thumbnail((240, 240))
                card = Image.new("RGB", (ref_img.width + 16, ref_img.height + 16), "#ffffff")
                card.paste(ref_img, (8, 8))
                combined.paste(card, (1024 - card.width - 24, 24))
            except Exception:
                pass
                
            buffer = BytesIO()
            combined.save(buffer, format="JPEG", quality=92)
            return f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode('ascii')}"
        except Exception:
            # Fallback to reference if hand fails
            pass

    # Reference-only design fallback
    image = Image.open(BytesIO(reference_image_bytes))
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((900, 900), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1024, 1024), "#fff7f9")
    fitted = ImageOps.pad(image, (620, 620), color="#fff7f9")
    canvas.paste(fitted, (202, 84))

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    palette = ["#ff5c74", "#ffd8df", "#2b0d1b", "#ffffff"]
    for nail_index in range(5):
        x = 230 + nail_index * 145
        y = 805
        color = palette[(nail_index + index) % len(palette)]
        draw.rounded_rectangle((x - 34, y - 105, x + 34, y + 58), radius=34, fill=color, outline="#ffffff", width=5)
        draw.ellipse((x - 14, y - 70, x + 14, y - 42), fill="#ffffff66")
    overlay = overlay.filter(ImageFilter.GaussianBlur(0.2))
    result = Image.alpha_composite(canvas.convert("RGBA"), overlay)
    buffer = BytesIO()
    result.convert("RGB").save(buffer, format="JPEG", quality=92)
    return f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode('ascii')}"


async def generate_diy_bounty_variants(
    reference_image_bytes: bytes,
    answers: DiyBountyAnswers,
    num_variants: int = 3,
    hand_image_bytes: bytes | None = None,
) -> tuple[str, list[DiyBountyVariant], dict[str, Any]]:
    import time
    t_start = time.perf_counter()
    
    has_hand = hand_image_bytes is not None and len(hand_image_bytes or b"") > 0
    endpoint = settings.qwen_image_api_url
    api_key = settings.qwen_image_api_key
    model = settings.qwen_image_model
    count = max(1, min(num_variants, 4))
    job_hash = hashlib.sha256(reference_image_bytes[:4096] + answers.model_dump_json().encode()).hexdigest()[:12]
    
    t_prompt_start = time.perf_counter()
    prompts = [build_diy_bounty_prompt(answers, index, has_hand_image=has_hand) for index in range(count)]
    prompt_ms = round((time.perf_counter() - t_prompt_start) * 1000, 1)

    t_normalize_start = time.perf_counter()
    if endpoint and api_key and not settings.enable_mock_ai:
        normalized_reference = _normalize_image_bytes(reference_image_bytes, max_side=1024, quality=90)
        reference_data_url = _ensure_data_url(normalized_reference)
        if has_hand:
            normalized_hand = _normalize_image_bytes(hand_image_bytes, max_side=1024, quality=90)
            hand_data_url = _ensure_data_url(normalized_hand)
    t_normalize_end = time.perf_counter()
    normalize_ms = round((t_normalize_end - t_normalize_start) * 1000, 1)

    t_generation_start = time.perf_counter()
    if not endpoint or not api_key or settings.enable_mock_ai:
        # Simulate slight network delay for realistic mock timing
        await asyncio.sleep(0.8)
        variants = [
            DiyBountyVariant(
                id=f"diy-{job_hash}-{index + 1}",
                image_url=_mock_diy_variant(reference_image_bytes, answers, index, hand_image_bytes=hand_image_bytes),
                title=["低调可做版", "保留参考图版", "加强设计版", "日常适配版"][index % 4],
                tags=[answers.occasion, answers.nail_length, answers.style],
                prompt=prompts[index],
            )
            for index in range(count)
        ]
        t_generation_end = time.perf_counter()
        generation_ms = round((t_generation_end - t_generation_start) * 1000, 1)
        total_ms = round((t_generation_end - t_start) * 1000, 1)
        
        return prompts[0], variants, {
            "mode": "mock-diy-bounty",
            "cache_key": job_hash,
            "timings_ms": {
                "prompt_build": prompt_ms,
                "reference_image_normalize": normalize_ms,
                "image_generation_api": generation_ms,
                "total": total_ms
            }
        }

    normalized_reference = _normalize_image_bytes(reference_image_bytes, max_side=1024, quality=90)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    reference_data_url = _ensure_data_url(normalized_reference)

    if has_hand:
        normalized_hand = _normalize_image_bytes(hand_image_bytes, max_side=1024, quality=90)
        hand_data_url = _ensure_data_url(normalized_hand)

    async def generate_variant(index: int) -> tuple[str, dict[str, Any]]:
        if has_hand:
            payload = {
                "model": model,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"image": hand_data_url},
                                {"image": reference_data_url},
                                {"text": prompts[index]}
                            ]
                        }
                    ]
                },
                "parameters": {
                    "size": "1024*1024",
                    "n": 1,
                    "watermark": False,
                    "prompt_extend": False
                }
            }
        else:
            content = [
                {"image": reference_data_url},
                {
                    "text": (
                        "输入图片是一张美甲或灵感参考图。请不要生成用户手部试戴图，"
                        "而是生成一张可用于 DIY 悬赏发布和美甲店报价的独立美甲方案参考图。\n"
                        f"{prompts[index]}"
                    )
                },
            ]
            payload = {
                "model": model,
                "input": {"messages": [{"role": "user", "content": content}]},
                "parameters": {
                    "size": "1024*1024",
                    "n": 1,
                    "watermark": False,
                    "prompt_extend": False,
                },
            }
        async with httpx.AsyncClient(timeout=settings.image2_timeout_seconds) as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            if response.status_code >= 400:
                detail = response.text[:400]
                raise ValueError(f"DashScope DIY request failed ({response.status_code}): {detail}")
            body = response.json()
        images = _extract_image_results(body)
        if not images:
            raise ValueError(body.get("message") or body.get("code") or "Qwen WAN did not return a DIY image")
        return images[0], body

    generated = await asyncio.gather(*(generate_variant(index) for index in range(count)))
    images = [image_url for image_url, _body in generated]
    provider_bodies = [body for _image_url, body in generated]
    
    t_generation_end = time.perf_counter()
    generation_ms = round((t_generation_end - t_generation_start) * 1000, 1)

    variants = [
        DiyBountyVariant(
            id=f"diy-{job_hash}-{index + 1}",
            image_url=image_url,
            title=["低调可做版", "保留参考图版", "加强设计版", "日常适配版"][index % 4],
            tags=[answers.occasion, answers.nail_length, answers.style],
            prompt=prompts[min(index, len(prompts) - 1)],
        )
        for index, image_url in enumerate(images[:count])
    ]

    total_ms = round((time.perf_counter() - t_start) * 1000, 1)

    return prompts[0], variants, {
        "mode": "qwen-wan-diy",
        "model": model,
        "cache_key": job_hash,
        "provider": provider_bodies,
        "timings_ms": {
            "prompt_build": prompt_ms,
            "reference_image_normalize": normalize_ms,
            "image_generation_api": generation_ms,
            "total": total_ms
        }
    }
