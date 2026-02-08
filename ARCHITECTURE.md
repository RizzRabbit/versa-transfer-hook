# 🏗️ Architecture Deep Dive

## System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     Solana Blockchain                        │
│                                                              │
│  ┌────────────────┐      ┌─────────────────┐              │
│  │  Token-2022    │      │ Versa Transfer  │              │
│  │  Program       │─────▶│     Hook        │              │
│  │  (SPL)         │      │   (Our Code)    │              │
│  └────────────────┘      └─────────────────┘              │
│         │                         │                         │
│         │                         ▼                         │
│         │                 ┌───────────────┐                │
│         │                 │   Hook Logic  │                │
│         │                 │  • Fee Calc   │                │
│         │                 │  • Loyalty    │                │
│         │                 │  • Analytics  │                │
│         │                 │  • Compliance │                │
│         │                 └───────────────┘                │
│         │                         │                         │
│         ▼                         ▼                         │
│  ┌─────────────────────────────────────────┐              │
│  │         Program Derived Accounts         │              │
│  │  ┌──────────────┐  ┌─────────────────┐  │              │
│  │  │ HookConfig   │  │   UserState     │  │              │
│  │  │ (Global)     │  │   (Per User)    │  │              │
│  │  └──────────────┘  └─────────────────┘  │              │
│  └─────────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────────┘
```

## Transfer Flow

```
User Initiates Transfer
         │
         ▼
┌────────────────────┐
│ Token-2022 Program │
│ Detects Transfer   │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Calls Transfer Hook│  ◄── Our program gets invoked automatically
└────────┬───────────┘
         │
         ▼
┌────────────────────────────────────────┐
│ Versa Transfer Hook Logic              │
│                                        │
│ 1. Check Pause Status                  │
│    └─▶ If paused → Error              │
│                                        │
│ 2. Check Blacklist                     │
│    └─▶ If blacklisted → Error         │
│                                        │
│ 3. Calculate Fee Tier                  │
│    ├─ < 0.1 tokens → 1.00%            │
│    ├─ 0.1-1 tokens → 0.50%            │
│    ├─ 1-10 tokens → 0.25%             │
│    └─ > 10 tokens → 0.10%             │
│                                        │
│ 4. Check Loyalty Tier                  │
│    ├─ 10+ transfers → Bronze (-0.10%) │
│    ├─ 50+ transfers → Silver (-0.25%) │
│    └─ 100+ transfers → Gold (-0.50%)  │
│                                        │
│ 5. Calculate Final Fee                 │
│    Base Fee - Loyalty Discount         │
│                                        │
│ 6. Update User Stats                   │
│    ├─ Increment transfer count         │
│    ├─ Add to total volume              │
│    └─ Update timestamp                 │
│                                        │
│ 7. Update Global Stats                 │
│    ├─ Increment total transfers        │
│    ├─ Add to global volume             │
│    └─ Add to fees collected            │
│                                        │
│ 8. Log Transfer Details                │
│    └─▶ Emit on-chain events           │
└────────┬───────────────────────────────┘
         │
         ▼
┌────────────────────┐
│ Transfer Completes │
│ Tokens Move        │
│ Fees Collected     │
└────────────────────┘
```

## State Management

### HookConfig (Global, per Mint)

```
PDA Derivation: ["hook-config", mint_pubkey]

┌───────────────────────────────────┐
│         HookConfig                │
├───────────────────────────────────┤
│ authority: Pubkey                 │  ◄── Admin who controls hook
│ fee_collector: Pubkey             │  ◄── Where fees go
│ is_paused: bool                   │  ◄── Emergency stop
│ total_transfers: u64              │  ◄── Global counter
│ total_volume: u64                 │  ◄── Total tokens transferred
│ total_fees_collected: u64         │  ◄── Revenue tracking
└───────────────────────────────────┘

Size: 137 bytes
Rent: ~0.001 SOL one-time
```

### UserState (Per User, per Mint)

```
PDA Derivation: ["user-state", user_pubkey, mint_pubkey]

