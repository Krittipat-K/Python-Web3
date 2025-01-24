from web3 import (
    Web3,
    AsyncWeb3,
    AsyncHTTPProvider
)
from web3.middleware import ExtraDataToPOAMiddleware

from hexbytes import HexBytes
import asyncio
from typing import (
    Any,)
from eth_typing import (
    ChecksumAddress,
    BlockIdentifier
)
from web3.contract.async_contract import (
    AsyncContract,
)
from web3.types import (
    TxParams,
    Wei,
    Nonce,
)
from eth_account.datastructures import (
    SignedTransaction,
)

from eth_account.signers.local import (
    LocalAccount,
)
from EVM.types import (
    TokenDetail,
    ChainDetail,
    RPCDetail,
    TxParamsInput
)


from EVM.constant import (
    CHAIN_DETAILS
    
)

def get_token_detail(token_symbol:str,
                     chain_id:str)->TokenDetail:
    chain_detail = CHAIN_DETAILS[chain_id]
    try:
        token_detail:dict[str,Any] = chain_detail['token_details'][token_symbol]
    except KeyError:
        raise ValueError(f"Token {token_symbol} not found in chain {chain_id} or not supported")
    
    return TokenDetail(
        symbol = token_detail['symbol'],
        address = Web3.to_checksum_address(token_detail['address']),
        decimal = token_detail['decimal'],
        unit_type = token_detail['unit_type'],
        created_block = token_detail['created_block']
    )
    
def get_chain_detail(chain_id:str)->ChainDetail:
    
    try:
        chain_detail:dict[str,Any] = CHAIN_DETAILS[chain_id]
    except KeyError:
        raise ValueError(f"Chain {chain_id} not found or not supported")
    
    token_details:dict[str,TokenDetail] = {}
    for token_symbol,token_detail in chain_detail['token_details'].items():
        token_details[token_symbol] = TokenDetail(
            symbol = token_detail['symbol'],
            address = Web3.to_checksum_address(token_detail['address']),
            decimal = token_detail['decimal'],
            unit_type = token_detail['unit_type'],
            created_block = token_detail['created_block']
        )
    
    address_map:dict[ChecksumAddress,str] = {}
    for address,alias in chain_detail['address_map'].items():
        address_map[Web3.to_checksum_address(address)] = alias
    
    return ChainDetail(
        native = chain_detail['native'],
        wrap_native = chain_detail['wrapNative'],
        wrap_native_address = Web3.to_checksum_address(chain_detail['wrapNativeAddress']),
        token_details = token_details,
        address_map = address_map
    )
    
def get_rpc_detail(rpc:str)->RPCDetail:
    
    try:
        rpc_detail:dict[str,Any] = CHAIN_DETAILS[rpc]
    except KeyError:
        raise ValueError(f"RPC {rpc} not found or not supported")
    
    chain_detail = get_chain_detail(rpc_detail['chain_id'])
    
    return RPCDetail(
        rpc = rpc_detail['rpc'],
        chain_id = int(rpc_detail['chain_id']),
        chain_detail = chain_detail
    )
    
class AsyncWeb3HTTP:
    
    def __init__(self,
                 rpc_detail:RPCDetail) -> None:
        self.w3 = AsyncWeb3(provider=AsyncHTTPProvider(rpc_detail.rpc))
        if rpc_detail.chain_id == 43114:
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0) # type: ignore
            
        self.chain_id = rpc_detail.chain_id
        self.native = rpc_detail.chain_detail.native
        self.wrap_native = rpc_detail.chain_detail.wrap_native
        self.wrap_native_address = rpc_detail.chain_detail.wrap_native_address
        self.token_details = rpc_detail.chain_detail.token_details
        self.address_map = rpc_detail.chain_detail.address_map
        pass
    
    def load_contract(self,abi:Any,address:ChecksumAddress) -> AsyncContract:
        return self.w3.eth.contract(abi=abi,address=address)
    
    async def async_get_balance_with_label(self,address:ChecksumAddress,block_identifier:BlockIdentifier='latest') -> tuple[ChecksumAddress,int]:
        balance = await self.w3.eth.get_balance(address,block_identifier)
        return address,balance
    
