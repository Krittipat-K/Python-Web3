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
    RPCDetail,
    AddressLike,
    TxParamsInput,
    ERC20TransferEventData,
    ERC20TransferArgs,
    UniswapV2GetReservesRespond,
    UniswapV2ReservesReport,
    UniswapV2SwapReport,
    UniswapV2SwapArgs,
    UniswapV2SwapEventData,
    UniswapV3Slot0Respond,
    UniswapV3SwapArgs,
    UniswapV3SwapReport,
    UniswapV3SwapEventData,
    UniswapV3QuoteExactInputSingleRespond,
    UniswapV3QuoteExactOutputSingleRespond,
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
        try:
            self.token_symbol = rpc_detail.chain_detail.address_map[self.address]
            self.decimal = rpc_detail.chain_detail.token_details[self.token_symbol].decimal
            self.unit_type = rpc_detail.chain_detail.token_details[self.token_symbol].unit_type
            self.created_block = rpc_detail.chain_detail.token_details[self.token_symbol].created_block
        except:
            self.token_symbol =  asyncio.run(self.symbol().call())
            self.decimal = asyncio.run(self.decimals().call())
            if self.decimal == 18:
                self.unit_type = 'ether'
            elif self.decimal == 9:
                self.unit_type = 'gwei'
            else:
                raise ValueError('Decimal is not 9 or 18')
            self.created_block = 0
        
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
        
class AsyncUniswapV2PoolContractBase(AsyncWeb3HTTP):
    
    def __init__(self,
                 rpc_detail: RPCDetail,
                 address:AddressLike) -> None:
        super().__init__(rpc_detail)
        self.address = Web3.to_checksum_address(address)
        self.contract = self.load_contract(UNISWAPV2_POOL_ABI,self.address)
        
    # Call function Section
    
    def getReserves(self) -> AsyncContractFunction:
        
        return self.contract.functions.getReserves()
    
    def token0(self) -> AsyncContractFunction:
        
        return self.contract.functions.token0()
    
    def token1(self) -> AsyncContractFunction:
        
        return self.contract.functions.token1()
    
    def factory(self) -> AsyncContractFunction:
        
        return self.contract.functions.factory()
    
    def kLast(self) -> AsyncContractFunction:
        
        return self.contract.functions.kLast()
    
    def mint(self,to:ChecksumAddress) -> AsyncContractFunction:
        
        return self.contract.functions.mint(to)
    
    def burn(self,to:ChecksumAddress) -> AsyncContractFunction:
        
        return self.contract.functions.burn(to)
    
    def swap(self,amount0Out:int,amount1Out:int,to:ChecksumAddress,data:bytes) -> AsyncContractFunction:
        
        return self.contract.functions.swap(amount0Out,amount1Out,to,data)
    
    def skim(self,to:ChecksumAddress) -> AsyncContractFunction:
        
        return self.contract.functions.skim(to)
    
    def sync(self) -> AsyncContractFunction:
        
        return self.contract.functions.sync()
    
    # Transaction Section
    
    def initialize(self,token0:ChecksumAddress,token1:ChecksumAddress) -> AsyncContractFunction:
        
        return self.contract.functions.initialize(token0,token1)
    
    def setFee(self,fee:int) -> AsyncContractFunction:
        
        return self.contract.functions.setFee(fee)
    
    def setKLast(self,kLast:int) -> AsyncContractFunction:
        
        return self.contract.functions.setKLast(kLast)
    
    # Event Section
    
    def eventMint(self) -> AsyncContractEvent:
        
        return self.contract.events.Mint()
    
    def eventBurn(self) -> AsyncContractEvent:
        
        return self.contract.events.Burn()
    
    def eventSwap(self) -> AsyncContractEvent:
        
        return self.contract.events.Swap()
    
    def eventSync(self) -> AsyncContractEvent:
        
        return self.contract.events.Sync()
    
    
