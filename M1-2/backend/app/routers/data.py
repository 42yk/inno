from datetime import date

from fastapi import APIRouter, Depends, Response, status

from app.dependencies import get_data_service, get_summary_service
from app.schemas.data import (
    DataCreate,
    DataListResponse,
    DataRecord,
    DataSummary,
    DataUpdate,
)
from app.services.data_service import DataService
from app.services.summary_service import SummaryService


router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/summary", response_model=DataSummary)
def get_summary(
    service: SummaryService = Depends(get_summary_service),
) -> DataSummary:
    return service.get_summary()


@router.post("", response_model=DataRecord, status_code=status.HTTP_201_CREATED)
def create_record(
    payload: DataCreate,
    service: DataService = Depends(get_data_service),
) -> DataRecord:
    return service.create_record(payload)


@router.get("", response_model=DataListResponse)
def list_records(
    start_date: date | None = None,
    end_date: date | None = None,
    service: DataService = Depends(get_data_service),
) -> DataListResponse:
    records = service.list_records(
        start_date=start_date,
        end_date=end_date,
        descending=True,
    )
    return DataListResponse(items=records, count=len(records))


@router.put("/{record_id}", response_model=DataRecord)
def update_record(
    record_id: str,
    payload: DataUpdate,
    service: DataService = Depends(get_data_service),
) -> DataRecord:
    return service.update_record(record_id, payload)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    record_id: str,
    service: DataService = Depends(get_data_service),
) -> Response:
    service.delete_record(record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
