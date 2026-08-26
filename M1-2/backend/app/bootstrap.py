from dataclasses import dataclass

from app.clients.openai_client import OpenAIClient
from app.config import Settings
from app.firebase import create_firestore_client
from app.repositories.conversation_repository import (
    FirestoreConversationRepository,
)
from app.repositories.data_repository import FirestoreDataRepository
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.data_service import DataService
from app.services.summary_service import SummaryService
from app.services.tool_service import ToolService


@dataclass(frozen=True)
class Services:
    data: DataService
    summary: SummaryService
    conversations: ConversationService
    chat: ChatService


def build_services(settings: Settings) -> Services:
    firestore_client = create_firestore_client(
        settings.firebase_service_account_json
    )
    data_service = DataService(FirestoreDataRepository(firestore_client))
    summary_service = SummaryService(data_service)
    conversation_service = ConversationService(
        FirestoreConversationRepository(firestore_client)
    )
    tool_service = ToolService(data_service, summary_service)
    ai_client = OpenAIClient(
        settings.openai_api_key,
        settings.openai_model,
        settings.openai_max_output_tokens,
    )
    chat_service = ChatService(
        ai_client=ai_client,
        summary_service=summary_service,
        tool_service=tool_service,
        conversation_service=conversation_service,
        max_tool_calls=settings.max_tool_calls,
    )
    return Services(
        data=data_service,
        summary=summary_service,
        conversations=conversation_service,
        chat=chat_service,
    )