class AsyncUniswapV2PoolContract(AsyncUniswapV2PoolContractBase):
    
    def __init__(self, 
                 rpc_detail: RPCDetail, 
                 pool_address:AddressLike,
                 underlying_address:ChecksumAddress,
                 collateral_address:ChecksumAddress) -> None:
        super().__init__(rpc_detail, pool_address)
        self.underlying = AsyncERC20Contract(rpc_detail,underlying_address)
        self.collateral = AsyncERC20Contract(rpc_detail,collateral_address)
        token0 = asyncio.run(self.async_get_token_0_address())
        
        if token0 == underlying_address:
            self.is_underlying_token0 = True
        else:
            self.is_underlying_token0 = False
        pass 
    
    async def async_get_token_0_address(self) -> ChecksumAddress:
        
        return Web3.to_checksum_address(await self.token0().call())
    
    async def async_get_token_1_address(self) -> ChecksumAddress:
        
        return Web3.to_checksum_address(await self.token1().call())
    
    async def async_get_raw_reserves(self) -> UniswapV2GetReservesRespond:
        
        reserves = await self.getReserves().call()
        return UniswapV2GetReservesRespond(reserves[0],reserves[1],reserves[2])
    
    def get_reserves_report(self,respond:UniswapV2GetReservesRespond) -> UniswapV2ReservesReport:
        
        if self.is_underlying_token0:
            underlying_reserve = Web3.from_wei(respond.reserve0,self.underlying.unit_type)
            collateral_reserve = Web3.from_wei(respond.reserve1,self.collateral.unit_type)
            
        else:
            underlying_reserve = Web3.from_wei(respond.reserve1,self.underlying.unit_type)
            collateral_reserve = Web3.from_wei(respond.reserve0,self.collateral.unit_type)
            
        return UniswapV2ReservesReport(int(underlying_reserve),int(collateral_reserve),respond.ts) 
    
    def calculate_price(self,reserves:UniswapV2ReservesReport) -> float:
        
        return reserves.collateral_reserve/reserves.underlying_reserve
    
    async def async_get_price(self) -> float:
        
        return self.calculate_price(self.get_reserves_report(await self.async_get_raw_reserves()))
    
    def get_process_swap_event_log(self,event_log:EventData) -> UniswapV2SwapEventData:
        
        base_event_data,arg = self.process_event_data(event_log)
        sender = Web3.to_checksum_address(arg['sender'])
        to = Web3.to_checksum_address(arg['to'])
        amount_0_in = int(arg['amount0In'])
        amount_1_in = int(arg['amount1In'])
        amount_0_out = int(arg['amount0Out'])
        amount_1_out = int(arg['amount1Out'])
        
        args = UniswapV2SwapArgs(sender,to,amount_0_in,amount_1_in,amount_0_out,amount_1_out)
        
        return UniswapV2SwapEventData(address=base_event_data.address,
                                        block_hash=base_event_data.block_hash,
                                        block_number=base_event_data.block_number,
                                        transaction_hash=base_event_data.transaction_hash,
                                        log_index=base_event_data.log_index,
                                        transaction_index=base_event_data.transaction_index,
                                        args=args)
    def get_swap_report(self,swap_event_data:UniswapV2SwapEventData) -> UniswapV2SwapReport:
        
        if self.is_underlying_token0: # token0 is underlying token
            if swap_event_data.args.amount_0_in >0:
                action = 'Sell'
                underlying_amount = swap_event_data.args.amount_0_in
                collateral_amount = swap_event_data.args.amount_1_out
                
            else:
                action = 'Buy'
                underlying_amount = swap_event_data.args.amount_0_out
                collateral_amount = swap_event_data.args.amount_1_in
                
        else: # token1 is underlying token
            if swap_event_data.args.amount_1_in >0:
                action = 'Sell'
                underlying_amount = swap_event_data.args.amount_1_in
                collateral_amount = swap_event_data.args.amount_0_out
                
            else:
                action = 'Buy'
                underlying_amount = swap_event_data.args.amount_1_out
                collateral_amount = swap_event_data.args.amount_0_in
        
        
        return UniswapV2SwapReport(sender=swap_event_data.args.sender,
                                    to=swap_event_data.args.to,
                                    action=action,
                                    underlying_amount=underlying_amount,
                                    collateral_amount=collateral_amount,
                                    transaction_hash=swap_event_data.transaction_hash,
                                    log_index=swap_event_data.log_index,
                                    block_number=swap_event_data.block_number,
                                    transaction_index=swap_event_data.transaction_index)
    
