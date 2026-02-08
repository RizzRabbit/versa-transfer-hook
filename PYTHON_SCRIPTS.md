# Python Scripts for Versa Transfer Hook

This directory contains Python utilities for testing and interacting with the Versa Transfer Hook program, using the same `solana` package (0.36.11) that works in the versalang-arena project.

## 🚀 Quick Start

### 1. Setup Virtual Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Scripts

```bash
# Test hook logic locally (no deployment needed)
./venv/bin/python scripts/test_hook_locally.py

# Run demo scenarios
./venv/bin/python scripts/python_demo.py

# Check if program is deployed (requires program ID)
./venv/bin/python scripts/check_program.py YOUR_PROGRAM_ID devnet
```

## 📁 Available Scripts

### 1. `test_hook_locally.py` - Local Simulation ✨ **RECOMMENDED**

**Purpose**: Test the transfer hook logic without deploying to chain

**Features**:
- Simulates the exact on-chain logic
- Tests fee calculation (4 tiers)
- Tests loyalty rewards (Bronze/Silver/Gold)
- Tests blacklist functionality
- Tracks user state across transfers

**Usage**:
```bash
./venv/bin/python scripts/test_hook_locally.py
```

**Output Example**:
```
📊 Transfer #1: Initial small transfer
   Amount: 0.0500 tokens
   Base fee tier: 1.00%
   Loyalty tier: None
   Final fee: 0.0005 tokens (1.00%)
   Net received: 0.0495 tokens
   Total volume: 0.0500 tokens

📊 Transfer #100: Gold unlocked (100th)
   Amount: 50.0000 tokens
   Loyalty tier: Gold
   Discount: -0.50% (0.0025 tokens)
   Final fee: 0.0475 tokens (0.09%)
   Net received: 49.9525 tokens
```

### 2. `python_demo.py` - Scenario Testing

**Purpose**: Demonstrate various transfer scenarios and calculations

**Features**:
- Calculate fees for different amounts
- Show loyalty tier progression
- Display fee tier breakdown
- RPC connection for on-chain queries (when deployed)

**Usage**:
```bash
./venv/bin/python scripts/python_demo.py
```

**Output**:
```
💰 Fee Tier Breakdown:
   0.05 tokens → 1.00% fee
   0.50 tokens → 0.50% fee
   5.00 tokens → 0.25% fee
  50.00 tokens → 0.10% fee

🏆 Loyalty Tier Progression:
   1 transfers → None   tier (-0.00%)
  10 transfers → Bronze tier (-0.10%)
  50 transfers → Silver tier (-0.25%)
 100 transfers → Gold   tier (-0.50%)
```

### 3. `check_program.py` - On-Chain Verification

**Purpose**: Check if the program is deployed and fetch its accounts

**Features**:
- Verify program deployment
- Check program accounts
- Fetch PDAs (hook configs, user states)
- Works with devnet/mainnet/testnet

**Usage**:
```bash
# Check on devnet
./venv/bin/python scripts/check_program.py YOUR_PROGRAM_ID devnet

# Check on mainnet
./venv/bin/python scripts/check_program.py YOUR_PROGRAM_ID mainnet

# Check on localhost
./venv/bin/python scripts/check_program.py YOUR_PROGRAM_ID localhost
```

**Output Example**:
```
🔍 Checking program: ABC123...

✅ Program found!
   Lamports: 1000000
   Owner: BPFLoader2111111111111111111111111111111111
   Executable: True
   Data length: 12345 bytes

✨ This is a valid executable program!

📋 Fetching accounts for program: ABC123...
Found 5 accounts:

1. HookConfigPDA123...
   Lamports: 2000000
   Data length: 137 bytes
```

## 🧪 Testing Without Deployment

The beauty of these Python scripts is that you can **test all the hook logic locally** without needing to:
- Build the Rust program
- Deploy to Solana
- Set up test wallets

The `test_hook_locally.py` script simulates the exact same calculations as the on-chain program:

```python
simulator = VersaTransferHookSimulator()

# Simulate a transfer
result = simulator.simulate_transfer(
    user="Alice",
    amount=1_000_000_000  # 1 token
)

print(f"Fee: {result['final_fee']}")
print(f"Tier: {result['loyalty_tier']}")
```

## 📊 Understanding the Output

### Fee Tiers
- **< 0.1 tokens**: 1.00% base fee
- **0.1 - 1 tokens**: 0.50% base fee  
- **1 - 10 tokens**: 0.25% base fee
- **> 10 tokens**: 0.10% base fee

### Loyalty Discounts
- **Bronze (10+ transfers)**: -0.10% discount
- **Silver (50+ transfers)**: -0.25% discount
- **Gold (100+ transfers)**: -0.50% discount

### Example: Gold Tier + Large Transfer
```
Amount: 50 tokens
Base fee tier: 0.10% (large amount)
Loyalty: Gold -0.50%
Final fee: 0.05% (amazing!)
```

## 🔧 Customization

You can modify the scripts to test different scenarios:

```python
# In test_hook_locally.py, add your own test cases:
test_transfers = [
    ("Your scenario", 100_000_000_000),  # 100 tokens
    ("Another test", 5_000_000),         # 0.005 tokens
]

# Modify fee tiers (for testing alternative models):
simulator.FEE_TIER_1_BPS = 150  # Change from 100 to 150 (1.5%)

# Test blacklist scenarios:
simulator.blacklist_user("Bob")
result = simulator.simulate_transfer("Bob", 1_000_000_000)
# Will return: {"success": False, "error": "User is blacklisted"}
```

## 🐛 Troubleshooting

### Import Errors
```bash
# Make sure you're using the venv python
which python  # Should show .../venv/bin/python

# Reinstall if needed
pip install -r requirements.txt
```

### RPC Connection Issues
```bash
# For check_program.py, try different endpoints:
./venv/bin/python scripts/check_program.py PROGRAM_ID https://api.devnet.solana.com
./venv/bin/python scripts/check_program.py PROGRAM_ID http://localhost:8899
```

## 🎯 Why This Approach Works

This Python setup replicates what worked in versalang-arena:
1. **Same `solana` package** (0.36.11) - proven to work
2. **Local testing** - no deployment needed for development
3. **RPC interaction** - can check deployed programs when ready
4. **Pure Python** - no Rust toolchain issues

## 🚀 Next Steps

1. **Test locally**: Run `test_hook_locally.py` to verify logic
2. **Deploy program**: Use Anchor to deploy to devnet
3. **Verify deployment**: Use `check_program.py` with your program ID
4. **Interact on-chain**: Extend `python_demo.py` to send real transactions

## 📚 Related Files

- `requirements.txt` - Python dependencies
- `programs/versa_transfer_hook/src/lib.rs` - Rust source (the actual on-chain logic)
- `tests/versa_transfer_hook.ts` - TypeScript tests (Anchor framework)

---

**Built to bypass the Rust toolchain issues while maintaining full testing capability!** 🎯
