#!/usr/bin/env python3
"""
Test the transfer hook logic locally without needing the program deployed
Simulates the same calculations the on-chain program would perform
"""

import asyncio
from typing import Dict, Tuple


class VersaTransferHookSimulator:
    """Local simulation of the Versa Transfer Hook logic"""
    
    # Constants matching the Rust program
    FEE_TIER_1_THRESHOLD = 100_000_000  # 0.1 tokens (9 decimals)
    FEE_TIER_2_THRESHOLD = 1_000_000_000  # 1 token
    FEE_TIER_3_THRESHOLD = 10_000_000_000  # 10 tokens
    
    FEE_TIER_1_BPS = 100  # 1.00%
    FEE_TIER_2_BPS = 50   # 0.50%
    FEE_TIER_3_BPS = 25   # 0.25%
    FEE_TIER_4_BPS = 10   # 0.10%
    
    BRONZE_THRESHOLD = 10
    SILVER_THRESHOLD = 50
    GOLD_THRESHOLD = 100
    
    BRONZE_DISCOUNT_BPS = 10  # 0.10%
    SILVER_DISCOUNT_BPS = 25  # 0.25%
    GOLD_DISCOUNT_BPS = 50    # 0.50%
    
    def __init__(self):
        self.user_states = {}  # Simulate on-chain user state
    
    def calculate_base_fee(self, amount: int) -> Tuple[int, int]:
        """Calculate base fee tier and amount"""
        if amount < self.FEE_TIER_1_THRESHOLD:
            fee_bps = self.FEE_TIER_1_BPS
        elif amount < self.FEE_TIER_2_THRESHOLD:
            fee_bps = self.FEE_TIER_2_BPS
        elif amount < self.FEE_TIER_3_THRESHOLD:
            fee_bps = self.FEE_TIER_3_BPS
        else:
            fee_bps = self.FEE_TIER_4_BPS
        
        fee_amount = (amount * fee_bps) // 10000
        return fee_bps, fee_amount
    
    def calculate_loyalty_discount(self, transfer_count: int) -> Tuple[str, int]:
        """Calculate loyalty tier and discount"""
        if transfer_count >= self.GOLD_THRESHOLD:
            return "Gold", self.GOLD_DISCOUNT_BPS
        elif transfer_count >= self.SILVER_THRESHOLD:
            return "Silver", self.SILVER_DISCOUNT_BPS
        elif transfer_count >= self.BRONZE_THRESHOLD:
            return "Bronze", self.BRONZE_DISCOUNT_BPS
        else:
            return "None", 0
    
    def simulate_transfer(self, user: str, amount: int) -> Dict:
        """Simulate a complete transfer with all hook logic"""
        
        # Get or create user state
        if user not in self.user_states:
            self.user_states[user] = {
                "transfer_count": 0,
                "total_volume": 0,
                "is_blacklisted": False
            }
        
        user_state = self.user_states[user]
        
        # Check blacklist
        if user_state["is_blacklisted"]:
            return {
                "success": False,
                "error": "User is blacklisted"
            }
        
        # Calculate base fee
        fee_bps, base_fee = self.calculate_base_fee(amount)
        
        # Calculate loyalty discount
        tier, discount_bps = self.calculate_loyalty_discount(user_state["transfer_count"])
        
        # Apply discount
        discount = (base_fee * discount_bps) // 10000
        final_fee = base_fee - discount
        net_amount = amount - final_fee
        
        # Update user state
        user_state["transfer_count"] += 1
        user_state["total_volume"] += amount
        
        return {
            "success": True,
            "user": user,
            "amount": amount,
            "fee_tier_bps": fee_bps,
            "base_fee": base_fee,
            "loyalty_tier": tier,
            "discount_bps": discount_bps,
            "discount": discount,
            "final_fee": final_fee,
            "net_amount": net_amount,
            "effective_fee_bps": (final_fee * 10000) // amount if amount > 0 else 0,
            "user_transfer_count": user_state["transfer_count"],
            "user_total_volume": user_state["total_volume"]
        }
    
    def blacklist_user(self, user: str):
        """Blacklist a user"""
        if user not in self.user_states:
            self.user_states[user] = {
                "transfer_count": 0,
                "total_volume": 0,
                "is_blacklisted": True
            }
        else:
            self.user_states[user]["is_blacklisted"] = True
    
    def get_user_state(self, user: str) -> Dict:
        """Get user state"""
        return self.user_states.get(user, None)