class AsyncUniswapV3ContractBase(AsyncWeb3HTTP):
    
    def __init__(self,
                 rpc_detail: RPCDetail,
                 address:AddressLike) -> None:
        super().__init__(rpc_detail)
        self.address = Web3.to_checksum_address(address)
        self.contract = self.load_contract(UNISWAPV3_POOL_ABI,self.address)
        
    # Call function Section
    def factory(self) -> AsyncContractFunction:
        
        return self.contract.functions.factory()
    
    def fee(self) -> AsyncContractFunction:
        
        return self.contract.functions.fee()
    
    def feeGrowthGlobal0X128(self) -> AsyncContractFunction:
        
        return self.contract.functions.feeGrowthGlobal0X128()
    
    def feeGrowthGlobal1X128(self) -> AsyncContractFunction:
        
        return self.contract.functions.feeGrowthGlobal1X128()
    
    def liquidity(self) -> AsyncContractFunction:
        
        return self.contract.functions.liquidity()
    
    def maxLiquidityPerTick(self) -> AsyncContractFunction:
        
        return self.contract.functions.maxLiquidityPerTick()
    
    def observations(self,observation_index:int) -> AsyncContractFunction:
        
        return self.contract.functions.observations(observation_index)
    
    def observe(self,seconds_agos:int) -> AsyncContractFunction:
        
        return self.contract.functions.observe(seconds_agos)
    
    def positions(self,position_key:int) -> AsyncContractFunction:
        
        return self.contract.functions.positions(position_key)
    
    def protocolFees(self) -> AsyncContractFunction:
        
        return self.contract.functions.protocolFees()
    
    def slot0(self) -> AsyncContractFunction:
        
        return self.contract.functions.slot0()
    
    def snapshotCumulativesInside(self,tick_lower:int,tick_upper:int  ) -> AsyncContractFunction:
        
        return self.contract.functions.snapshotCumulativesInside(tick_lower,tick_upper)
    
    def tickBitmap(self,tick:int) -> AsyncContractFunction:
        
        return self.contract.functions.tickBitmap(tick)
    
    def tickSpacing(self) -> AsyncContractFunction:
        
        return self.contract.functions.tickSpacing()
    
    def ticks(self,tick:int) -> AsyncContractFunction:
        
        return self.contract.functions.ticks(tick)
    
    def token0(self) -> AsyncContractFunction:
        
        return self.contract.functions.token0()
    
    def token1(self) -> AsyncContractFunction:
        
        return self.contract.functions.token1()
    
    # transaction Section
    
    def burn(self,tick_lower:int,tick_upper:int,amount:int) -> AsyncContractFunction:
        
        return self.contract.functions.burn(tick_lower,tick_upper,amount)
    
    def collect(self,recipient:ChecksumAddress,tick_lower:int,tick_upper:int,amount_0_requested:int,amount_1_requested:int) -> AsyncContractFunction:
        
        return self.contract.functions.collect(recipient,tick_lower,tick_upper,amount_0_requested,amount_1_requested)
    
    def collectProtocol(self,recipient:ChecksumAddress,amount_0_requested:int,amount_1_requested:int) -> AsyncContractFunction:
        
        return self.contract.functions.collectProtocol(recipient,amount_0_requested,amount_1_requested)
    
    def flash(self,recipient:ChecksumAddress,amount_0:int,amount_1:int,data:bytes) -> AsyncContractFunction:
        
        return self.contract.functions.flash(recipient,amount_0,amount_1,data)
    
    def increaseObservationCardinalityNext(self,observation_cardinality_next:int) -> AsyncContractFunction:
        
        return self.contract.functions.increaseObservationCardinalityNext(observation_cardinality_next)
    
    def initialize(self,sqrt_price_X9:int) -> AsyncContractFunction:
        
        return self.contract.functions.initialize(sqrt_price_X9)
    
        
    def mint(self,recipient:ChecksumAddress,amount_0:int,amount_1:int,amount:int,data:bytes) -> AsyncContractFunction:
        return self.contract.functions.mint(recipient,amount_0,amount_1,amount,data)
    
    def setFeeProtocol(self,fee_protocol_0:int,fee_protocol_1:int) -> AsyncContractFunction:
        
        return self.contract.functions.setFeeProtocol(fee_protocol_0,fee_protocol_1)
    
    def swap(self,recipient:ChecksumAddress,zero_for_one:bool,amount_specified:int,sqrt_price_limit_X96 :int,data :int) -> AsyncContractFunction:
        
        return self.contract.functions.swap(recipient,zero_for_one,amount_specified,sqrt_price_limit_X96,data)
            
    # Event Section
    
    def eventBurn(self) -> AsyncContractEvent:
        
        return self.contract.events.Burn()
    
    def eventCollect(self) -> AsyncContractEvent:
        
        return self.contract.events.Collect()
    
    def eventCollectProtocol(self) -> AsyncContractEvent:
        
        return self.contract.events.CollectProtocol()
    
    def eventFlash(self) -> AsyncContractEvent:
        
        return self.contract.events.Flash()
    
    def eventInitialize(self) -> AsyncContractEvent:
        
        return self.contract.events.Initialize()
    
    def eventMint(self) -> AsyncContractEvent:
        
        return self.contract.events.Mint()
    
    def eventSwap(self) -> AsyncContractEvent:
        
        return self.contract.events.Swap()
    
    def eventSync(self) -> AsyncContractEvent:
        
        return self.contract.events.Sync()
    
