from pydantic import BaseModel, Field


class NailStyle(BaseModel):
    id: str
    name: str
    color: str
    finish: str
    occasion: list[str]
    tags: list[str]
    palette: list[str]
    prompt: str
    difficulty: str
    price_level: str
    image_url: str | None = None
    nail_length: str = "natural"
    taxonomy: dict[str, list[str]] = Field(default_factory=dict)
    stock_total: int | None = None
    stock_reserved: int | None = None
    is_active: bool = True


class TryOnResponse(BaseModel):
    job_id: str
    status: str
    channel: str
    style: NailStyle
    hand_confidence: float = Field(ge=0, le=1)
    quality_score: float = Field(ge=0, le=1)
    result_image_url: str
    mask_image_url: str | None = None
    nail_count: int | None = None
    nail_confidence: float | None = Field(default=None, ge=0, le=1)
    provider_payload: dict = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    selected_style_ids: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    intent: str
    recommended_styles: list[NailStyle]
    follow_up_questions: list[str]
    channel: str = "local-fallback"
    model: str | None = None


class DiyBountyAnswers(BaseModel):
    occasion: str
    nail_length: str
    nail_shape: str
    style: str
    colors: list[str] = Field(default_factory=list)
    decorations: list[str] = Field(default_factory=list)
    budget: str
    change_policy: str
    user_prompt: str = ""


class DiyBountyVariant(BaseModel):
    id: str
    image_url: str
    title: str
    tags: list[str]
    prompt: str


class DiyBountyGenerateResponse(BaseModel):
    job_id: str
    status: str
    channel: str
    prompt: str
    variants: list[DiyBountyVariant]
    provider_payload: dict = Field(default_factory=dict)


class DiyBountyPublishRequest(BaseModel):
    title: str
    description: str
    budget: str
    image: str
    answers: DiyBountyAnswers
    selected_variant_id: str


class DiyBountyPublishResponse(BaseModel):
    id: str
    title: str
    budget: str
    status: str
    image: str
    participants: int
    deadline: str
    description: str
    selected_variant_id: str
