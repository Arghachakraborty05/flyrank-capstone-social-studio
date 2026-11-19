from datetime import datetime
from pydantic import BaseModel, Field, model_validator


class PostIngestRequest(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    markdown_content: str | None = Field(default=None)
    source_url: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_source(self) -> "PostIngestRequest":
        has_md = bool(self.markdown_content and self.markdown_content.strip())
        has_url = bool(self.source_url and self.source_url.strip())
        if not has_md and not has_url:
            raise ValueError("Provide either markdown_content or source_url.")
        return self


class GenerateVariantsRequest(BaseModel):
    platforms: list[str] = Field(default=["telegram", "mock_x"], min_length=2)


class ValidateCandidateRequest(BaseModel):
    platform: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)


class VariantRead(BaseModel):
    id: int
    post_id: int
    platform: str
    content: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PostRead(BaseModel):
    id: int
    source_type: str
    source_url: str | None = None
    title: str | None = None
    content: str
    created_at: datetime
    variants: list[VariantRead] = []

    model_config = {"from_attributes": True}