class AsyncUniswapV3PoolContract(AsyncUniswapV3ContractBase):
    
    def __init__(self, 
                 rpc_detail: RPCDetail, 
                 pool_address:AddressLike,
                 underlying_address:ChecksumAddress,
                 collateral_address:ChecksumAddress) -> None:
        super().__init__(rpc_detail, pool_address)
        self.underlying = AsyncERC20Contract(rpc_detail,underlying_address)
        self.collateral = AsyncERC20Contract(rpc_detail,collateral_address)
        token0 = asyncio.run(self.async_get_token_0_address())
        
        if token0 == underlying_address:
            self.is_underlying_token0 = True
        else:
            self.is_underlying_token0 = False
        pass 
    
    async def async_get_token_0_address(self) -> ChecksumAddress:
        
        return Web3.to_checksum_address(await self.token0().call())
    
    async def async_get_token_1_address(self) -> ChecksumAddress:
        
        return Web3.to_checksum_address(await self.token1().call())
    
    async def async_get_slot0(self,bloack_identifier:BlockIdentifier='latest') -> UniswapV3Slot0Respond:
        
        slot0 = await self.slot0().call(block_identifier=bloack_identifier)
        return UniswapV3Slot0Respond(slot0[0], slot0[1], slot0[2], slot0[3], slot0[4], slot0[5], slot0[6])
    
    def calculate_price_from_sqrt_price_x96(self,sqrt_price_x96:int) -> float:
        
        if self.is_underlying_token0:
            price = (sqrt_price_x96/2**96)**2 * 10**(self.underlying.decimal-self.collateral.decimal)
            
        else:
            price = 1/((sqrt_price_x96/2**96)**2 * 10**(self.collateral.decimal-self.underlying.decimal))
            
        return price
    
    async def async_get_fees(self) -> int:
        
        return await self.fee().call()
    
    async def async_get_price_from_sqrt_price_x96(self,bloack_identifier:BlockIdentifier='latest') -> float:
        
        slot0 =  await self.async_get_slot0(bloack_identifier)
        return self.calculate_price_from_sqrt_price_x96(slot0.sqrt_price_x96)
    
    def get_process_swap_event_log(self,event_log:EventData) -> UniswapV3SwapEventData:
        
        base_event_data,arg = self.process_event_data(event_log)
        sender = Web3.to_checksum_address(arg['sender'])
        recipient = Web3.to_checksum_address(arg['recipient'])
        amount_0 = int(arg['amount0'])
        amount_1 = int(arg['amount1'])
        sqrt_price_x96 = int(arg['sqrtPriceX96'])
        liquidity = int(arg['liquidity'])
        tick = int(arg['tick'])
        
        args = UniswapV3SwapArgs(sender,recipient,amount_0,amount_1,sqrt_price_x96,liquidity,tick)
        
        return UniswapV3SwapEventData(address=base_event_data.address,
                                        block_hash=base_event_data.block_hash,
                                        block_number=base_event_data.block_number,
                                        transaction_hash=base_event_data.transaction_hash,
                                        log_index=base_event_data.log_index,
                                        transaction_index=base_event_data.transaction_index,
                                        args=args)
        
    def get_swap_report(self,swap_event_data:UniswapV3SwapEventData) -> UniswapV3SwapReport:
        
        sender = swap_event_data.args.sender
        recipient = swap_event_data.args.recipient
        amount_0 = swap_event_data.args.amount_0
        amount_1 = swap_event_data.args.amount_1
        transaction_hash = swap_event_data.transaction_hash
        log_index = swap_event_data.log_index
        block_number = swap_event_data.block_number
        transaction_index = swap_event_data.transaction_index
        
        if self.is_underlying_token0:
            if amount_0 >0:
                action = 'Sell'
                underlying_amount = amount_0
                collateral_amount = abs(amount_1)
                
            else:
                action = 'Buy'
                collateral_amount = amount_1
                underlying_amount = abs(amount_0)
                
        else:
            if amount_0>0:
                action = 'Buy'
                underlying_amount = abs(amount_1)
                collateral_amount = amount_0
                
            else:
                action = 'Sell'
                collateral_amount = abs(amount_0)
                underlying_amount = amount_1
                
        return UniswapV3SwapReport(sender,recipient,action,underlying_amount,collateral_amount,transaction_hash,log_index,block_number,transaction_index)
    
class AsyncUniswapV3QuoterContractBase(AsyncWeb3HTTP):
    
    def __init__(self,
                 rpc_detail: RPCDetail,
                 address:AddressLike|None) -> None:
        super().__init__(rpc_detail)
        if address is None:
            if rpc_detail.chain_id == 8453:
                address = UNISWAPV3_QUOTER_ADDRESS_BASE
            else:
                raise ValueError("address cannot be None")
        else:
            address = address
            
        self.address = Web3.to_checksum_address(address)
        self.contract = self.load_contract(UNISWAPV3_QUOTER_ABI,self.address)
        
    def factory(self) -> AsyncContractFunction:
        
        return self.contract.functions.factory()
    
    def quoteExactInput(self,path:bytes,amount_in:int) -> AsyncContractFunction:
        
        return self.contract.functions.quoteExactInput(path,amount_in)
    
    def quoteExactInputSingle(self,token_in:ChecksumAddress,token_out:ChecksumAddress,amount_in:int,fee:int,sqrt_price_limit_X96:int) -> AsyncContractFunction:
        
        return self.contract.functions.quoteExactInputSingle((token_in,token_out,amount_in,fee,sqrt_price_limit_X96))
    
    def quoteExactInputSingleWithPool(self,token_in:ChecksumAddress,token_out:ChecksumAddress,amount_in:int,pool:ChecksumAddress,fee:int,sqrt_price_limit_X96:int) -> AsyncContractFunction:
        
        return self.contract.functions.quoteExactInputSingleWithPool((token_in,token_out,amount_in,pool,fee,sqrt_price_limit_X96))

    def quoteExactOutput(self,path:bytes,amount_out:int) -> AsyncContractFunction:
        
        return self.contract.functions.quoteExactOutput(path,amount_out)
    
    def quoteExactOutputSingle(self,token_in:ChecksumAddress,token_out:ChecksumAddress,amount:int,fee:int,sqrt_price_limit_X96:int) -> AsyncContractFunction:
        
        return self.contract.functions.quoteExactOutputSingle((token_in,token_out,amount,fee,sqrt_price_limit_X96))
    
    def quoteExactOutputSingleWithPool(self,token_in:ChecksumAddress,token_out:ChecksumAddress,amount:int,fee:int,pool:ChecksumAddress,sqrt_price_limit_X96:int) -> AsyncContractFunction:
        
        return self.contract.functions.quoteExactOutputSingleWithPool((token_in,token_out,amount,fee,pool,sqrt_price_limit_X96))
    
