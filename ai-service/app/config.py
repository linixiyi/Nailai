from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    image2_provider: str = "generic"
    image2_api_url: str | None = None
    image2_api_key: str | None = None
    image2_model: str = "wan2.7-image-pro"
    qwen_fast_model: str = "wan2.7-image-pro"
    qwen_image_api_url: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    qwen_image_api_key: str | None = None
    qwen_image_model: str = "wan2.7-image-pro"
    qwen_chat_api_url: str | None = None
    qwen_chat_api_key: str | None = None
    qwen_chat_model: str = "qwen-plus"
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: str | None = None
    openai_compatible_model: str = "gpt-image-2"
    gpt_image2_api_url: str | None = None
    gpt_image2_api_key: str | None = None
    gpt_image2_model: str = "gpt-image-2"
    doubao_image_api_url: str = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    doubao_image_api_key: str | None = None
    doubao_image_model: str = "doubao-seedream-5-0-260128"
    flux_kontext_async_url: str = "https://api.jiekou.ai/v3/async/flux-1-kontext-dev"
    async_task_result_url: str = "https://api.jiekou.ai/v3/async/task-result"
    image2_timeout_seconds: float = 45.0
    chat_timeout_seconds: float = 25.0
    enable_mock_ai: bool = True
    cors_origins: str = "http://localhost:3003,http://127.0.0.1:3003"
    nail_segmentation_model_path: str = "models/nails_seg_s_yolov8_v1.pt"
    nail_segmentation_min_confidence: float = 0.25
    nail_segmentation_enabled: bool = True
    nail_try_on_min_nails: int = 3
    nail_try_on_min_nail_confidence: float = 0.35
    vision_analyzer_enabled: bool = False
    vision_analyzer_provider: str = "qwen_vl"
    vision_analyzer_api_url: str | None = None
    vision_analyzer_api_key: str | None = None
    vision_analyzer_model: str = "qwen3-vl-flash"
    supabase_url: str | None = None
    next_public_supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_anon_key: str | None = None
    next_public_supabase_anon_key: str | None = None
    style_catalog_cache_seconds: float = 30.0
    test_dashboard_password: str | None = None

    model_config = SettingsConfigDict(env_file=(".env", ".env.local"), env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
