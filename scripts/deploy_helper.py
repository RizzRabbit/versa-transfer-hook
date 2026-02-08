#!/usr/bin/env python3
"""
Helper script for deploying and initializing the Versa Transfer Hook
Works with the deployed program to set up hook configs
"""

import asyncio
import json
import os
from pathlib import Path
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import ID as SYS_PROGRAM_ID


class DeploymentHelper:
    """Helper for deploying and configuring the transfer hook"""
    
    def __init__(self, program_id: str, rpc_url: str = "https://api.devnet.solana.com"):
        self.program_id = Pubkey.from_string(program_id)
        self.client = AsyncClient(rpc_url, commitment=Confirmed)
        self.rpc_url = rpc_url
    
    async def get_program_info(self) -> dict:
        """Get information about the deployed program"""
        try:
            response = await self.client.get_account_info(self.program_id)
            
            if response.value is None:
                return {
                    "deployed": False,
                    "message": "Program not found on chain"
                }
            
            account = response.value
            return {
                "deployed": True,
                "executable": account.executable,
                "lamports": account.lamports,
                "owner": str(account.owner),
                "data_length": len(account.data)
            }
        except Exception as e:
            return {
                "deployed": False,
                "error": str(e)
            }
    
    def derive_hook_config_pda(self, mint: Pubkey) -> tuple:
        """Derive the hook config PDA for a mint"""
        return Pubkey.find_program_address(
            [b"hook-config", bytes(mint)],
            self.program_id
        )
    
    def derive_user_state_pda(self, mint: Pubkey, user: Pubkey) -> tuple:
        """Derive the user state PDA"""
        return Pubkey.find_program_address(
            [b"user-state", bytes(mint), bytes(user)],
            self.program_id
        )
    
    async def check_hook_config_exists(self, mint: Pubkey) -> bool:
        """Check if a hook config exists for a mint"""
        hook_config_pda, _ = self.derive_hook_config_pda(mint)
        
        try:
            response = await self.client.get_account_info(hook_config_pda)
            return response.value is not None
        except:
            return False
    
    async def get_mint_info(self, mint: Pubkey) -> dict:
        """Get information about a mint"""
        try:
            response = await self.client.get_account_info(mint)
            
            if response.value is None:
                return {"exists": False}
            
            account = response.value
            return {
                "exists": True,
                "lamports": account.lamports,
                "owner": str(account.owner),
                "data_length": len(account.data)
            }
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    async def close(self):
        """Close the RPC connection"""
        await self.client.close()


def load_keypair(path: str) -> Keypair:
    """Load a keypair from a JSON file"""
    with open(path, 'r') as f:
        data = json.load(f)
        return Keypair.from_bytes(bytes(data))


