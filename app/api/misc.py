from fastapi import APIRouter, Depends

from app.utils.audit_logger import get_audit_logger
from app.services.product_service import get_product_service
from app.services.payment_service import get_payment_service
from app.services.fraud_service import init_fraud_service, get_flags

router = APIRouter(prefix="/api/v1", tags=["misc"])


@router.get("/logs")
def view_logs():
    return get_audit_logger().all()


@router.get("/inventory/low-stock")
def low_stock(threshold: int = 5):
    svc = get_product_service()
    # product service now exposes `list_products()` and `stock` on records
    return [p for p in svc.list_products() if p.stock <= threshold]


@router.post("/simulate/failure")
def simulate_failure(enable: bool = True):
    ps = get_payment_service()
    ps.set_failure_mode(enable)
    return {"failure_mode": enable}


@router.get("/fraud/flags")
def fraud_flags():
    init_fraud_service()
    return get_flags()