┌───────────────────────────────────┐
│          UserState                │
├───────────────────────────────────┤
│ owner: Pubkey                     │  ◄── User identity
│ transfer_count: u64               │  ◄── Activity tracking
│ total_volume: u64                 │  ◄── User's total volume
│ first_transfer_timestamp: i64     │  ◄── Account age
│ last_transfer_timestamp: i64      │  ◄── Last activity
│ is_blacklisted: bool              │  ◄── Compliance flag
└───────────────────────────────────┘

Size: 105 bytes
Rent: ~0.001 SOL per user (one-time)
Creation: Lazy (init_if_needed on first transfer)
```

## Fee Calculation Algorithm

```rust
fn calculate_final_fee(amount: u64, transfer_count: u64) -> u64 {
    // Step 1: Determine base fee tier
    let fee_bps = if amount < 0.1_tokens {
        100  // 1.00%
    } else if amount < 1.0_tokens {
        50   // 0.50%
    } else if amount < 10.0_tokens {
        25   // 0.25%
    } else {
        10   // 0.10%
    };
    
    // Step 2: Calculate base fee
    let base_fee = (amount * fee_bps) / 10000;
    
    // Step 3: Determine loyalty discount
    let discount_bps = if transfer_count >= 100 {
        50   // 0.50% (Gold)
    } else if transfer_count >= 50 {
        25   // 0.25% (Silver)
    } else if transfer_count >= 10 {
        10   // 0.10% (Bronze)
    } else {
        0    // No discount
    };
    
    // Step 4: Calculate discount amount
    let discount = (amount * discount_bps) / 10000;
    
    // Step 5: Final fee (base - discount)
    base_fee.saturating_sub(discount)
}
```

## Example Scenarios

### Scenario 1: New User, Small Transfer
```
Input:
  amount = 0.05 tokens (50,000,000 lamports with 9 decimals)
  transfer_count = 0

Calculation:
  Tier: < 0.1 tokens → 1.00% (100 bps)
  Base Fee: 50,000,000 * 100 / 10,000 = 500,000 lamports
  Loyalty: 0 transfers → None (0 bps)
  Discount: 50,000,000 * 0 / 10,000 = 0 lamports
  
Final Fee: 500,000 lamports (0.0005 tokens)
Effective Rate: 1.00%
```

### Scenario 2: Active User, Large Transfer
```
Input:
  amount = 5.0 tokens (5,000,000,000 lamports)
  transfer_count = 50

Calculation:
  Tier: 1-10 tokens → 0.25% (25 bps)
  Base Fee: 5,000,000,000 * 25 / 10,000 = 12,500,000 lamports
  Loyalty: 50 transfers → Silver (25 bps)
  Discount: 5,000,000,000 * 25 / 10,000 = 12,500,000 lamports
  
Final Fee: 0 lamports (fully offset by loyalty!)
Effective Rate: 0.00%
```

### Scenario 3: Gold User, Whale Transfer
```
Input:
  amount = 20.0 tokens (20,000,000,000 lamports)
  transfer_count = 100

Calculation:
  Tier: > 10 tokens → 0.10% (10 bps)
  Base Fee: 20,000,000,000 * 10 / 10,000 = 20,000,000 lamports
  Loyalty: 100 transfers → Gold (50 bps)
  Discount: 20,000,000,000 * 50 / 10,000 = 100,000,000 lamports
  
Final Fee: 0 lamports (discount exceeds base fee, saturates to 0)
Effective Rate: 0.00%

Note: In production, you'd want min fee logic to prevent zero fees
```

## Security Model

### Access Control
```
┌─────────────────────────────────────┐
│          Admin Actions              │
│  (Require authority signature)      │
├─────────────────────────────────────┤
│ • Pause/Unpause                     │
│ • Blacklist/Whitelist User          │
│ • Update Fee Collector              │
│ • Update Fee Tiers (future)         │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│         User Actions                │
│  (No special permissions)           │
├─────────────────────────────────────┤
│ • Transfer tokens                   │
│ • Trigger hook automatically        │
│ • Build loyalty tier                │
└─────────────────────────────────────┘
```

### Overflow Protection
```rust
// All arithmetic uses checked operations
amount.checked_mul(fee_bps)  // Returns None on overflow
  .unwrap()                   // Safe to unwrap (validated inputs)
  .checked_div(10000)         // Returns None on div-by-zero
  .unwrap() as u64            // Convert back to u64

