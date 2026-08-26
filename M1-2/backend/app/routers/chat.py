from fastapi import APIRouter, Depends

from app.dependencies import get_chat_service
from app.schemas.chat import ChatRequest, ChatResult
from app.services.chat_service import ChatService


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResult)
def chat(
    payload: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResult:
    return service.chat(payload)
