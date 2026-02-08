#!/usr/bin/env python3
"""
Python demo script for Versa Transfer Hook
Uses the same solana package as versalang-arena
"""

import asyncio
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import ID as SYS_PROGRAM_ID
import json
import os


class VersaTransferHookClient:
    """Python client for Versa Transfer Hook program"""
    
    def __init__(self, program_id: str, rpc_url: str = "https://api.devnet.solana.com"):
        self.program_id = Pubkey.from_string(program_id)
        self.client = AsyncClient(rpc_url, commitment=Confirmed)
        
    async def get_hook_config_pda(self, mint: Pubkey) -> tuple[Pubkey, int]:
        """Derive the hook config PDA for a mint"""
        return Pubkey.find_program_address(
            [b"hook-config", bytes(mint)],
            self.program_id
        )
    
    async def get_user_state_pda(self, mint: Pubkey, user: Pubkey) -> tuple[Pubkey, int]:
        """Derive the user state PDA"""
        return Pubkey.find_program_address(
            [b"user-state", bytes(mint), bytes(user)],
            self.program_id
        )
    
    async def fetch_hook_config(self, mint: Pubkey) -> dict:
        """Fetch hook configuration from chain"""
        hook_config_pda, _ = await self.get_hook_config_pda(mint)
        
        try:
            account_info = await self.client.get_account_info(hook_config_pda)
            if account_info.value is None:
                return None
                
            # Parse the account data (simplified - would need proper borsh deserialization)
            data = account_info.value.data
            return {
                "address": str(hook_config_pda),
                "data_length": len(data),
                "exists": True
            }
        except Exception as e:
            print(f"Error fetching hook config: {e}")
            return None
    
    async def fetch_user_state(self, mint: Pubkey, user: Pubkey) -> dict:
        """Fetch user state from chain"""
        user_state_pda, _ = await self.get_user_state_pda(mint, user)
        
        try:
            account_info = await self.client.get_account_info(user_state_pda)
            if account_info.value is None:
                return None
                
            data = account_info.value.data
            return {
                "address": str(user_state_pda),
                "data_length": len(data),
                "exists": True
            }
        except Exception as e:
            print(f"Error fetching user state: {e}")
            return None
    
    async def calculate_fee(self, amount: int) -> dict:
        """
        Calculate fee based on amount (simulates on-chain logic)
        
        Fee tiers:
        - < 0.1 tokens: 1.00%
        - 0.1-1 tokens: 0.50%
        - 1-10 tokens: 0.25%
        - > 10 tokens: 0.10%
        """
        # Assuming 9 decimals (typical for SPL tokens)
        DECIMALS = 9
        ONE_TOKEN = 10 ** DECIMALS
        
        if amount < ONE_TOKEN // 10:  # < 0.1 tokens
            fee_bps = 100  # 1.00%
        elif amount < ONE_TOKEN:  # 0.1-1 tokens
            fee_bps = 50   # 0.50%
        elif amount < ONE_TOKEN * 10:  # 1-10 tokens
            fee_bps = 25   # 0.25%
        else:  # > 10 tokens
            fee_bps = 10   # 0.10%
        
        fee_amount = (amount * fee_bps) // 10000
        
        return {
            "amount": amount,
            "fee_bps": fee_bps,
            "fee_amount": fee_amount,
            "net_amount": amount - fee_amount,
            "fee_percentage": fee_bps / 100
        }
    
    async def calculate_loyalty_discount(self, transfer_count: int) -> dict:
        """
        Calculate loyalty discount based on transfer count
        
        Tiers:
        - Bronze (10+): 0.10% discount
        - Silver (50+): 0.25% discount  
        - Gold (100+): 0.50% discount
        """
        if transfer_count >= 100:
            tier = "Gold"
            discount_bps = 50  # 0.50%
        elif transfer_count >= 50:
            tier = "Silver"
            discount_bps = 25  # 0.25%
        elif transfer_count >= 10:
            tier = "Bronze"
            discount_bps = 10  # 0.10%
        else:
            tier = "None"
            discount_bps = 0
        
        return {
            "tier": tier,
            "discount_bps": discount_bps,
            "discount_percentage": discount_bps / 100,
            "transfer_count": transfer_count
        }
    
    async def simulate_transfer(self, amount: int, transfer_count: int) -> dict:
        """Simulate a complete transfer with fees and loyalty"""
        fee_calc = await self.calculate_fee(amount)
        loyalty_calc = await self.calculate_loyalty_discount(transfer_count)
        
        # Apply loyalty discount
        base_fee = fee_calc["fee_amount"]
        discount_amount = (base_fee * loyalty_calc["discount_bps"]) // 10000
        final_fee = base_fee - discount_amount
        
        return {
            "amount": amount,
            "base_fee": base_fee,
            "loyalty_tier": loyalty_calc["tier"],
            "discount": discount_amount,
            "final_fee": final_fee,
            "net_amount": amount - final_fee,
            "effective_fee_bps": (final_fee * 10000) // amount if amount > 0 else 0
        }
    
    async def close(self):
        """Close the RPC connection"""
        await self.client.close()


async def main():
    """Demo: Simulate various transfer scenarios"""
    
    # Use placeholder program ID (replace with actual deployed ID)
    PROGRAM_ID = "11111111111111111111111111111111"  # Replace with real program ID
    
    client = VersaTransferHookClient(PROGRAM_ID)
    
    print("🎯 Versa Transfer Hook - Python Demo\n")
    print("=" * 60)
    
    # Demo scenarios
    scenarios = [
        {"description": "Small transfer (0.05 tokens)", "amount": 50_000_000, "count": 1},
        {"description": "Medium transfer (1.0 tokens)", "amount": 1_000_000_000, "count": 10},
        {"description": "Large transfer (5.0 tokens)", "amount": 5_000_000_000, "count": 50},
        {"description": "Whale transfer (20.0 tokens)", "amount": 20_000_000_000, "count": 100},
    ]
    
    for scenario in scenarios:
        print(f"\n📊 {scenario['description']}")
        print(f"   Transfer Count: {scenario['count']}")
        
        result = await client.simulate_transfer(
            scenario['amount'],
            scenario['count']
        )
        
        print(f"   Amount: {result['amount'] / 1e9:.4f} tokens")
        print(f"   Loyalty Tier: {result['loyalty_tier']}")
        print(f"   Base Fee: {result['base_fee'] / 1e9:.6f} tokens")
        print(f"   Discount: {result['discount'] / 1e9:.6f} tokens")
        print(f"   Final Fee: {result['final_fee'] / 1e9:.6f} tokens")
        print(f"   Net Amount: {result['net_amount'] / 1e9:.4f} tokens")
        print(f"   Effective Rate: {result['effective_fee_bps'] / 100:.2f}%")
        print("-" * 60)
    
    # Fee calculation table
    print("\n💰 Fee Tier Breakdown:")
    amounts = [0.05, 0.5, 5.0, 50.0]
    for amt in amounts:
        amount_lamports = int(amt * 1e9)
        fee_calc = await client.calculate_fee(amount_lamports)
        print(f"   {amt:6.2f} tokens → {fee_calc['fee_percentage']:.2f}% fee")
    
    # Loyalty progression
    print("\n🏆 Loyalty Tier Progression:")
    counts = [1, 10, 50, 100, 200]
    for count in counts:
        loyalty = await client.calculate_loyalty_discount(count)
        print(f"   {count:3d} transfers → {loyalty['tier']:6s} tier (-{loyalty['discount_percentage']:.2f}%)")
    
    await client.close()
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
