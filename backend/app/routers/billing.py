from fastapi import APIRouter, HTTPException

from app.schemas.billing import BillRequest, CompareRequest, DualRequest
from app.services.billing_service import BillingService, DualInputError

router = APIRouter(tags=["billing"])


@router.post("/bill")
def post_bill(body: BillRequest):
    with BillingService() as svc:
        return svc.run_bill(body.kwh, body.peak, body.account_id, body.persist)


@router.post("/compare")
def post_compare(body: CompareRequest):
    with BillingService() as svc:
        return svc.run_compare(body.kwh, body.persist)


@router.post("/dual")
def post_dual(body: DualRequest):
    with BillingService() as svc:
        try:
            return svc.run_dual(body.left, body.right, body.persist)
        except DualInputError as e:
            raise HTTPException(e.status_code, e.detail)