class AsyncUniswapV3QuoterContract(AsyncUniswapV3QuoterContractBase):
    
    def __init__(self,
                 rpc_detail: RPCDetail,
                 address:AddressLike|None) -> None:
        super().__init__(rpc_detail, address)
        pass
    
    async def async_quote_exact_input_single(self,token_in:ChecksumAddress,token_out:ChecksumAddress,amount_in:int,fee:int,sqrt_price_limit_X96:int) -> UniswapV3QuoteExactInputSingleRespond:
        
        res = await self.quoteExactInputSingle(token_in,token_out,amount_in,fee,sqrt_price_limit_X96).call()
        
        return UniswapV3QuoteExactInputSingleRespond(*res)
    
    async def async_quote_exact_output_single(self,token_in:ChecksumAddress,token_out:ChecksumAddress,amount:int,fee:int,sqrt_price_limit_X96:int) -> UniswapV3QuoteExactOutputSingleRespond:
        
        res = await self.quoteExactOutputSingle(token_in,token_out,amount,fee,sqrt_price_limit_X96).call()
        
        return UniswapV3QuoteExactOutputSingleRespond(*res)
    
    async def async_quote_exact_input_single_with_pool(self,token_in:ChecksumAddress,token_out:ChecksumAddress,amount_in:int,pool:ChecksumAddress,fee:int,sqrt_price_limit_X96:int) -> UniswapV3QuoteExactInputSingleRespond:
        
        res = await self.quoteExactInputSingleWithPool(token_in,token_out,amount_in,pool,fee,sqrt_price_limit_X96).call()
        
        return UniswapV3QuoteExactInputSingleRespond(*res)
    
    async def async_quote_exact_output_single_with_pool(self,token_in:ChecksumAddress,token_out:ChecksumAddress,amount:int,fee:int,pool:ChecksumAddress,sqrt_price_limit_X96:int) -> UniswapV3QuoteExactOutputSingleRespond:
        
        res = await self.quoteExactOutputSingleWithPool(token_in,token_out,amount,fee,pool,sqrt_price_limit_X96).call()
        
        return UniswapV3QuoteExactOutputSingleRespond(*res)
    
class AsyncUniswapV3RouterV2ContractBase(AsyncWeb3HTTP):
    
    def __init__(self,
                 rpc_detail: RPCDetail,
                 address:AddressLike|None) -> None:
        super().__init__(rpc_detail)
        if address is None:
            if rpc_detail.chain_id == 8453:
                address = UNISWAPV3_ROUTERV2_ADDRESS_BASE
            else:
                raise ValueError("address cannot be None")
        else:
            address = address
            
        self.address = Web3.to_checksum_address(address)
        self.contract = self.load_contract(UNISWAPV3_ROUTERV2_ABI,self.address)
        
    def exactInputSingle(self,token_in:ChecksumAddress,token_out:ChecksumAddress,fee:int,recipient:ChecksumAddress,amount_in:int,amount_out_minimum:int,sqrt_price_limit_x96:int) -> AsyncContractFunction:
        
        return self.contract.functions.exactInputSingle((token_in,token_out,fee,recipient,amount_in,amount_out_minimum,sqrt_price_limit_x96))
    
    def exactInput(self,path:bytes,recipient:ChecksumAddress,amount_in:int,amount_out_minimum:int) -> AsyncContractFunction:
        
        return self.contract.functions.exactInput(path,recipient,amount_in,amount_out_minimum)
    
    def exactOutputSingle(self,token_in:ChecksumAddress,token_out:ChecksumAddress,fee:int,recipient:ChecksumAddress,amount_out:int,amount_in_maximum:int,sqrt_price_limit_x96:int) -> AsyncContractFunction:
        
        return self.contract.functions.exactOutputSingle((token_in,token_out,fee,recipient,amount_out,amount_in_maximum,sqrt_price_limit_x96))
    
    def exactOutput(self,path:bytes,recipient:ChecksumAddress,amount_out:int,amount_in_maximum:int) -> AsyncContractFunction:
        
        return self.contract.functions.exactOutput(path,recipient,amount_out,amount_in_maximum)
    
    def multicall(self,calls:list[bytes]) -> AsyncContractFunction:
        
        return self.contract.functions.multicall(calls)
    
