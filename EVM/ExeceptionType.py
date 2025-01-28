from typing import (
    Optional
)


class InsufficientBalanceForSwap(Exception):
    """Raised when the account has insufficient balance for a transaction."""

    def __init__(self, had: int, needed: int,token:Optional[str]=None) -> None:
        if token:
            Exception.__init__(self, f"Insufficient balance for {token}. Had {had} WEI, needed {needed} WEI")
        else:
            Exception.__init__(self, f"Insufficient balance. Had {had} WEI, needed {needed} WEI")
            
class OutOfBallanceForAllWallet(Exception):
    """Raised when all wallet has insufficient balance for a transaction."""
    def __init__(self) -> None:
        Exception.__init__(self, f"All wallet has insufficient balance for a transaction")