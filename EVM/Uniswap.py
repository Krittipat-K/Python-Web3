from typing import Optional
from eth_typing import ChecksumAddress
from web3 import Web3
from hexbytes import HexBytes
import asyncio
import time

from web3.types import (
    Wei,
    TxParams
    # Nonce,
)
from EVM.constant import NATIVE_ADDRESS
from EVM.ExeceptionType import InsufficientBalanceForSwap
from EVM.W3 import (
    AsyncWeb3HTTPWallet,
    AsyncWeb3HTTP
)
from EVM.Contract import (
    AsyncUniswapV2RouterV2Contract,
    AsyncUniswapV2PoolContract,
    AsyncUniswapV3PoolContract,
    AsyncUniswapV3QuoterContract,
    AsyncUniswapV3RouterV2Contract,
    
)
from EVM.types import (
    TxParamsInput,
    RPCDetail,
)
    
def get_dead_line()->int:
    return int(time.time()) + 10 * 60

class AsyncUniswapV2SinglePoolSDK(AsyncWeb3HTTP):
    
    def __init__(self, 
                 rpc_detail: RPCDetail,
                 pool_address:ChecksumAddress,
                 underlying_address:ChecksumAddress,
                 collateral_address:ChecksumAddress,
                 router_address:Optional[ChecksumAddress]=None) -> None:
        super().__init__(rpc_detail)
        self.pool = AsyncUniswapV2PoolContract(rpc_detail,pool_address,underlying_address,collateral_address)
        self.router = AsyncUniswapV2RouterV2Contract(rpc_detail,router_address)
        
    async def async_trade_given_collateral(self,
                               trading_order:float,
                               slippage:float,
                               wallet:AsyncWeb3HTTPWallet,
                               recipient:Optional[ChecksumAddress]=None,
                               swap_with_native:bool=True,
                               recive_in_native:bool=True,
                               tx_params_input:TxParamsInput=TxParamsInput(),)->TxParams:
        if recipient is None:
            recipient = wallet.wallet_address
        
        volumn_in_wei = int(Web3.to_wei(abs(trading_order),self.pool.collateral.unit_type))
        if trading_order >0: #Buy Case
            
            token_in = self.pool.collateral.address
            token_out = self.pool.underlying.address
            
            path = [token_in, token_out]
            amount_detail = await self.router.async_get_amounts_out(volumn_in_wei, path,)
            amount_out = amount_detail[-1]
            min_amount_out = int(amount_out*(1-slippage))
            
            if token_out == self.wrap_native_address:
                if recive_in_native:
                    token_out = NATIVE_ADDRESS
                    
            if token_in == self.wrap_native_address:
                if swap_with_native:
                    token_in = NATIVE_ADDRESS
                    tx_params_input = tx_params_input._replace(value = Wei(volumn_in_wei))
            else:
                swap_with_native = False
                
            token_in_balance = 0
            if token_in == NATIVE_ADDRESS:
                token_in_balance = await self.w3.eth.get_balance(wallet.wallet_address)
            else:
                token_in_balance = await self.pool.collateral.async_get_balance_of(wallet.wallet_address)
                
            if token_in_balance < volumn_in_wei:
                raise InsufficientBalanceForSwap(token_in_balance, volumn_in_wei, token_in)
            
            if not swap_with_native:
                await self.pool.collateral.async_checking_approve_ERC20(wallet, self.router.address)
                
            path = [token_in, token_out]
            
            swap_func = self.router.swap_given_amount_in(volumn_in_wei,
                                                         min_amount_out,
                                                         path,
                                                         recipient,
                                                         get_dead_line())
            
        else: #Sell Case
            
            token_in = self.pool.underlying.address
            token_out = self.pool.collateral.address
            path = [token_in, token_out]
            
            amount_detail = await self.router.async_get_amounts_in(volumn_in_wei, path)
            amount_in = amount_detail[0]
            max_amount_in = int(amount_in*(1+slippage))
            
            if token_out == self.wrap_native_address:
                if recive_in_native:
                    token_out = NATIVE_ADDRESS
            if token_in == self.wrap_native_address:
                if swap_with_native:
                    token_in = NATIVE_ADDRESS
                    tx_params_input = tx_params_input._replace(value = Wei(max_amount_in))
            else:
                swap_with_native = False

            # checking amount in balance
            token_in_balance = 0
            if token_in == NATIVE_ADDRESS:
                token_in_balance = await self.w3.eth.get_balance(wallet.wallet_address)
                
            else:
                
                token_in_balance = await self.pool.underlying.async_get_balance_of(wallet.wallet_address)
                
            if token_in_balance < max_amount_in:
                
                raise InsufficientBalanceForSwap(token_in_balance, max_amount_in, token_in)
            
            if not swap_with_native:
                await self.pool.underlying.async_checking_approve_ERC20(wallet, self.router.address)
                
            path = [token_in, token_out]
                
            swap_func = self.router.swap_given_amount_out(volumn_in_wei,
                                                          max_amount_in,
                                                         path,
                                                         recipient,
                                                         get_dead_line())
        tx_params = await wallet.async_create_txn_params(tx_params_input)
            
        return await swap_func.build_transaction(tx_params)
    
