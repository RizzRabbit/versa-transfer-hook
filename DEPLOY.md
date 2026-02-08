# Deployment Guide

## Prerequisites

- Solana CLI installed (`solana --version`)
- Anchor CLI installed (`anchor --version`)
- Node.js & Yarn installed
- Wallet with SOL for deployment

## Build

```bash
# Fix edition 2024 compatibility issues (if needed)
find ~/.cargo/registry/src -type f -name "Cargo.toml" -exec sed -i 's/edition = "2024"/edition = "2021"/' {} \;

# Build the program
cd programs/versa_transfer_hook
cargo-build-sbf

# Or use Anchor
cd ../..
anchor build
```

## Deploy to Devnet

```bash
# Configure Solana CLI for devnet
solana config set --url devnet

# Check wallet balance (need ~5 SOL for deployment)
solana balance

# If low, airdrop some SOL
solana airdrop 2

# Deploy
anchor deploy --provider.cluster devnet

# Update program ID in code if changed
# Edit: Anchor.toml, declare_id!() in lib.rs
```

## Deploy to Mainnet

```bash
# Configure for mainnet
solana config set --url mainnet-beta

# Ensure wallet has sufficient SOL (deployment costs ~3-5 SOL)
solana balance

# Deploy
anchor deploy --provider.cluster mainnet

# Verify deployment
solana program show <PROGRAM_ID>
```

## Post-Deployment

###1. Initialize Hook for a Token

```typescript
import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { VersaTransferHook } from "./target/types/versa_transfer_hook";

const program = anchor.workspace.VersaTransferHook as Program<VersaTransferHook>;

// Derive hook config PDA
const [hookConfig] = PublicKey.findProgramAddressSync(
  [Buffer.from("hook-config"), mint.toBuffer()],
  program.programId
);

// Initialize
await program.methods
  .initialize(feeCollectorPubkey)
  .accounts({
    hookConfig,
    mint: mintPubkey,
    authority: authorityKeypair.publicKey,
    systemProgram: SystemProgram.programId,
  })
  .signers([authorityKeypair])
  .rpc();
```

### 2. Create Token with Hook

```typescript
import {
  ExtensionType,
  createInitializeMintInstruction,
  createInitializeTransferHookInstruction,
  getMintLen,
  TOKEN_2022_PROGRAM_ID,
} from "@solana/spl-token";

// Create mint with transfer hook extension
const extensions = [ExtensionType.TransferHook];
const mintLen = getMintLen(extensions);

const createAccountIx = SystemProgram.createAccount({
  fromPubkey: payer.publicKey,
  newAccountPubkey: mint.publicKey,
  space: mintLen,
  lamports: await connection.getMinimumBalanceForRentExemption(mintLen),
  programId: TOKEN_2022_PROGRAM_ID,
});

const initTransferHookIx = createInitializeTransferHookInstruction(
  mint.publicKey,
  authority.publicKey,
  PROGRAM_ID, // Versa Transfer Hook program ID
  TOKEN_2022_PROGRAM_ID
);

const initMintIx = createInitializeMintInstruction(
  mint.publicKey,
  decimals,
  mintAuthority.publicKey,
  null,
  TOKEN_2022_PROGRAM_ID
);

await sendAndConfirmTransaction(
  connection,
  new Transaction().add(createAccountIx, initTransferHookIx, initMintIx),
  [payer, mint]
);
```

## Testing

```bash
# Start local validator
solana-test-validator

# In another terminal, run tests
anchor test --skip-local-validator
```

## Troubleshooting

### Build Errors

If you see "edition 2024" errors:
```bash
find ~/.cargo/registry/src -type f -name "Cargo.toml" -exec sed -i 's/edition = "2024"/edition = "2021"/' {} \;
```

### Deployment Fails

- Check wallet balance: `solana balance`
- Verify cluster: `solana config get`
- Check program size (max 10 MB on devnet/mainnet)

### Hook Not Working

- Verify hook is initialized: Check if hook-config PDA exists
- Confirm transfer uses `createTransferCheckedWithTransferHookInstruction`
- Check logs: `solana logs` while testing

## Program Addresses

- **Program ID**: `9WBmvVwg9LqodhDrh1FVLqxf4cZ22qNvQ4qEX88fewST` (update after deployment)
- **GitHub**: https://github.com/RizzRabbit/versa-transfer-hook

## Support

Issues? Open a GitHub issue or contact [@Versa_Arena](https://twitter.com/Versa_Arena)
