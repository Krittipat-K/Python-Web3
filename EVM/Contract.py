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
    AsyncContractFunction,
    AsyncContractEvent
)
from web3.types import (
    TxParams,
    Wei,
    Nonce,
    
)
from web3.types import (
    EventData,
)

from EVM.types import (
    AddressLike,
    TxParamsInput,
    ERC20TransferEventData,
    ERC20TransferArgs
)

from EVM.Constant import (
    ERC20_ABI,
    FWX_MEMBERSHIP_ABI,
    FWX_MEMBERSHIP_ADDRESS_BASE,
    FWX_PERP_CORE_ABI,
    FWX_PERP_CORE_ADDRESS_BASE,
    FWX_PERP_HELPER_ABI,
    FWX_PERP_HELPER_ADDRESS_BASE,
    MAX_UINT,
    NATIVE_ADDRESS,
    UNISWAPV2_POOL_ABI,
    UNISWAPV2_ROUTERV2_ABI,
    UNISWAPV2_ROUTERV2_ADDRESS_BASE,
    UNISWAPV3_POOL_ABI,
    UNISWAPV3_QUOTER_ABI,
    UNISWAPV3_QUOTER_ADDRESS_BASE,
    UNISWAPV3_ROUTERV2_ABI,
    UNISWAPV3_ROUTERV2_ADDRESS_BASE
    
)

from EVM.W3 import (
    AsyncWeb3HTTP,
    AsyncWeb3HTTPWallet
)
from EVM.types import RPCDetail

class AsyncERC20ContractBase(AsyncWeb3HTTP):
    
    def __init__(self, 
                 rpc_detail: RPCDetail,
                 address:AddressLike) -> None:
        super().__init__(rpc_detail)
        self.address = Web3.to_checksum_address(address)
        self.contract = self.load_contract(ERC20_ABI,self.address)
        
    # Call function Section
    
    def balanceOf(self,address:ChecksumAddress) -> AsyncContractFunction:
        
        return self.contract.functions.balanceOf(address)
    
    def allowance(self,owner:ChecksumAddress,spender:ChecksumAddress) -> AsyncContractFunction:
        
        return self.contract.functions.allowance(owner,spender)
    
    def name(self) -> AsyncContractFunction:
        
        return self.contract.functions.name()
    
    def totalSupply(self) -> AsyncContractFunction:
        
        return self.contract.functions.totalSupply()
    
    def symbol(self) -> AsyncContractFunction:
        
        return self.contract.functions.symbol()
    
    def decimals(self) -> AsyncContractFunction:
        
        return self.contract.functions.decimals()
    
    # Transaction Section
    
    def approve(self,spender:ChecksumAddress,amount:int) -> AsyncContractFunction:
        
        return self.contract.functions.approve(spender,amount)
    
    def transfer(self,to:ChecksumAddress,amount:int) -> AsyncContractFunction:
        
        return self.contract.functions.transfer(to,amount)
    
    def transferFrom(self,from_address:ChecksumAddress,to:ChecksumAddress,amount:int) -> AsyncContractFunction:
        
        return self.contract.functions.transferFrom(from_address,to,amount)
    
    def eventTransfer(self) -> AsyncContractEvent:
        
        return self.contract.events.Transfer()
    
class AsyncERC20Contract(AsyncERC20ContractBase):
    
    def __init__(self, rpc_detail: RPCDetail, address: AddressLike) -> None:
        super().__init__(rpc_detail, address)
        self.token_symbol = rpc_detail.chain_detail.address_map[self.address]
        self.decimal = rpc_detail.chain_detail.token_details[self.token_symbol].decimal
        self.unit_type = rpc_detail.chain_detail.token_details[self.token_symbol].unit_type
        self.created_block = rpc_detail.chain_detail.token_details[self.token_symbol].created_block
        
    def process_transfer_event_log(self,event_log:EventData) -> ERC20TransferEventData:
        
        base_event_data,arg = self.process_event_data(event_log)
        sender = Web3.to_checksum_address(arg['from'])
        receiver = Web3.to_checksum_address(arg['to'])
        value = int(arg['value'])
        transfer_args = ERC20TransferArgs(sender,receiver,value)
        return ERC20TransferEventData(address=base_event_data.address,
                                       block_hash=base_event_data.block_hash,
                                       block_number=base_event_data.block_number,
                                       transaction_hash=base_event_data.transaction_hash,
                                       log_index=base_event_data.log_index,
                                       transaction_index=base_event_data.transaction_index,
                                       args=transfer_args)
    
    async def get_balance_of(self,address:ChecksumAddress,block_identifier:BlockIdentifier='latest') -> Wei:
        
        return await self.balanceOf(address).call(block_identifier=block_identifier)
    
    async def async_get_balance_of_with_label(self,address:ChecksumAddress,block_identifier:BlockIdentifier='latest') -> tuple[ChecksumAddress,Wei]:
        
        return address,await self.get_balance_of(address,block_identifier)
    
    async def async_get_allowance(self,owner:ChecksumAddress,spender:ChecksumAddress,block_identifier:BlockIdentifier='latest') -> Wei:
        
        return await self.allowance(owner,spender).call(block_identifier=block_identifier)
    
    async def async_checking_approve_ERC20(self,
                                        wallet:AsyncWeb3HTTPWallet,
                                        spender:ChecksumAddress,
                                        amount:int=MAX_UINT,
                                        tx_params_input:TxParamsInput=TxParamsInput(),
                                        waiting_txn:bool=True,
                                        time_out:float =120,
                                        pull_latency:float=0.5) -> int:
        
        owner = wallet.wallet_address
        allowance:int = int(await self.async_get_allowance(owner,spender))
        
        if allowance < amount:
            print(f'Approve {amount} to {spender} from {owner}')
            func = self.approve(spender,amount)
            txn_params = await wallet.async_create_txn_params(tx_params_input,)
            txn_params = await func.build_transaction(txn_params)
            txn_hash:HexBytes = await wallet.async_send_transaction(txn_params)
            if waiting_txn:
                await self.w3.eth.wait_for_transaction_receipt(txn_hash,timeout=time_out,poll_latency=pull_latency)
                
            return amount
        
        else:
            return allowance
    
                
                