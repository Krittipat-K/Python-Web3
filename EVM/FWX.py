from hexbytes import HexBytes
from web3 import Web3
import requests
from typing import (
    Any,
)
from eth_typing import (
    ChecksumAddress,
)
import asyncio

from EVM.constant import (
    FWX_MEMBERSHIP_ADDRESS_BASE,
    FWX_PERP_CORE_ADDRESS_BASE,
    FWX_PERP_HELPER_ADDRESS_BASE,
    PYTH_ID,
)

from EVM.types import (
    TxParamsInput,
    RPCDetail,
    FWXPerpHelperGetAllPositionRespond,
    FWXPerpHelperGetBalanceRespond
)

from EVM.W3 import (
    AsyncWeb3HTTP,
    AsyncWeb3HTTPWallet,
)

from web3.types import (
    TxParams,
)


from EVM.Contract import (
    AsyncERC20Contract,
    AsyncFWXMembershipContract,
    AsyncFWXPerpCoreContract,
    AsyncFWXPerpHelperContract,
)

def get_raw_pyth_fwx_data()->dict[str,Any]:
        url = 'https://hermes-pyth.fwx.finance/?pyth=perp&encoding=hex'
        data = requests.get(url).json()
        return data
    
def create_pyth_fwx_data(raw_pyth_data:dict[str,Any])->list[tuple[bytes,tuple[int,...],tuple[int,...]]]:
    pyth_data:list[tuple[bytes,tuple[int,...],tuple[int,...]]] = []
    for i in raw_pyth_data['parsed']:
        
        id:bytes = bytes.fromhex(i['id'])
        price:tuple[int,...] = tuple([int(j) for j in i['price'].values()])
        ema_price:tuple[int,...] = tuple([int(j) for j in i['ema_price'].values()])
        d:tuple[bytes,tuple[int,...],tuple[int,...]] = (id,price,ema_price)
        pyth_data.append(d)
        
    return pyth_data

def create_pyth_update_fwx_data(raw_pyth_data:dict[str,Any])->list[bytes]:
    
    return [bytes.fromhex(raw_pyth_data['binary']['data'][0])]