class AsyncUniswapV3RouterV2Contract(AsyncUniswapV3RouterV2ContractBase):
    
    def __init__(self,
                 rpc_detail: RPCDetail,
                 address:AddressLike|None) -> None:
        super().__init__(rpc_detail, address)
        pass
    
    def single_swap_exact_input_token_to_token(self,
                                               token_in:ChecksumAddress,
                                               token_out:ChecksumAddress,
                                               fee:int,
                                               recipient:ChecksumAddress,
                                               amount_in:int,
                                               amount_out_minimum:int,
                                               sqrt_price_limit_x96:int) -> AsyncContractFunction:
        
        return self.exactInputSingle(token_in,token_out,fee,recipient,amount_in,amount_out_minimum,sqrt_price_limit_x96)
    
    def single_swap_exact_output_token_to_token(self,
                                                token_in:ChecksumAddress,
                                                token_out:ChecksumAddress,
                                                fee:int,
                                                recipient:ChecksumAddress,
                                                amount_out:int,
                                                amount_in_maximum:int,
                                                sqrt_price_limit_x96:int) -> AsyncContractFunction:
        
        return self.exactOutputSingle(token_in,token_out,fee,recipient,amount_out,amount_in_maximum,sqrt_price_limit_x96)
    
    def single_swap_exact_input_native_to_token(self,
                                                token_out:ChecksumAddress,
                                                fee:int,
                                                recipient:ChecksumAddress,
                                                amount_in:int,
                                                amount_out_minimum:int,
                                                sqrt_price_limit_x96:int) -> AsyncContractFunction:
        
        return self.exactInputSingle(self.wrap_native_address,token_out,fee,recipient,amount_in,amount_out_minimum,sqrt_price_limit_x96)
    
    def single_swap_exact_output_native_to_token(self,
                                                token_out:ChecksumAddress,
                                                fee:int,
                                                recipient:ChecksumAddress,
                                                amount_out:int,
                                                amount_in_maximum:int,
                                                sqrt_price_limit_x96:int) -> AsyncContractFunction:
        swap_args:tuple[ChecksumAddress,ChecksumAddress,int,ChecksumAddress,int,int,int] = (self.wrap_native_address,token_out,fee,recipient,amount_out,amount_in_maximum,sqrt_price_limit_x96)
        args: list[tuple[ChecksumAddress, ChecksumAddress, int, ChecksumAddress, int, int, int]] = [swap_args]
        swap_data = self.contract.encode_abi(abi_element_identifier='exactOutputSingle',
                                             args = args)
        
        refund_data = self.contract.encode_abi(abi_element_identifier='refundETH',args=None)
        
        return self.contract.functions.multicall([swap_data,refund_data])
    
    def single_swap_exact_input_token_to_native(self,
                                                token_in:ChecksumAddress,
                                                fee:int,
                                                recipient:ChecksumAddress,
                                                amount_in:int,
                                                amount_out_minimum:int,
                                                sqrt_price_limit_x96:int) -> AsyncContractFunction:
        
        swap_args:tuple[ChecksumAddress,ChecksumAddress,int,ChecksumAddress,int,int,int] = (token_in,self.wrap_native_address,fee,self.address,amount_in,amount_out_minimum,sqrt_price_limit_x96)
        args: list[tuple[ChecksumAddress, ChecksumAddress, int, ChecksumAddress, int, int, int]] = [swap_args]
        swap_data = self.contract.encode_abi(abi_element_identifier='exactInputSingle',
                                             args = args)
        
        unwrap_data = self.contract.encode_abi(abi_element_identifier='unwrapWETH9',args=(amount_out_minimum,recipient))
        
        return self.contract.functions.multicall([swap_data,unwrap_data])
    
    def single_swap_exact_output_token_to_native(self,
                                                token_in:ChecksumAddress,
                                                fee:int,
                                                recipient:ChecksumAddress,
                                                amount_out:int,
                                                amount_in_maximum:int,
                                                sqrt_price_limit_x96:int) -> AsyncContractFunction:
        
        swap_args:tuple[ChecksumAddress,ChecksumAddress,int,ChecksumAddress,int,int,int] = (token_in,self.wrap_native_address,fee,self.address,amount_out,amount_in_maximum,sqrt_price_limit_x96)
        args: list[tuple[ChecksumAddress, ChecksumAddress, int, ChecksumAddress, int, int, int]] = [swap_args]
        swap_data = self.contract.encode_abi(abi_element_identifier='exactOutputSingle',
                                             args = args)
        
        unwrap_data = self.contract.encode_abi(abi_element_identifier='unwrapWETH9',args=(amount_out,recipient))
        
        return self.contract.functions.multicall([swap_data,unwrap_data])
    
    def single_swap_exact_input(self,
                                token_in:ChecksumAddress,
                                token_out:ChecksumAddress,
                                fee:int,
                                recipient:ChecksumAddress,
                                amount_in:int,
                                amount_out_minimum:int,
                                sqrt_price_limit_x96:int) -> AsyncContractFunction:
        
        if token_in == token_out:
            raise ValueError("token_in and token_out cannot be same")
        
        if token_in == NATIVE_ADDRESS:
            return self.single_swap_exact_input_native_to_token(token_out,fee,recipient,amount_in,amount_out_minimum,sqrt_price_limit_x96)
        
        elif token_out == NATIVE_ADDRESS:
            return self.single_swap_exact_input_token_to_native(token_in,fee,recipient,amount_in,amount_out_minimum,sqrt_price_limit_x96)
        
        else:
            return self.single_swap_exact_input_token_to_token(token_in,token_out,fee,recipient,amount_in,amount_out_minimum,sqrt_price_limit_x96)
        
    def single_swap_exact_output(self,
                                token_in:ChecksumAddress,
                                token_out:ChecksumAddress,
                                fee:int,
                                recipient:ChecksumAddress,
                                amount_out:int,
                                amount_in_maximum:int,
                                sqrt_price_limit_x96:int) -> AsyncContractFunction:
        
        if token_in == token_out:
            raise ValueError("token_in and token_out cannot be same")
        
        if token_in == NATIVE_ADDRESS:
            
            return self.single_swap_exact_output_native_to_token(token_out,fee,recipient,amount_out,amount_in_maximum,sqrt_price_limit_x96)
        
        elif token_out == NATIVE_ADDRESS:
            
            return self.single_swap_exact_output_token_to_native(token_in,fee,recipient,amount_out,amount_in_maximum,sqrt_price_limit_x96)
        
        else:
            return self.single_swap_exact_output_token_to_token(token_in,token_out,fee,recipient,amount_out,amount_in_maximum,sqrt_price_limit_x96)
        