def format_tokens(amount: int) -> str:
    """Format amount in lamports to tokens"""
    return f"{amount / 1e9:.4f}"


def format_percentage(bps: int) -> str:
    """Format basis points to percentage"""
    return f"{bps / 100:.2f}%"


async def main():
    print("🎯 Versa Transfer Hook - Local Simulator")
    print("=" * 70)
    
    simulator = VersaTransferHookSimulator()
    
    # Test scenario: User makes multiple transfers
    user_alice = "Alice"
    test_transfers = [
        ("Initial small transfer", 50_000_000),      # 0.05 tokens
        ("Growing confidence", 500_000_000),          # 0.5 tokens
        ("Regular user (10th transfer)", 1_000_000_000),  # 1 token
        ("More transfers...", 2_000_000_000),         # 2 tokens
        ("Bronze achieved!", 5_000_000_000),          # 5 tokens
        ("Silver milestone (50th)", 10_000_000_000),  # 10 tokens
        ("Gold unlocked (100th)", 50_000_000_000),    # 50 tokens
    ]
    
    print(f"\n👤 Testing user journey for: {user_alice}\n")
    
    # Simulate progression to each milestone
    current_count = 0
    for description, amount in test_transfers:
        # Fast-forward to milestone if needed
        if "10th" in description:
            while current_count < 9:
                simulator.simulate_transfer(user_alice, 1_000_000_000)
                current_count += 1
        elif "50th" in description:
            while current_count < 49:
                simulator.simulate_transfer(user_alice, 1_000_000_000)
                current_count += 1
        elif "100th" in description:
            while current_count < 99:
                simulator.simulate_transfer(user_alice, 1_000_000_000)
                current_count += 1
        
        result = simulator.simulate_transfer(user_alice, amount)
        current_count = result["user_transfer_count"]
        
        if result["success"]:
            print(f"📊 Transfer #{current_count}: {description}")
            print(f"   Amount: {format_tokens(result['amount'])} tokens")
            print(f"   Base fee tier: {format_percentage(result['fee_tier_bps'])}")
            print(f"   Loyalty tier: {result['loyalty_tier']}")
            if result['discount_bps'] > 0:
                print(f"   Discount: -{format_percentage(result['discount_bps'])} ({format_tokens(result['discount'])} tokens)")
            print(f"   Final fee: {format_tokens(result['final_fee'])} tokens ({format_percentage(result['effective_fee_bps'])})")
            print(f"   Net received: {format_tokens(result['net_amount'])} tokens")
            print(f"   Total volume: {format_tokens(result['user_total_volume'])} tokens")
            print()
        else:
            print(f"❌ {result['error']}\n")
    
    # Show final state
    final_state = simulator.get_user_state(user_alice)
    print("=" * 70)
    print(f"\n✨ Final State for {user_alice}:")
    print(f"   Total transfers: {final_state['transfer_count']}")
    print(f"   Total volume: {format_tokens(final_state['total_volume'])} tokens")
    print(f"   Blacklisted: {final_state['is_blacklisted']}")
    
    # Test blacklist
    print("\n" + "=" * 70)
    print("\n🛡️  Testing blacklist functionality\n")
    
    user_bob = "Bob"
    
    # Bob makes a successful transfer
    result = simulator.simulate_transfer(user_bob, 1_000_000_000)
    print(f"✅ Bob's first transfer: {format_tokens(result['net_amount'])} tokens received")
    
    # Blacklist Bob
    simulator.blacklist_user(user_bob)
    print("⚠️  Bob has been blacklisted")
    
    # Bob tries another transfer
    result = simulator.simulate_transfer(user_bob, 1_000_000_000)
    if not result["success"]:
        print(f"❌ Bob's second transfer blocked: {result['error']}")
    
    print("\n✅ Simulation complete!")


if __name__ == "__main__":
    asyncio.run(main())