class FWXPerpSDK(AsyncWeb3HTTPWallet):
    
    def __init__(self,
                 rpc_detail: RPCDetail,
                 private_key: str,
                 referal_id:int=0,
                 membership_address:ChecksumAddress=FWX_MEMBERSHIP_ADDRESS_BASE,
                 core_address:ChecksumAddress=FWX_PERP_CORE_ADDRESS_BASE,
                 helper_address:ChecksumAddress=FWX_PERP_HELPER_ADDRESS_BASE,) -> None:
        
        super().__init__(rpc_detail, private_key)
        self.membership = AsyncFWXMembershipContract(rpc_detail, membership_address)
        self.core = AsyncFWXPerpCoreContract(rpc_detail, core_address)
        self.helper = AsyncFWXPerpHelperContract(rpc_detail, helper_address)
        self.usdc = AsyncERC20Contract(rpc_detail, self.token_details['usdc'].address)
        asyncio.run(self.get_nft_id(referal_id))
            
    async def get_nft_id(self,referal_id:int=0)->None:
        self.nft_id = await self.membership.async_get_default_membership(self.wallet_address)
        if self.nft_id == 0:
            print("Minting NFT ID")
            txn_params = await self.membership.mint(referal_id).build_transaction()
            txn = await self.async_send_transaction(txn_params)
            await self.w3.eth.wait_for_transaction_receipt(txn)
            self.nft_id = await self.membership.async_get_default_membership(self.wallet_address)
        
    async def get_perp_balance(self,
                                     nft_id:int=0)->FWXPerpHelperGetBalanceRespond:
        if nft_id == 0:
            nft_id = self.nft_id
        raw_pyth_data = get_raw_pyth_fwx_data()
        pyth_data = create_pyth_fwx_data(raw_pyth_data)
        
        return await self.helper.async_get_balance(self.core.address,nft_id,pyth_data)
    
    async def get_all_positions(self,nft_id:int) -> list[FWXPerpHelperGetAllPositionRespond]|None:
        
        if nft_id == 0:
            nft_id = self.nft_id
        raw_pyth_data = get_raw_pyth_fwx_data()
        pyth_data = create_pyth_fwx_data(raw_pyth_data)
        
        return await self.helper.async_get_all_active_positions(self.core.address,
                                                                nft_id,
                                                                pyth_data)
        
        
    async def deposit_collateral_in_wei(self,
                                        amount:int,
                                        underlying_address:ChecksumAddress,
                                        tx_params_input:TxParamsInput=TxParamsInput(),
                                        waiting_txn:bool=True)->HexBytes:
        
        await self.usdc.async_checking_approve_ERC20(self,self.wallet_address)
        
        deposit_func = self.core.depositCollateral(self.nft_id,self.usdc.address,underlying_address,amount)
        
        txn_params = await self.async_create_txn_params(tx_params_input)
        txn_params = await deposit_func.build_transaction(txn_params)
        txn = await self.async_send_transaction(txn_params)
        if waiting_txn:
            await self.w3.eth.wait_for_transaction_receipt(txn)
        return txn
    
    async def deposit_collateral(self,
                                 amount:float,
                                 underlying_address:ChecksumAddress,
                                 tx_params_input:TxParamsInput=TxParamsInput(),
                                 waiting_txn:bool=True)->HexBytes:
        
        amount_in_wei = Web3.to_wei(amount,self.usdc.unit_type)
        
        return await self.deposit_collateral_in_wei(amount_in_wei,underlying_address,tx_params_input,waiting_txn)
    
    async def get_max_contract_size(self,
                              underlying_address:ChecksumAddress,
                              raw_pyth_data:dict[str,Any],
                              is_new_long:bool,
                              leverage:int,
                              safety_factor:int=980000)->int:
        pyth_data = create_pyth_fwx_data(raw_pyth_data)
        leverage = leverage*10**18
        
        return await self.helper.async_get_max_contract_size(self.core.address,
                                                self.nft_id,
                                                underlying_address,
                                                is_new_long,
                                                leverage,
                                                safety_factor,
                                                pyth_data)
        
    async def open_position_given_contract_size_in_wei(self,
                                                       is_long:bool,
                                                       is_new_long:bool,
                                                       contract_size:int,
                                                       leverage:int,
                                                       underlying_address:ChecksumAddress,
                                                       raw_pyth_data:dict[str,Any],
                                                       tx_params_input:TxParamsInput=TxParamsInput(),
                                                       waiting_txn:bool=True)->HexBytes:
        max_contract_size = await self.get_max_contract_size(underlying_address,raw_pyth_data,is_new_long,leverage)
        if contract_size > max_contract_size:
            contract_size = max_contract_size
            print("Contract size is too large, setting to max contract size")
        leverage = leverage*10**18
        pyth_updata_data = create_pyth_update_fwx_data(raw_pyth_data)
        value = 25
        func = self.core.openPosition(self.nft_id,
                                      is_long,
                                      self.usdc.address,
                                      underlying_address,
                                      contract_size,
                                      leverage,
                                      pyth_updata_data,
                                      )
        tx_params_input = tx_params_input._replace(value=value)
        txn_params = await self.async_create_txn_params(tx_params_input)
        txn_params = await func.build_transaction(txn_params)
        txn = await self.async_send_transaction(txn_params)
        if waiting_txn:
            await self.w3.eth.wait_for_transaction_receipt(txn)
        return txn
        
    def get_contract_size_given_volumn(self,
                                       volume:float,
                                       underlying_symbol:str,
                                       )->tuple[float,dict[str,Any]]:
        contract_size = 0
        raw_pyth_data = get_raw_pyth_fwx_data()
        for i in raw_pyth_data['parsed']:
            if i['id'] == PYTH_ID[underlying_symbol]:
                price = int(i['price']['price'])*10**i['price']['expo']
                contract_size = volume/price
                break
            
        if contract_size == 0:
            raise ValueError("Invalid underlying symbol")
    
            
        return contract_size,raw_pyth_data
    
    async def open_position_given_contract_size(self,
                                          is_long:bool,
                                          contract_size:float,
                                          leverage:int,
                                          underlying_address:ChecksumAddress,
                                          raw_pyth_data:dict[str,Any],
                                          is_new_long:bool,
                                          tx_params_input:TxParamsInput=TxParamsInput(),
                                          waiting_txn:bool=True)->HexBytes:
        underlying_symbol = self.address_map[underlying_address]
        underlying = self.token_details[underlying_symbol]
        contract_size_in_wei = Web3.to_wei(contract_size,underlying.unit_type)
        
        return await self.open_position_given_contract_size_in_wei(is_long,
                                                                   is_new_long,
                                                                   contract_size_in_wei,
                                                                   leverage,
                                                                   underlying_address,
                                                                   raw_pyth_data,
                                                                   tx_params_input,
                                                                   waiting_txn)
        
    async def close_position_with_pos_id(self,
                                         pos_id:int,
                                         closing_size:int,
                                         tx_params_input:TxParamsInput=TxParamsInput(),
                                            waiting_txn:bool=True)->HexBytes:
        
        raw_pyth_data = get_raw_pyth_fwx_data()
        value = len(raw_pyth_data['parsed']) + len(raw_pyth_data['binary'])
        pyth_update_data = create_pyth_update_fwx_data(raw_pyth_data)
        func =  self.core.closePosition(self.nft_id,
                                        pos_id,
                                        closing_size,
                                        pyth_update_data)
        tx_params_input = tx_params_input._replace(value=value)
        txn_params = await self.async_create_txn_params(tx_params_input)
        txn_params = await func.build_transaction(txn_params)
        txn = await self.async_send_transaction(txn_params)
        if waiting_txn:
            await self.w3.eth.wait_for_transaction_receipt(txn)
        return txn
    