class AsyncUniswapV2RouterV2ContractBase(AsyncWeb3HTTP):
    
    def __init__(self,
                 rpc_detail: RPCDetail,
                 address:AddressLike|None) -> None:
        super().__init__(rpc_detail)
        if address is None:
            if rpc_detail.chain_id == 8453:
                address = UNISWAPV2_ROUTERV2_ADDRESS_BASE
            else:
                raise ValueError("address cannot be None")
        else:
            address = address
            
        self.address = Web3.to_checksum_address(address)
        self.contract = self.load_contract(UNISWAPV2_ROUTERV2_ABI,self.address)
        
    def getAmountIn(self,
                    amount_out:int,
                    reserve_in:int,
                    reserve_out:int) -> AsyncContractFunction:
        
        return self.contract.functions.getAmountIn(amount_out,reserve_in,reserve_out)
    
    def getAmountOut(self,
                        amount_in:int,
                        reserve_in:int,
                        reserve_out:int) -> AsyncContractFunction:
            
            return self.contract.functions.getAmountOut(amount_in,reserve_in,reserve_out)
        
    # Transaction Section
    
    def swapETHForExactTokens(self,
                              amount_out:int,
                              path:list[ChecksumAddress],
                              recipient:ChecksumAddress,
                              deadline:int) -> AsyncContractFunction:
        
        return self.contract.functions.swapExactETHForTokens(amount_out,path,recipient,deadline)
        
    def swapExactETHForTokens(self,
                                amount_out_min:int,
                                path:list[ChecksumAddress],
                                recipient:ChecksumAddress,
                                deadline:int) -> AsyncContractFunction:
        
        return self.contract.functions.swapExactETHForTokens(amount_out_min,path,recipient,deadline)
    
    def swapExactTokensForETH(self,
                                amount_in:int,
                                amount_out_min:int,
                                path:list[ChecksumAddress],
                                recipient:ChecksumAddress,
                                deadline:int) -> AsyncContractFunction:
        
        return self.contract.functions.swapExactTokensForETH(amount_in,amount_out_min,path,recipient,deadline)
    
    def swapExactTokensForTokens(self,
                                amount_in:int,
                                amount_out_min:int,
                                path:list[ChecksumAddress],
                                recipient:ChecksumAddress,
                                deadline:int) -> AsyncContractFunction:
        
        return self.contract.functions.swapExactTokensForTokens(amount_in,amount_out_min,path,recipient,deadline)
    
    def swapTokensForExactETH(self,
                                amount_out:int,
                                amount_in_max:int,
                                path:list[ChecksumAddress],
                                recipient:ChecksumAddress,
                                deadline:int) -> AsyncContractFunction:
        
        return self.contract.functions.swapTokensForExactETH(amount_out,amount_in_max,path,recipient,deadline)
    
    def swapTokensForExactTokens(self,
                                amount_out:int,
                                amount_in_max:int,
                                path:list[ChecksumAddress],
                                recipient:ChecksumAddress,
                                deadline:int) -> AsyncContractFunction:
        
        return self.contract.functions.swapTokensForExactTokens(amount_out,amount_in_max,path,recipient,deadline)
    
    def swapExactETHForTokensSupportingFeeOnTransferTokens(self,
                                                           amount_out_min:int,
                                                           path:list[ChecksumAddress],
                                                           to:ChecksumAddress,
                                                           deadline:int) -> AsyncContractFunction:
        
        return self.contract.functions.swapExactETHForTokensSupportingFeeOnTransferTokens(amount_out_min,path,to,deadline)
    
    def swapExactTokensForETHSupportingFeeOnTransferTokens(self,
                                                           amount_in:int,
                                                           amount_out_min:int,
                                                           path:list[ChecksumAddress],
                                                           to:ChecksumAddress,
                                                           deadline:int) -> AsyncContractFunction:
        
        return self.contract.functions.swapExactTokensForETHSupportingFeeOnTransferTokens(amount_in,amount_out_min,path,to,deadline)
    
    def swapExactTokensForTokensSupportingFeeOnTransferTokens(self,
                                                           amount_in:int,
                                                           amount_out_min:int,
                                                           path:list[ChecksumAddress],
                                                           to:ChecksumAddress,
                                                           deadline:int) -> AsyncContractFunction:
        
        return self.contract.functions.swapExactTokensForTokensSupportingFeeOnTransferTokens(amount_in,amount_out_min,path,to,deadline)
    
