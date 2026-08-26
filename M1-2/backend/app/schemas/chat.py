from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=128)


class ChatResult(BaseModel):
    conversation_id: str
    answer: str
    tools_used: list[str]
