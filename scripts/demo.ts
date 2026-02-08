/**
 * Demo Script for Versa Transfer Hook
 * 
 * Demonstrates:
 * - Dynamic fee tiers
 * - Loyalty rewards
 * - Blacklist functionality  
 * - Pause mechanism
 */

import * as anchor from "@coral-xyz/anchor";
import { Program, BN } from "@coral-xyz/anchor";
import { VersaTransferHook } from "../target/types/versa_transfer_hook";
import {
  PublicKey,
  Keypair,
  SystemProgram,
  Transaction,
  sendAndConfirmTransaction,
  LAMPORTS_PER_SOL,
  Connection,
  clusterApiUrl,
} from "@solana/web3.js";
import {
  ExtensionType,
  createInitializeMintInstruction,
  createInitializeTransferHookInstruction,
  getMintLen,
  TOKEN_2022_PROGRAM_ID,
  createAssociatedTokenAccountIdempotentInstruction,
  getAssociatedTokenAddressSync,
  createMintToInstruction,
  createTransferCheckedWithTransferHookInstruction,
} from "@solana/spl-token";

async function main() {
  console.log("🎯 Versa Transfer Hook Demo\n");

  // Setup connection (change to devnet/mainnet as needed)
  const connection = new Connection("http://localhost:8899", "confirmed");
  
  // Load wallet from environment or create new for demo
  const wallet = Keypair.fromSecretKey(
    Buffer.from(JSON.parse(process.env.WALLET_SECRET || "[]"))
  );

  const provider = new anchor.AnchorProvider(
    connection,
    new anchor.Wallet(wallet),
    { commitment: "confirmed" }
  );
  anchor.setProvider(provider);

  const program = anchor.workspace
    .VersaTransferHook as Program<VersaTransferHook>;

  // Generate accounts
  const mint = Keypair.generate();
  const mintAuthority = Keypair.generate();
  const feeCollector = Keypair.generate();
  const alice = Keypair.generate();
  const bob = Keypair.generate();

  console.log("📋 Accounts:");
  console.log(`   Mint: ${mint.publicKey.toString()}`);
  console.log(`   Program: ${program.programId.toString()}\n`);

  // Airdrop SOL
  console.log("💰 Airdropping SOL...");
  await Promise.all([
    connection.requestAirdrop(wallet.publicKey, 5 * LAMPORTS_PER_SOL),
    connection.requestAirdrop(mintAuthority.publicKey, 2 * LAMPORTS_PER_SOL),
    connection.requestAirdrop(alice.publicKey, 2 * LAMPORTS_PER_SOL),
    connection.requestAirdrop(bob.publicKey, 2 * LAMPORTS_PER_SOL),
  ]).then((sigs) =>
    Promise.all(sigs.map((sig) => connection.confirmTransaction(sig)))
  );
  console.log("✅ SOL airdropped\n");

  // Derive PDAs
  const [hookConfig] = PublicKey.findProgramAddressSync(
    [Buffer.from("hook-config"), mint.publicKey.toBuffer()],
    program.programId
  );

  const [aliceUserState] = PublicKey.findProgramAddressSync(
    [
      Buffer.from("user-state"),
      alice.publicKey.toBuffer(),
      mint.publicKey.toBuffer(),
    ],
    program.programId
  );

  // Create mint with transfer hook
  console.log("🏗️  Creating Token-2022 mint with transfer hook...");
  const extensions = [ExtensionType.TransferHook];
  const mintLen = getMintLen(extensions);
  const lamports = await connection.getMinimumBalanceForRentExemption(mintLen);

  const createMintTx = new Transaction().add(
    SystemProgram.createAccount({
      fromPubkey: wallet.publicKey,
      newAccountPubkey: mint.publicKey,
      space: mintLen,
      lamports,
      programId: TOKEN_2022_PROGRAM_ID,
    }),
    createInitializeTransferHookInstruction(
      mint.publicKey,
      wallet.publicKey,
      program.programId,
      TOKEN_2022_PROGRAM_ID
    ),
    createInitializeMintInstruction(
      mint.publicKey,
      9,
      mintAuthority.publicKey,
      null,
      TOKEN_2022_PROGRAM_ID
    )
  );

  await sendAndConfirmTransaction(connection, createMintTx, [wallet, mint]);
  console.log("✅ Mint created\n");

  // Initialize hook
  console.log("⚙️  Initializing transfer hook...");
  await program.methods
    .initialize(feeCollector.publicKey)
    .accounts({
      hookConfig,
      mint: mint.publicKey,
      authority: wallet.publicKey,
      systemProgram: SystemProgram.programId,
    })
    .rpc();
  console.log("✅ Hook initialized\n");

  // Create token accounts and mint
  const aliceATA = getAssociatedTokenAddressSync(
    mint.publicKey,
    alice.publicKey,
    false,
    TOKEN_2022_PROGRAM_ID
  );

  const bobATA = getAssociatedTokenAddressSync(
    mint.publicKey,
    bob.publicKey,
    false,
    TOKEN_2022_PROGRAM_ID
  );

  console.log("🪙  Creating token accounts and minting...");
  const setupTx = new Transaction().add(
    createAssociatedTokenAccountIdempotentInstruction(
      wallet.publicKey,
      aliceATA,
      alice.publicKey,
      mint.publicKey,
      TOKEN_2022_PROGRAM_ID
    ),
    createAssociatedTokenAccountIdempotentInstruction(
      wallet.publicKey,
      bobATA,
      bob.publicKey,
      mint.publicKey,
      TOKEN_2022_PROGRAM_ID
    ),
    createMintToInstruction(
      mint.publicKey,
      aliceATA,
      mintAuthority.publicKey,
      1000n * 10n ** 9n,
      [],
      TOKEN_2022_PROGRAM_ID
    )
  );

  await sendAndConfirmTransaction(connection, setupTx, [
    wallet,
    mintAuthority,
  ]);
  console.log("✅ Token accounts created, 1000 tokens minted to Alice\n");

  // Demo 1: Tier 1 fee (< 0.1 tokens, 1% fee)
  console.log("📊 Demo 1: Small transfer (0.05 tokens) - Tier 1 (1% fee)");
  await transfer(connection, alice, aliceATA, bobATA, mint.publicKey, 0.05);
  await showStats();

  // Demo 2: Make 9 more transfers to reach Bronze tier
  console.log("\n📊 Demo 2: Making 9 more small transfers to unlock Bronze tier...");
  for (let i = 0; i < 9; i++) {
    await transfer(connection, alice, aliceATA, bobATA, mint.publicKey, 0.01);
  }
  await showStats();
  console.log("🏆 Bronze tier unlocked! (10+ transfers, 0.1% discount)");

  // Demo 3: Larger transfer with Bronze discount
  console.log("\n📊 Demo 3: Medium transfer (5 tokens) with Bronze loyalty discount");
  await transfer(connection, alice, aliceATA, bobATA, mint.publicKey, 5);
  await showStats();

  // Demo 4: Blacklist
  console.log("\n📊 Demo 4: Blacklisting Alice...");
  await program.methods
    .setBlacklist(true)
    .accounts({
      hookConfig,
      mint: mint.publicKey,
      userState: aliceUserState,
      user: alice.publicKey,
      authority: wallet.publicKey,
    })
    .rpc();
  console.log("🚫 Alice blacklisted");

  try {
    await transfer(connection, alice, aliceATA, bobATA, mint.publicKey, 0.01);
    console.log("❌ ERROR: Transfer should have failed!");
  } catch (e) {
    console.log("✅ Transfer correctly blocked for blacklisted user");
  }

  // Whitelist again
  await program.methods
    .setBlacklist(false)
    .accounts({
      hookConfig,
      mint: mint.publicKey,
      userState: aliceUserState,
      user: alice.publicKey,
      authority: wallet.publicKey,
    })
    .rpc();
  console.log("✅ Alice whitelisted again");

  // Demo 5: Pause
  console.log("\n📊 Demo 5: Pausing hook...");
  await program.methods
    .setPause(true)
    .accounts({
      hookConfig,
      mint: mint.publicKey,
      authority: wallet.publicKey,
    })
    .rpc();
  console.log("⏸️  Hook paused");

  try {
    await transfer(connection, alice, aliceATA, bobATA, mint.publicKey, 0.01);
    console.log("❌ ERROR: Transfer should have failed!");
  } catch (e) {
    console.log("✅ Transfer correctly blocked when paused");
  }

  // Unpause
  await program.methods
    .setPause(false)
    .accounts({
      hookConfig,
      mint: mint.publicKey,
      authority: wallet.publicKey,
    })
    .rpc();
  console.log("▶️  Hook unpaused");
  await transfer(connection, alice, aliceATA, bobATA, mint.publicKey, 0.01);
  console.log("✅ Transfers working again");

  // Final stats
  console.log("\n📊 Final Statistics:");
  await showStats();

  console.log("\n🎉 Demo complete!");

  async function transfer(
    connection: Connection,
    sender: Keypair,
    fromATA: PublicKey,
    toATA: PublicKey,
    mint: PublicKey,
    amount: number
  ) {
    const amountLamports = BigInt(Math.floor(amount * 10 ** 9));
    const ix = await createTransferCheckedWithTransferHookInstruction(
      connection,
      fromATA,
      mint,
      toATA,
      sender.publicKey,
      amountLamports,
      9,
      [],
      "confirmed",
      TOKEN_2022_PROGRAM_ID
    );

    const tx = new Transaction().add(ix);
    await sendAndConfirmTransaction(connection, tx, [sender], {
      commitment: "confirmed",
    });
  }

  async function showStats() {
    const config = await program.account.hookConfig.fetch(hookConfig);
    const userState = await program.account.userState.fetch(aliceUserState);

    console.log("   Global:");
    console.log(`     Total Transfers: ${config.totalTransfers.toString()}`);
    console.log(
      `     Total Volume: ${(
        Number(config.totalVolume) /
        10 ** 9
      ).toFixed(2)} tokens`
    );
    console.log(
      `     Total Fees: ${(
        Number(config.totalFeesCollected) /
        10 ** 9
      ).toFixed(6)} tokens`
    );
    console.log("   Alice:");
    console.log(`     Transfers: ${userState.transferCount.toString()}`);
    console.log(
      `     Volume: ${(Number(userState.totalVolume) / 10 ** 9).toFixed(
        2
      )} tokens`
    );
  }
}

main()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