class AsyncUniswapV2RouterV2Contract(AsyncUniswapV2RouterV2ContractBase):
    
    def __init__(self,
                 rpc_detail: RPCDetail,
                 address:AddressLike|None) -> None:
        super().__init__(rpc_detail, address)
        pass
    
    async def async_get_amount_in(self,
                      amount_out:int,
                      reserve_in:int,
                      reserve_out:int) -> int:
        
        return await self.getAmountIn(amount_out,reserve_in,reserve_out).call()
    
    async def async_get_amount_out(self,
                      amount_in:int,
                      reserve_in:int,
                      reserve_out:int) -> int:
        
        return await self.getAmountOut(amount_in,reserve_in,reserve_out).call()
    
    def swap_given_amount_out(self,
                              amount_out:int,
                              amount_in_max:int,
                              path:list[ChecksumAddress],
                              recipient:ChecksumAddress,
                              deadline:int) -> AsyncContractFunction:
        
        token_in = path[0]
        token_out = path[-1]
        
        if len(path) == 2 and token_in == token_out:
            raise ValueError("token_in and token_out cannot be same")
        
        if token_in == NATIVE_ADDRESS:
            
            return self.swapETHForExactTokens(amount_out,path,recipient,deadline)
        
        elif token_out == NATIVE_ADDRESS:
            
            return self.swapTokensForExactETH(amount_out,amount_in_max,path,recipient,deadline)
        
        else:
            return self.swapTokensForExactTokens(amount_out,amount_in_max,path,recipient,deadline)
        
    def swap_given_amount_in(self,
                                amount_in:int,
                                amount_out_min:int,
                                path:list[ChecksumAddress],
                                recipient:ChecksumAddress,
                                deadline:int) -> AsyncContractFunction:
        
        token_in = path[0]
        token_out = path[-1]
        
        if len(path) == 2 and token_in == token_out:
            
            raise ValueError("token_in and token_out cannot be same")
        
        if token_in == NATIVE_ADDRESS:
            
            return self.swapExactETHForTokens(amount_out_min,path,recipient,deadline)
        
        elif token_out == NATIVE_ADDRESS:
            
            return self.swapExactTokensForETH(amount_in,amount_out_min,path,recipient,deadline)
        
        else:
            return self.swapExactTokensForTokens(amount_in,amount_out_min,path,recipient,deadline)
        
    def swap_given_amount_in_supporting_fee_on_transfer_tokens(self,
                                                              amount_in:int,
                                                              amount_out_min:int,
                                                              path:list[ChecksumAddress],
                                                                recipient:ChecksumAddress,
                                                                deadline:int) -> AsyncContractFunction:
        
        token_in = path[0]
        token_out = path[-1]
        
        if len(path) == 2 and token_in == token_out:
            raise ValueError("token_in and token_out cannot be same")
        
        if token_in == NATIVE_ADDRESS:
            
            return self.swapExactETHForTokensSupportingFeeOnTransferTokens(amount_out_min,path,recipient,deadline)
        
        elif token_out == NATIVE_ADDRESS:
            
            return self.swapExactTokensForETHSupportingFeeOnTransferTokens(amount_in,amount_out_min,path,recipient,deadline)
        
        else:
            return self.swapExactTokensForTokensSupportingFeeOnTransferTokens(amount_in,amount_out_min,path,recipient,deadline)