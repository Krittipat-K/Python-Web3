from typing import NamedTuple, Union,Sequence,NewType
from hexbytes import HexBytes
from eth_typing import (
    Address,
    ChecksumAddress,
    HexStr,
)
from web3.types import (
    Wei,
    Nonce,
)

class AccessListEntry(NamedTuple):
    address: HexStr
    storageKeys: Sequence[HexStr]


AddressLike = Union[Address, ChecksumAddress,str]
AccessList = NewType("AccessList", Sequence[AccessListEntry])

class TokenDetail(NamedTuple):
    symbol: str
    address: ChecksumAddress
    decimal: int
    unit_type: str
    created_block: int
    
class ChainDetail(NamedTuple):
    
    native:str
    wrap_native:str
    wrap_native_address:ChecksumAddress
    token_details:dict[str,TokenDetail]
    address_map:dict[ChecksumAddress,str] = {}
    
class RPCDetail(NamedTuple):
    rpc:str
    chain_id:int
    chain_detail:ChainDetail
    
class TxParamsInput(NamedTuple):
    accessList:AccessList|None = None
    blobVersionedHashes:Sequence[Union[str, HexStr, bytes, HexBytes]]|None = None
    chinId:int|None = None
    data:Union[bytes, HexStr]|None = None
    from_address:ChecksumAddress|None = None
    gas:int|None = None
    gasPrice:Wei|None = None
    maxFeePerBlobGas:Union[str, Wei]|None = None
    maxFeePerGas:Union[str, Wei]|None = None
    maxPriorityFeePerGas: Union[str, Wei]|None = None
    nonce: Nonce|None = None
    to:ChecksumAddress|None = None
    type:Union[int, HexStr]|None = None
    value:Wei|None = None
    
class BaseEventData(NamedTuple):
    address: ChecksumAddress
    block_hash: HexBytes
    block_number: int
    event: str
    log_index: int
    transaction_hash: HexBytes
    transaction_index: int
    
class ERC20TransferArgs(NamedTuple):
    from_address: ChecksumAddress
    to_address: ChecksumAddress
    value: int
    
class ERC20TransferEventData(BaseEventData):
    def __new__(cls, address: ChecksumAddress, block_hash: HexBytes, block_number: int, log_index: int, transaction_hash: HexBytes, transaction_index: int, args: ERC20TransferArgs) -> 'ERC20TransferEventData':
        return super().__new__(cls, address, block_hash, block_number, "Transfer", log_index, transaction_hash, transaction_index)
    
    def __init__(self, address: ChecksumAddress, block_hash: HexBytes, block_number: int, log_index: int, transaction_hash: HexBytes, transaction_index: int, args:ERC20TransferArgs) -> None:
        self.args = args
        
        
class UniswapV2GetReservesRespond(NamedTuple):
    reserve0: int
    reserve1: int
    ts: int
    
class UniswapV2ReservesReport(NamedTuple):
    underlying_reserve: int
    collateral_reserve: int
    ts: int
    
class UniswapV2SwapReport(NamedTuple):
    sender:ChecksumAddress
    to:ChecksumAddress
    action:str
    underlying_amount: int
    collateral_amount: int
    transaction_hash: HexBytes
    log_index: int
    block_number: int
    transaction_index: int
    
class UniswapV2SwapArgs(NamedTuple):
    sender:ChecksumAddress
    to:ChecksumAddress
    amount_0_in:int
    amount_1_in:int
    amount_0_out:int
    amount_1_out:int
    
class UniswapV2SwapEventData(BaseEventData):
    def __new__(cls, address: ChecksumAddress, block_hash: HexBytes, block_number: int, log_index: int, transaction_hash: HexBytes, transaction_index: int, args: UniswapV2SwapArgs) -> 'UniswapV2SwapEventData':
        return super().__new__(cls, address, block_hash, block_number, "Swap", log_index, transaction_hash, transaction_index)
    
    def __init__(self, address: ChecksumAddress, block_hash: HexBytes, block_number: int, log_index: int, transaction_hash: HexBytes, transaction_index: int, args:UniswapV2SwapArgs) -> None:
        self.args = args
        
class UniswapV3Slot0Respond(NamedTuple):
    sqrt_price_x96: int
    tick: int
    observation_index: int
    observation_cardinality: int
    observation_cardinality_next: int
    fee_protocol: int
    unlocked: bool
    
class UniswapV3SwapArgs(NamedTuple):
    sender: ChecksumAddress
    recipient: ChecksumAddress
    amount_0: int
    amount_1: int
    sqrt_price_x96:int
    liquidity: int
    tick:int
    
class UniswapV3SwapReport(NamedTuple):
    sender:ChecksumAddress
    recipient:ChecksumAddress
    action:str
    underlying_amount: int
    collateral_amount: int
    transaction_hash: HexBytes
    log_index: int
    block_number: int
    transaction_index: int
    
class UniswapV3SwapEventData(BaseEventData):
    def __new__(cls, address: ChecksumAddress, block_hash: HexBytes, block_number: int, log_index: int, transaction_hash: HexBytes, transaction_index: int, args: UniswapV3SwapArgs) -> 'UniswapV3SwapEventData':
        return super().__new__(cls, address, block_hash, block_number, "Swap", log_index, transaction_hash, transaction_index)
    
    def __init__(self, address: ChecksumAddress, block_hash: HexBytes, block_number: int, log_index: int, transaction_hash: HexBytes, transaction_index: int, args:UniswapV3SwapArgs) -> None:
        self.args = args
        
class UniswapV3QuoteExactInputSingleRespond(NamedTuple):
    amount_received: int
    sqrt_price_x96_after: int
    intialized_ticks_crossed: int
    gas_estimate: int
    
class UniswapV3QuoteExactOutputSingleRespond(NamedTuple):
    amount_in: int
    sqrt_price_x96_after: int
    intialized_ticks_crossed: int
    gas_estimate: int