def save_deployment_info(program_id: str, network: str, mint: str = None):
    """Save deployment info to a JSON file"""
    deployment_file = Path("deployment.json")
    
    data = {}
    if deployment_file.exists():
        with open(deployment_file, 'r') as f:
            data = json.load(f)
    
    if network not in data:
        data[network] = {}
    
    data[network]["program_id"] = program_id
    if mint:
        data[network]["mint"] = mint
    data[network]["updated_at"] = asyncio.get_event_loop().time()
    
    with open(deployment_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Saved deployment info to {deployment_file}")


async def main():
    import sys
    
    if len(sys.argv) < 2:
        print("🚀 Versa Transfer Hook - Deployment Helper")
        print("=" * 60)
        print("\nUsage:")
        print("  Check program status:")
        print("    python deploy_helper.py check <PROGRAM_ID> [network]")
        print("\n  Derive PDAs:")
        print("    python deploy_helper.py pda <PROGRAM_ID> <MINT_ADDRESS>")
        print("\n  Check mint:")
        print("    python deploy_helper.py mint <MINT_ADDRESS> [network]")
        print("\n  Save deployment:")
        print("    python deploy_helper.py save <PROGRAM_ID> <NETWORK>")
        print("\nNetworks: devnet, mainnet, testnet, localhost")
        print("\nExamples:")
        print("  python deploy_helper.py check YOUR_PROGRAM_ID devnet")
        print("  python deploy_helper.py pda YOUR_PROGRAM_ID YOUR_MINT_ADDRESS")
        print("  python deploy_helper.py save YOUR_PROGRAM_ID devnet")
        return
    
    command = sys.argv[1]
    
    rpc_urls = {
        "devnet": "https://api.devnet.solana.com",
        "mainnet": "https://api.mainnet-beta.solana.com",
        "testnet": "https://api.testnet.solana.com",
        "localhost": "http://127.0.0.1:8899"
    }
    
    if command == "check":
        if len(sys.argv) < 3:
            print("❌ Missing program ID")
            return
        
        program_id = sys.argv[2]
        network = sys.argv[3] if len(sys.argv) > 3 else "devnet"
        rpc_url = rpc_urls.get(network, network)
        
        print(f"🔍 Checking program: {program_id}")
        print(f"🌐 Network: {network} ({rpc_url})\n")
        
        helper = DeploymentHelper(program_id, rpc_url)
        info = await helper.get_program_info()
        
        if info.get("deployed"):
            print("✅ Program is deployed!")
            print(f"   Executable: {info['executable']}")
            print(f"   Lamports: {info['lamports']}")
            print(f"   Owner: {info['owner']}")
            print(f"   Data length: {info['data_length']} bytes")
        else:
            print("❌ Program not deployed")
            if "error" in info:
                print(f"   Error: {info['error']}")
            else:
                print(f"   {info.get('message', 'Unknown error')}")
        
        await helper.close()
    
    elif command == "pda":
        if len(sys.argv) < 4:
            print("❌ Missing program ID or mint address")
            return
        
        program_id = sys.argv[2]
        mint_address = sys.argv[3]
        
        print(f"🔑 Deriving PDAs for:")
        print(f"   Program: {program_id}")
        print(f"   Mint: {mint_address}\n")
        
        helper = DeploymentHelper(program_id)
        mint = Pubkey.from_string(mint_address)
        
        # Derive hook config PDA
        hook_config_pda, hook_config_bump = helper.derive_hook_config_pda(mint)
        print(f"📋 Hook Config PDA:")
        print(f"   Address: {hook_config_pda}")
        print(f"   Bump: {hook_config_bump}\n")
        
        # Example user state PDA
        example_user = Keypair()
        user_state_pda, user_state_bump = helper.derive_user_state_pda(mint, example_user.pubkey())
        print(f"👤 User State PDA (example):")
        print(f"   User: {example_user.pubkey()}")
        print(f"   Address: {user_state_pda}")
        print(f"   Bump: {user_state_bump}")
        
        await helper.close()
    
    elif command == "mint":
        if len(sys.argv) < 3:
            print("❌ Missing mint address")
            return
        
        mint_address = sys.argv[2]
        network = sys.argv[3] if len(sys.argv) > 3 else "devnet"
        rpc_url = rpc_urls.get(network, network)
        
        print(f"🪙 Checking mint: {mint_address}")
        print(f"🌐 Network: {network} ({rpc_url})\n")
        
        # Use a dummy program ID since we're just checking the mint
        helper = DeploymentHelper("11111111111111111111111111111111", rpc_url)
        mint = Pubkey.from_string(mint_address)
        
        info = await helper.get_mint_info(mint)
        
        if info.get("exists"):
            print("✅ Mint exists!")
            print(f"   Lamports: {info['lamports']}")
            print(f"   Owner: {info['owner']}")
            print(f"   Data length: {info['data_length']} bytes")
        else:
            print("❌ Mint not found")
            if "error" in info:
                print(f"   Error: {info['error']}")
        
        await helper.close()
    
    elif command == "save":
        if len(sys.argv) < 4:
            print("❌ Missing program ID or network")
            print("Usage: python deploy_helper.py save <PROGRAM_ID> <NETWORK>")
            return
        
        program_id = sys.argv[2]
        network = sys.argv[3]
        
        save_deployment_info(program_id, network)
        print(f"\n💾 Deployment info saved:")
        print(f"   Program ID: {program_id}")
        print(f"   Network: {network}")
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Run without arguments to see usage")


if __name__ == "__main__":
    asyncio.run(main())
