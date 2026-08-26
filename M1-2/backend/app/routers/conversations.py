from fastapi import APIRouter, Depends, Response, status

from app.dependencies import get_conversation_service
from app.schemas.conversations import (
    Conversation,
    ConversationCreate,
    ConversationListResponse,
)
from app.services.conversation_service import ConversationService


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=Conversation, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    service: ConversationService = Depends(get_conversation_service),
) -> Conversation:
    return service.create(payload)


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationListResponse:
    items = service.list()
    return ConversationListResponse(items=items, count=len(items))


@router.get("/{conversation_id}", response_model=Conversation)
def get_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service),
) -> Conversation:
    return service.get(conversation_id)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service),
) -> Response:
    service.delete(conversation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