class AsyncUniswapV3SDK(AsyncWeb3HTTP):
    
    async def __init__(self, 
                 rpc_detail: RPCDetail,
                 pool_address:ChecksumAddress,
                 underlying_address:ChecksumAddress,
                 collateral_address:ChecksumAddress,) -> None:
        super().__init__(rpc_detail)
        self.pool = AsyncUniswapV3PoolContract(rpc_detail,pool_address,underlying_address,collateral_address)
        self.quoter = AsyncUniswapV3QuoterContract(rpc_detail)
        self.router = AsyncUniswapV3RouterV2Contract(rpc_detail)
        self.fee = await self.pool.async_get_fees()
        
    async def async_trade_given_collateral(self,
                                 trading_order:float,
                                 slippage:float,
                                 wallet:AsyncWeb3HTTPWallet,
                                 recipient:Optional[ChecksumAddress]=None,
                                 swap_with_native:bool=True,
                                 recive_in_native:bool=True,
                                 tx_params_input:TxParamsInput=TxParamsInput(),)->TxParams:
        if recipient is None:
            recipient = wallet.wallet_address
        volumn_in_wei = int(Web3.to_wei(abs(trading_order),self.pool.collateral.unit_type))
        if trading_order >0: #Buy Case
            token_in = self.pool.collateral.address
            token_out = self.pool.underlying.address
            if token_out == self.wrap_native_address:
                if recive_in_native:
                    token_out = NATIVE_ADDRESS
                        
            if token_in == self.wrap_native_address:
                if swap_with_native:
                    token_in = NATIVE_ADDRESS
                    tx_params_input = tx_params_input._replace(value = Wei(volumn_in_wei))
            else:
                swap_with_native = False
                
            if token_in == NATIVE_ADDRESS:
                token_in_balance = await self.w3.eth.get_balance(wallet.wallet_address)
            else:
                token_in_balance = await self.pool.collateral.async_get_balance_of(wallet.wallet_address)
                
            if token_in_balance < volumn_in_wei:
                raise InsufficientBalanceForSwap(token_in_balance, volumn_in_wei, token_in)
                
            if not swap_with_native:
                await self.pool.collateral.async_checking_approve_ERC20(wallet, self.router.address)
                
            quoter_respond = await self.quoter.async_quote_exact_input_single_with_pool(token_in,
                                                                                token_out,
                                                                                volumn_in_wei,
                                                                                self.pool.address,
                                                                                self.fee,
                                                                                0)
            
            amount_out = quoter_respond.amount_received
            min_amount_out = int(amount_out*(1-slippage))
            
            swap_func = self.router.single_swap_exact_input(token_in,
                                                            token_out,
                                                            self.fee,
                                                            recipient,
                                                            volumn_in_wei,
                                                            min_amount_out,
                                                            0)
                
        else: #Sell Case
            token_in = self.pool.collateral.address
            token_out = self.pool.underlying.address
            
            quoter_respond = await self.quoter.async_quote_exact_output_single_with_pool(token_in,
                                                                            token_out,
                                                                            volumn_in_wei,
                                                                            self.fee,
                                                                            self.pool.address,
                                                                            0)
            amount_in = quoter_respond.amount_in
            max_amount_in = int(amount_in*(1+slippage))
            
            if token_out == self.wrap_native_address:
                if recive_in_native:
                    token_out = NATIVE_ADDRESS
            
            if token_in == self.wrap_native_address:
                if swap_with_native:
                    token_in = NATIVE_ADDRESS
                    tx_params_input = tx_params_input._replace(value = Wei(max_amount_in))
            else:
                swap_with_native = False
                
            # checking amount in balance
            token_in_balance = 0
            if token_in == NATIVE_ADDRESS:
                token_in_balance = await self.w3.eth.get_balance(wallet.wallet_address)
                
            else:
                token_in_balance = await self.pool.underlying.async_get_balance_of(wallet.wallet_address)
                
            if token_in_balance < max_amount_in:
                
                raise InsufficientBalanceForSwap(token_in_balance, max_amount_in, token_in)
            
            if not swap_with_native:
                await self.pool.underlying.async_checking_approve_ERC20(wallet, self.router.address)
                
            swap_func = self.router.single_swap_exact_output(token_in,
                                                            token_out,
                                                            self.fee,
                                                            recipient,
                                                            volumn_in_wei,
                                                            max_amount_in,
                                                            0)
                
        tx_params = await wallet.async_create_txn_params(tx_params_input)    
        return await swap_func.build_transaction(tx_params)
    
    async def async_trade_given_underlying(self,
                                    trading_order:float,
                                    slippage:float,
                                    wallet:AsyncWeb3HTTPWallet,
                                    recipient:Optional[ChecksumAddress]=None,
                                    swap_with_native:bool=True,
                                    recive_in_native:bool=True,
                                    tx_params_input:TxParamsInput=TxParamsInput(),)->TxParams:
        if recipient is None:
            recipient = wallet.wallet_address
        volumn_in_wei = int(Web3.to_wei(abs(trading_order),self.pool.underlying.unit_type))
        if trading_order >0: #Buy Case
            token_in = self.pool.underlying.address
            token_out = self.pool.collateral.address
            
            quoter_respond = await self.quoter.async_quote_exact_output_single_with_pool(token_in,
                                                                            token_out,
                                                                            volumn_in_wei,
                                                                            self.fee,
                                                                            self.pool.address,
                                                                            0)
            amount_in = quoter_respond.amount_in
            max_amount_in = int(amount_in*(1+slippage))
            
            if token_out == self.wrap_native_address:
                if recive_in_native:
                    token_out = NATIVE_ADDRESS
            
            if token_in == self.wrap_native_address:
                if swap_with_native:
                    token_in = NATIVE_ADDRESS
                    tx_params_input = tx_params_input._replace(value = Wei(max_amount_in))
            else:
                swap_with_native = False
                
            # checking amount in balance
            token_in_balance = 0
            if token_in == NATIVE_ADDRESS:
                token_in_balance = await self.w3.eth.get_balance(wallet.wallet_address)
                
            else:
                
                token_in_balance = await self.pool.underlying.async_get_balance_of(wallet.wallet_address)
                
            if token_in_balance < max_amount_in:
                
                raise InsufficientBalanceForSwap(token_in_balance, max_amount_in, token_in)
            
            if not swap_with_native:
                await self.pool.collateral.async_checking_approve_ERC20(wallet, self.router.address)
                
            swap_func = self.router.single_swap_exact_output(token_in,
                                                            token_out,
                                                            self.fee,
                                                            recipient,
                                                            volumn_in_wei,
                                                            max_amount_in,
                                                            0)
        else: #Sell Case
            token_in = self.pool.underlying.address
            token_out = self.pool.collateral.address
            
            if token_out == self.wrap_native_address:
                    if recive_in_native:
                        token_out = NATIVE_ADDRESS
                        
            if token_in == self.wrap_native_address:
                if swap_with_native:
                    token_in = NATIVE_ADDRESS
                    tx_params_input = tx_params_input._replace(value = Wei(volumn_in_wei))
            else:
                swap_with_native = False
                
            if token_in == NATIVE_ADDRESS:
                token_in_balance = await self.w3.eth.get_balance(wallet.wallet_address)
            else:
                token_in_balance = await self.pool.collateral.async_get_balance_of(wallet.wallet_address)
                
            if token_in_balance < volumn_in_wei:
                raise InsufficientBalanceForSwap(token_in_balance, volumn_in_wei, token_in)
                
            if not swap_with_native:
                await self.pool.underlying.async_checking_approve_ERC20(wallet, self.router.address)
                
            quoter_respond = await self.quoter.async_quote_exact_input_single_with_pool(token_in,
                                                                                token_out,
                                                                                volumn_in_wei,
                                                                                self.pool.address,  
                                                                                self.fee,
                                                                                0)
            
            amount_out = quoter_respond.amount_received
            min_amount_out = int(amount_out*(1-slippage))
            swap_func = self.router.single_swap_exact_input(token_in,
                                                            token_out,
                                                            self.fee,
                                                            recipient,
                                                            volumn_in_wei,
                                                            min_amount_out,
                                                            0)
            
        tx_params = await wallet.async_create_txn_params(tx_params_input)    
        return await swap_func.build_transaction(tx_params)