class AsyncWeb3HTTPWallet(AsyncWeb3HTTP):
    
    def __init__(self, 
                 rpc_detail: RPCDetail,
                 private_key:str) -> None:
        super().__init__(rpc_detail)
        self.__private_key = private_key
        account:LocalAccount = self.w3.eth.account.from_key(private_key)
        self.wallet_address:ChecksumAddress = account.address
        self.last_nonce:Nonce|None = None
        pass 
    async def async_get_base_fee(self,
                                 block_identifier:BlockIdentifier='pending')->Wei:
        block_data = await self.w3.eth.get_block(block_identifier)
        return block_data.get('baseFeePerGas', Wei(0))
    
    async def async_create_txn_params(self,
                          tx_params_input:TxParamsInput=TxParamsInput(),
                          max_fee_multiplier:float=2) -> TxParams:
        
        txn_params:TxParams = {'from':self.wallet_address,
                               'chainId':self.chain_id}
        
        if 'nonce' not in txn_params:
            if self.last_nonce is None:
                self.last_nonce = Nonce(0)
            nonce:Nonce = max(self.last_nonce,await self.w3.eth.get_transaction_count(self.wallet_address))
            txn_params['nonce'] = nonce
            
        return txn_params
    
    async def checking_txn_params(self,
                                  txn_params:TxParams,
                                  trick:float=1.5,
                                  priority_multipier:float=1) -> TxParams:
        
        if 'to' not in txn_params:
            raise ValueError("Destination address is required")
        
        priority = None
        max_priority_fee = 0
        if 'maxPriorityFeePerGas' not in txn_params:
            priority = asyncio.create_task(self.w3.eth.max_priority_fee)
        else:
            max_priority_fee = int(txn_params['maxPriorityFeePerGas'])
            
        base_fee = None
        if 'maxFeePerGas' not in txn_params:
            base_fee = asyncio.create_task(self.async_get_base_fee())
        
        gas = None
        if 'gas' not in txn_params:
            gas = asyncio.create_task(self.w3.eth.estimate_gas(txn_params))
        nonce = None
        if 'nonce' not in txn_params:
            if self.last_nonce is None:
                self.last_nonce = Nonce(0)
            nonce = asyncio.create_task(self.w3.eth.get_transaction_count(self.wallet_address))
            
        if 'from' not in txn_params:
            txn_params['from'] = self.wallet_address
            
        if 'chainId' not in txn_params:
            txn_params['chainId'] = self.chain_id
            
        if 'value' not in txn_params:
            txn_params['value'] = Wei(0)
            
        if priority is not None:
            max_priority_fee = int(await priority * priority_multipier)
            txn_params['maxPriorityFeePerGas'] = Wei(max_priority_fee)
            
        if base_fee is not None:
            max_fee_per_gas = await base_fee *2 + max_priority_fee
            txn_params['maxFeePerGas'] = Wei(max_fee_per_gas)
        
        if gas is not None:
            txn_params['gas'] = Wei(int(await gas * trick))
            
        if nonce is not None:
            if self.last_nonce is None:
                self.last_nonce = Nonce(0)
            txn_params['nonce'] = max(self.last_nonce,Nonce(await nonce))
            
        
        return txn_params
    
    async def async_send_transaction(self,
                                     txn_params:TxParams,
                                     trick:float=1.5,
                                     priority_multipier:float=1) -> HexBytes:
        txn_params = await self.checking_txn_params(txn_params,trick,priority_multipier)
        signed_txn:SignedTransaction = self.w3.eth.account.sign_transaction(txn_params,private_key=self.__private_key)
        txn_hash = await self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        
        return txn_hash
    
    async def async_transfer_native_token(self,
                                          to_address:ChecksumAddress,
                                          amount:int,
                                          tx_params_input:TxParamsInput=TxParamsInput())->HexBytes:
        
            tx_params_input = tx_params_input._replace(to=Web3.to_checksum_address(to_address))
            tx_params_input = tx_params_input._replace(value = Wei(amount))
            tx_params_input = tx_params_input._replace(chainId = self.chain_id)
            tx_params_input = tx_params_input._replace(gas = 21000)
            txx_params = await self.async_create_txn_params(tx_params_input)
            return await self.async_send_transaction(txx_params)