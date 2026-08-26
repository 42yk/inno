from fastapi import Request

from app.services.data_service import DataService
from app.services.summary_service import SummaryService


def get_data_service(request: Request) -> DataService:
    return request.app.state.data_service


def get_summary_service(request: Request) -> SummaryService:
    return request.app.state.summary_service
