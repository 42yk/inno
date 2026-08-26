from fastapi import Request

from app.services.data_service import DataService
from app.services.conversation_service import ConversationService
from app.services.chat_service import ChatService
from app.services.summary_service import SummaryService


def get_data_service(request: Request) -> DataService:
    return request.app.state.data_service


def get_summary_service(request: Request) -> SummaryService:
    return request.app.state.summary_service


def get_conversation_service(request: Request) -> ConversationService:
    return request.app.state.conversation_service


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service
