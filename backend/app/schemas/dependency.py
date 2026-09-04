from pydantic import BaseModel, model_validator

from app.models.enums import DependencyType, SchedulableType


class DependencyCreate(BaseModel):
    predecessor_type: SchedulableType
    predecessor_id: int
    successor_type: SchedulableType
    successor_id: int
    dependency_type: DependencyType = DependencyType.FINISH_TO_START
    lag_days: int = 0

    @model_validator(mode="after")
    def validate_not_self_referential(self) -> "DependencyCreate":
        if (
            self.predecessor_type == self.successor_type
            and self.predecessor_id == self.successor_id
        ):
            raise ValueError("An item cannot depend on itself")
        return self


class DependencyRead(BaseModel):
    id: int
    predecessor_type: SchedulableType
    predecessor_id: int
    predecessor_label: str
    successor_type: SchedulableType
    successor_id: int
    successor_label: str
    dependency_type: DependencyType
    lag_days: int
