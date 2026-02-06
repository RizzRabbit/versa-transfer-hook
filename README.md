# Versa Transfer Hook

**Colosseum Agent Hackathon Submission**

A flexible and extensible transfer hook for Solana Token Extensions (Token-2022), built with Anchor.

## 🎯 Project Overview

Versa Transfer Hook is a programmable transfer hook implementation for SPL Token-2022 that enables custom logic execution during token transfers. This allows for:

- Custom fee structures
- Transfer restrictions and allowlists
- Token gating mechanisms
- Compliance and regulatory controls
- Dynamic transfer rules based on on-chain data

## 🔗 Solana Integration

This project leverages Solana's Token Extensions (Token-2022) program, specifically the Transfer Hook extension. The integration includes:

- **On-chain program**: Deployed as a Solana program using Anchor framework
- **Token-2022 Extension**: Utilizes the Transfer Hook interface from SPL Token-2022
- **Account resolution**: Uses TLV (Type-Length-Value) account resolution for flexible account passing
- **PDAs**: Employs Program Derived Addresses for secure state management
- **On-chain validation**: All transfer logic executes directly on Solana L1

### Key Solana Components Used:
- `spl-transfer-hook-interface` - Transfer hook standard interface
- `spl-tlv-account-resolution` - Dynamic account resolution
- `spl-token-2022` - Token Extensions program
- `solana-program` - Core Solana runtime

## 🏗️ Architecture

### Program Structure

```
versa_transfer_hook/
├── programs/
│   └── versa_transfer_hook/
│       └── src/
│           └── lib.rs          # Main program logic
├── tests/                       # Integration tests
├── Anchor.toml                  # Anchor configuration
└── Cargo.toml                   # Rust dependencies
```

### Key Instructions

1. **`initialize_extra_account_meta_list`**: Sets up the list of additional accounts required by the transfer hook
2. **`transfer_hook`**: The main hook that executes during every token transfer

## 🚀 Getting Started

### Prerequisites

- Rust 1.75+
- Solana CLI 1.18+
- Anchor CLI 0.30+
- Node.js 18+

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/versa_transfer_hook.git
cd versa_transfer_hook

# Install dependencies
yarn install

# Build the program
anchor build

# Run tests
anchor test
```

### Deployment

```bash
# Deploy to devnet
anchor deploy --provider.cluster devnet

# Deploy to mainnet
anchor deploy --provider.cluster mainnet
```

## 💡 Use Cases

1. **Fee Optimization**: Implement dynamic fee structures based on transfer amount or frequency
2. **Compliance**: Add KYC/AML checks before allowing transfers
3. **Loyalty Programs**: Reward frequent traders with reduced fees or bonuses
4. **DAO Governance**: Restrict token transfers based on voting participation
5. **Access Control**: Create member-only tokens with transfer restrictions

## 🔧 Configuration

The transfer hook can be configured for different use cases by modifying the `transfer_hook` function in `lib.rs`. Key parameters include:

- Transfer amount
- Source/destination accounts
- Mint information
- Custom account data

## 📊 Technical Details

- **Language**: Rust
- **Framework**: Anchor 0.30.1
- **Solana Version**: 1.18.17
- **Token Standard**: SPL Token-2022
- **Program Type**: On-chain Solana program

## 🧪 Testing

```bash
# Run all tests
anchor test

# Run specific test
anchor test --skip-local-validator
```

## 🛠️ Development

### Building

```bash
# Clean build
anchor clean && anchor build

# Generate IDL
anchor idl parse -f programs/versa_transfer_hook/src/lib.rs -o target/idl/versa_transfer_hook.json
```

### Local Testing

```bash
# Start local validator
solana-test-validator

# Deploy locally
anchor deploy --provider.cluster localnet
```

## 📝 Program ID

The program is deployed at:
```
9WBmvVwg9LqodhDrh1FVLqxf4cZ22qNvQ4qEX88fewST
```

## 🔐 Security Considerations

- All transfer logic executes on-chain, ensuring transparency
- Program Derived Addresses (PDAs) protect account ownership
- Anchor's account validation prevents unauthorized access
- Transfer hooks are called by the Token-2022 program, ensuring atomicity

## 🤝 Contributing

This is a hackathon submission, but feedback and contributions are welcome!

## 📄 License

MIT

## 🏆 Colosseum Hackathon

Built for the Colosseum Agent Hackathon (Feb 2-12, 2026).

**Tags**: `defi`, `infra`, `ai`

---

**Built by an AI agent** competing in the world's first agent hackathon. 🤖✨
