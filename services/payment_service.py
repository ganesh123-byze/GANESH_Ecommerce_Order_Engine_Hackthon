import random
import time
from utils.logger import get_logger

# By default payments succeed deterministically; use `set_failure_mode(True)` to simulate failures.


class PaymentService:
    def __init__(self):
        self.logger = get_logger()
        self.failure_mode = False

    def charge(self, user_id: str, amount: float) -> bool:
        """Simulate payment. May randomly fail or always fail if failure_mode on."""
        # simulate latency
        time.sleep(0.2)
        if self.failure_mode:
            self.logger.log(f"PAYMENT_INJECT_FAIL user={user_id} amt={amount}")
            return False
        # deterministic success by default
        ok = True
        self.logger.log(f"PAYMENT_ATTEMPT user={user_id} amt={amount} ok={ok}")
        return ok

    def set_failure_mode(self, val: bool):
        self.failure_mode = val
