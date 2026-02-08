#!/usr/bin/env python3
"""
Check if the Versa Transfer Hook program is deployed and fetch its info
"""

import asyncio
import sys
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey


async def check_program(program_id_str: str, rpc_url: str = "https://api.devnet.solana.com"):
    """Check if a program is deployed on chain"""
    
    client = AsyncClient(rpc_url, commitment=Confirmed)
    
    try:
        program_id = Pubkey.from_string(program_id_str)
        print(f"🔍 Checking program: {program_id}\n")
        
        # Get account info
        response = await client.get_account_info(program_id)
        
        if response.value is None:
            print("❌ Program not found on chain")
            print(f"   Network: {rpc_url}")
            return False
        
        account = response.value
        print("✅ Program found!")
        print(f"   Lamports: {account.lamports}")
        print(f"   Owner: {account.owner}")
        print(f"   Executable: {account.executable}")
        print(f"   Data length: {len(account.data)} bytes")
        
        if account.executable:
            print("\n✨ This is a valid executable program!")
        else:
            print("\n⚠️  Account exists but is not executable")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        await client.close()


async def get_program_accounts(program_id_str: str, rpc_url: str = "https://api.devnet.solana.com"):
    """Get accounts owned by the program (PDAs)"""
    
    client = AsyncClient(rpc_url, commitment=Confirmed)
    
    try:
        program_id = Pubkey.from_string(program_id_str)
        print(f"\n📋 Fetching accounts for program: {program_id}\n")
        
        # Get program accounts
        response = await client.get_program_accounts(program_id)
        
        accounts = response.value
        print(f"Found {len(accounts)} accounts:\n")
        
        for i, account_info in enumerate(accounts[:10], 1):  # Show first 10
            pubkey = account_info.pubkey
            account = account_info.account
            print(f"{i}. {pubkey}")
            print(f"   Lamports: {account.lamports}")
            print(f"   Data length: {len(account.data)} bytes")
            print()
        
        if len(accounts) > 10:
            print(f"   ... and {len(accounts) - 10} more")
        
        return accounts
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []
    finally:
        await client.close()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python check_program.py <PROGRAM_ID> [devnet|mainnet]")
        print("\nExample:")
        print("  python check_program.py 11111111111111111111111111111111")
        print("  python check_program.py YOUR_PROGRAM_ID mainnet")
        sys.exit(1)
    
    program_id = sys.argv[1]
    network = sys.argv[2] if len(sys.argv) > 2 else "devnet"
    
    rpc_urls = {
        "devnet": "https://api.devnet.solana.com",
        "mainnet": "https://api.mainnet-beta.solana.com",
        "mainnet-beta": "https://api.mainnet-beta.solana.com",
        "testnet": "https://api.testnet.solana.com",
        "localhost": "http://127.0.0.1:8899"
    }
    
    rpc_url = rpc_urls.get(network, network)
    print(f"🌐 Network: {network} ({rpc_url})\n")
    
    # Check if program exists
    exists = await check_program(program_id, rpc_url)
    
    # If it exists, fetch its accounts
    if exists:
        await get_program_accounts(program_id, rpc_url)


if __name__ == "__main__":
    asyncio.run(main())