// For accumulation, use saturating ops
config.total_transfers
  .saturating_add(1)          // Never overflows, clamps to u64::MAX
```

### PDA Security
```
Seeds must be deterministic and unique:

HookConfig: ["hook-config", mint]
  ✅ One per mint
  ✅ Prevents multiple configs for same mint
  
UserState: ["user-state", user, mint]
  ✅ One per user per mint
  ✅ Prevents impersonation
  ✅ Prevents double-initialization
```

## Performance Characteristics

### Compute Units
```
Instruction Breakdown:
├─ Account validation:     ~2,000 CU
├─ PDA derivation:         ~2,000 CU
├─ Fee calculation:        ~1,000 CU
├─ State updates:          ~5,000 CU
├─ Logging:                ~3,000 CU
└─ Hook return:            ~2,000 CU
─────────────────────────────────────
Total (estimated):        ~15,000 CU

Transaction Limit: 200,000 CU
Headroom: ~185,000 CU for other ops
```

### Storage Costs (Rent)
```
Per Mint:
  HookConfig: 137 bytes
  Rent: ~0.001 SOL (one-time)

Per User:
  UserState: 105 bytes
  Rent: ~0.001 SOL per user (one-time)
  Creation: Lazy (only when user first transfers)

Example at scale:
  1M users = 1M * 0.001 SOL = 1,000 SOL
  @ $100/SOL = $100,000 total storage cost
  
  But: Users pay their own rent (init_if_needed pattern)
  Protocol cost: Just the HookConfig (~0.001 SOL)
```

### Latency
```
On-chain execution:
├─ Solana block time:    ~400ms
├─ Hook execution:       < 1ms
└─ Total latency:        ~400ms

This is as fast as Solana L1 gets!
```

## Integration Example

### For Protocol Developers

```typescript
import { createTransferCheckedWithTransferHookInstruction } from '@solana/spl-token';

// Standard Token-2022 transfer with hook
const transferIx = createTransferCheckedWithTransferHookInstruction(
  connection,
  sourceTokenAccount,
  mint,
  destinationTokenAccount,
  owner,
  amount,
  decimals,
  [],  // Additional signers
  'confirmed',
  TOKEN_2022_PROGRAM_ID
);

// The hook is automatically invoked by Token-2022 program
// No special integration code needed!
const tx = new Transaction().add(transferIx);
await sendAndConfirmTransaction(connection, tx, [owner]);

// Fees are calculated and applied automatically
// Loyalty tier is updated automatically
// Analytics are tracked automatically
```

## Deployment Architecture

```
Environment: Solana (devnet/mainnet-beta)

┌──────────────────────────────────────┐
│         Deployment Setup             │
├──────────────────────────────────────┤
│ 1. Deploy program                    │
│    └─▶ Get program ID                │
│                                      │
│ 2. Update program ID in code         │
│    └─▶ declare_id!("...")           │
│                                      │
│ 3. Rebuild with correct ID           │
│    └─▶ anchor build                  │
│                                      │
│ 4. Create Token-2022 mint            │
│    └─▶ With transfer hook extension  │
│                                      │
│ 5. Initialize hook config            │
│    └─▶ Call initialize instruction   │
│                                      │
│ 6. Optional: Set up monitoring       │
│    └─▶ Watch on-chain logs          │
└──────────────────────────────────────┘
```

---

## Key Design Decisions

### Why PDA-based State?
- **Security**: No direct account ownership transfers
- **Determinism**: Same inputs always derive same address
- **Efficiency**: No need to pass account addresses explicitly
- **Scalability**: Unlimited users (bounded by Solana's account limit)

### Why init_if_needed?
- **UX**: Users don't need to pre-register
- **Gas**: Only pay rent once (on first transfer)
- **Simplicity**: No separate initialization step required

### Why Tiered Fees?
- **Fairness**: Small transactions pay proportionally more (higher risk)
- **Incentive**: Large transactions get better rates (economies of scale)
- **Flexibility**: Easy to adjust tiers for different use cases

### Why Zero-Cost Loyalty?
- **Simplicity**: No additional token to manage
- **Security**: No token minting/burning vulnerabilities
- **UX**: Automatic rewards, no claiming needed
- **Alignment**: Rewards active users without dilution

---

Built with ❤️ by WTXSoftware Agent
