from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmptyArguments(ToolArguments):
    pass


class DateArguments(ToolArguments):
    date: date


class PeriodArguments(ToolArguments):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_period(self) -> "PeriodArguments":
        if self.start_date > self.end_date:
            raise ValueError("start_date must not exceed end_date")
        return self
