import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas import ChatRequest, ChatResponse
from app.services.chat_recommender import recommend, stream_recommend

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return await recommend(request.message, request.selected_style_ids, request.history)


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        async for item in stream_recommend(request.message, request.selected_style_ids, request.history):
            yield f"event: {item['event']}\n"
            yield f"data: {json.dumps(item['data'], ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
