from pydantic import BaseModel, Field


class BillRequest(BaseModel):
    account_id: int | None = None
    kwh: float = Field(ge=0)
    peak: bool = False
    persist: bool = True


class CompareRequest(BaseModel):
    kwh: float = Field(ge=0)
    persist: bool = False


class DualSide(BaseModel):
    # kwh validated in the service so the error can name the failing side
    account_id: int
    kwh: float
    peak: bool = False


class DualRequest(BaseModel):
    left: DualSide
    right: DualSide
    persist: bool = False


class CalcRunOut(BaseModel):
    id: int
    kind: str
    account_id: int | None
    input_json: str
    result_json: str
    created_at: str
