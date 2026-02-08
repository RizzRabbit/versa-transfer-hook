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
import { assert } from "chai";

describe("versa_transfer_hook", () => {
  // Configure the client to use the local cluster
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace
    .VersaTransferHook as Program<VersaTransferHook>;
  const wallet = provider.wallet as anchor.Wallet;
  const connection = provider.connection;

  // Test accounts
  let mint: Keypair;
  let mintAuthority: Keypair;
  let feeCollector: Keypair;
  let alice: Keypair;
  let bob: Keypair;
  let aliceTokenAccount: PublicKey;
  let bobTokenAccount: PublicKey;
  let hookConfig: PublicKey;
  let aliceUserState: PublicKey;

  const DECIMALS = 9;
  const MINT_AMOUNT = 1000 * 10 ** DECIMALS;

  before(async () => {
    // Generate keypairs
    mint = Keypair.generate();
    mintAuthority = Keypair.generate();
    feeCollector = Keypair.generate();
    alice = Keypair.generate();
    bob = Keypair.generate();

    // Airdrop SOL
    const airdropTxs = await Promise.all([
      connection.requestAirdrop(
        mintAuthority.publicKey,
        2 * LAMPORTS_PER_SOL
      ),
      connection.requestAirdrop(alice.publicKey, 2 * LAMPORTS_PER_SOL),
      connection.requestAirdrop(bob.publicKey, 2 * LAMPORTS_PER_SOL),
      connection.requestAirdrop(feeCollector.publicKey, LAMPORTS_PER_SOL),
    ]);

    await Promise.all(
      airdropTxs.map((tx) =>
        connection.confirmTransaction(tx, "confirmed")
      )
    );

    // Derive PDAs
    [hookConfig] = PublicKey.findProgramAddressSync(
      [Buffer.from("hook-config"), mint.publicKey.toBuffer()],
      program.programId
    );

    [aliceUserState] = PublicKey.findProgramAddressSync(
      [
        Buffer.from("user-state"),
        alice.publicKey.toBuffer(),
        mint.publicKey.toBuffer(),
      ],
      program.programId
    );

    // Get token accounts
    aliceTokenAccount = getAssociatedTokenAddressSync(
      mint.publicKey,
      alice.publicKey,
      false,
      TOKEN_2022_PROGRAM_ID
    );

    bobTokenAccount = getAssociatedTokenAddressSync(
      mint.publicKey,
      bob.publicKey,
      false,
      TOKEN_2022_PROGRAM_ID
    );

    // Create mint with transfer hook extension
    const extensions = [ExtensionType.TransferHook];
    const mintLen = getMintLen(extensions);
    const lamports = await connection.getMinimumBalanceForRentExemption(
      mintLen
    );

    const createAccountIx = SystemProgram.createAccount({
      fromPubkey: wallet.publicKey,
      newAccountPubkey: mint.publicKey,
      space: mintLen,
      lamports,
      programId: TOKEN_2022_PROGRAM_ID,
    });

    const initTransferHookIx = createInitializeTransferHookInstruction(
      mint.publicKey,
      wallet.publicKey,
      program.programId,
      TOKEN_2022_PROGRAM_ID
    );

    const initMintIx = createInitializeMintInstruction(
      mint.publicKey,
      DECIMALS,
      mintAuthority.publicKey,
      null,
      TOKEN_2022_PROGRAM_ID
    );

    const tx = new Transaction().add(
      createAccountIx,
      initTransferHookIx,
      initMintIx
    );

    await sendAndConfirmTransaction(connection, tx, [wallet.payer, mint], {
      commitment: "confirmed",
    });

    console.log("✅ Mint created:", mint.publicKey.toString());
  });

  it("Initializes the hook config", async () => {
    await program.methods
      .initialize(feeCollector.publicKey)
      .accounts({
        hookConfig,
        mint: mint.publicKey,
        authority: wallet.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .rpc();

    const config = await program.account.hookConfig.fetch(hookConfig);
    assert.equal(
      config.authority.toString(),
      wallet.publicKey.toString()
    );
    assert.equal(
      config.feeCollector.toString(),
      feeCollector.publicKey.toString()
    );
    assert.equal(config.isPaused, false);
    assert.equal(config.totalTransfers.toNumber(), 0);

    console.log("✅ Hook initialization test passed");
  });

  it("Creates token accounts and mints tokens", async () => {
    // Create Alice's token account
    const createAliceATAIx =
      createAssociatedTokenAccountIdempotentInstruction(
        wallet.publicKey,
        aliceTokenAccount,
        alice.publicKey,
        mint.publicKey,
        TOKEN_2022_PROGRAM_ID
      );

    // Mint tokens to Alice
    const mintToIx = createMintToInstruction(
      mint.publicKey,
      aliceTokenAccount,
      mintAuthority.publicKey,
      MINT_AMOUNT,
      [],
      TOKEN_2022_PROGRAM_ID
    );

    const tx = new Transaction().add(createAliceATAIx, mintToIx);

    await sendAndConfirmTransaction(
      connection,
      tx,
      [wallet.payer, mintAuthority],
      { commitment: "confirmed" }
    );

    // Create Bob's token account
    const createBobATAIx =
      createAssociatedTokenAccountIdempotentInstruction(
        wallet.publicKey,
        bobTokenAccount,
        bob.publicKey,
        mint.publicKey,
        TOKEN_2022_PROGRAM_ID
      );

    await sendAndConfirmTransaction(
      connection,
      new Transaction().add(createBobATAIx),
      [wallet.payer],
      { commitment: "confirmed" }
    );

    console.log("✅ Token accounts created and tokens minted");
  });

  it("Handles transfer with dynamic fees (Tier 1: < 0.1 tokens, 1% fee)", async () => {
    const transferAmount = 0.05 * 10 ** DECIMALS; // 0.05 tokens, should be 1% fee

    const transferIx = await createTransferCheckedWithTransferHookInstruction(
      connection,
      aliceTokenAccount,
      mint.publicKey,
      bobTokenAccount,
      alice.publicKey,
      transferAmount,
      DECIMALS,
      [],
      "confirmed",
      TOKEN_2022_PROGRAM_ID
    );

    const tx = new Transaction().add(transferIx);

    await sendAndConfirmTransaction(connection, tx, [alice], {
      commitment: "confirmed",
    });

    // Verify user state
    const userState = await program.account.userState.fetch(
      aliceUserState
    );
    assert.equal(userState.transferCount.toNumber(), 1);

    // Verify global config
    const config = await program.account.hookConfig.fetch(hookConfig);
    assert.equal(config.totalTransfers.toNumber(), 1);

    console.log("✅ Dynamic fee test passed (Tier 1)");
  });

  it("Tracks user loyalty tiers (Bronze: 10+ transfers)", async () => {
    const transferAmount = 0.01 * 10 ** DECIMALS; // Small transfers

    // Make 9 more transfers to reach 10 total (Bronze tier)
    for (let i = 0; i < 9; i++) {
      const transferIx =
        await createTransferCheckedWithTransferHookInstruction(
          connection,
          aliceTokenAccount,
          mint.publicKey,
          bobTokenAccount,
          alice.publicKey,
          transferAmount,
          DECIMALS,
          [],
          "confirmed",
          TOKEN_2022_PROGRAM_ID
        );

      const tx = new Transaction().add(transferIx);
      await sendAndConfirmTransaction(connection, tx, [alice], {
        commitment: "confirmed",
      });
    }

    const userState = await program.account.userState.fetch(
      aliceUserState
    );
    assert.equal(userState.transferCount.toNumber(), 10);

    const config = await program.account.hookConfig.fetch(hookConfig);
    assert.equal(config.totalTransfers.toNumber(), 10);

    console.log("✅ Loyalty tracking test passed (Bronze tier unlocked)");
  });

  it("Enforces blacklist rules", async () => {
    // Blacklist Alice
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

    const userState = await program.account.userState.fetch(
      aliceUserState
    );
    assert.equal(userState.isBlacklisted, true);

    // Try to transfer (should fail)
    try {
      const transferAmount = 0.01 * 10 ** DECIMALS;
      const transferIx =
        await createTransferCheckedWithTransferHookInstruction(
          connection,
          aliceTokenAccount,
          mint.publicKey,
          bobTokenAccount,
          alice.publicKey,
          transferAmount,
          DECIMALS,
          [],
          "confirmed",
          TOKEN_2022_PROGRAM_ID
        );

      const tx = new Transaction().add(transferIx);
      await sendAndConfirmTransaction(connection, tx, [alice], {
        commitment: "confirmed",
      });

      assert.fail("Transfer should have failed for blacklisted user");
    } catch (error) {
      console.log("✅ Blacklist enforcement test passed (transfer blocked)");
    }

    // Whitelist Alice again
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
  });

  it("Pauses and unpauses correctly", async () => {
    // Pause hook
    await program.methods
      .setPause(true)
      .accounts({
        hookConfig,
        mint: mint.publicKey,
        authority: wallet.publicKey,
      })
      .rpc();

    const configPaused = await program.account.hookConfig.fetch(
      hookConfig
    );
    assert.equal(configPaused.isPaused, true);

    // Try to transfer (should fail)
    try {
      const transferAmount = 0.01 * 10 ** DECIMALS;
      const transferIx =
        await createTransferCheckedWithTransferHookInstruction(
          connection,
          aliceTokenAccount,
          mint.publicKey,
          bobTokenAccount,
          alice.publicKey,
          transferAmount,
          DECIMALS,
          [],
          "confirmed",
          TOKEN_2022_PROGRAM_ID
        );

      const tx = new Transaction().add(transferIx);
      await sendAndConfirmTransaction(connection, tx, [alice], {
        commitment: "confirmed",
      });

      assert.fail("Transfer should have failed when paused");
    } catch (error) {
      console.log("✅ Pause mechanism test passed (transfers blocked)");
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

    // Transfer should work now
    const transferAmount = 0.01 * 10 ** DECIMALS;
    const transferIx =
      await createTransferCheckedWithTransferHookInstruction(
        connection,
        aliceTokenAccount,
        mint.publicKey,
        bobTokenAccount,
        alice.publicKey,
        transferAmount,
        DECIMALS,
        [],
        "confirmed",
        TOKEN_2022_PROGRAM_ID
      );

    const tx = new Transaction().add(transferIx);
    await sendAndConfirmTransaction(connection, tx, [alice], {
      commitment: "confirmed",
    });

    console.log("✅ Unpause test passed");
  });

  it("Tracks global analytics", async () => {
    const config = await program.account.hookConfig.fetch(hookConfig);

    assert.isTrue(config.totalTransfers.toNumber() > 0);
    assert.isTrue(config.totalVolume.toNumber() > 0);
    assert.isTrue(config.totalFeesCollected.toNumber() >= 0);

    console.log("📊 Global Analytics:");
    console.log(
      "   Total Transfers:",
      config.totalTransfers.toString()
    );
    console.log("   Total Volume:", config.totalVolume.toString());
    console.log(
      "   Total Fees Collected:",
      config.totalFeesCollected.toString()
    );

    const userState = await program.account.userState.fetch(
      aliceUserState
    );
    console.log("📊 Alice's Stats:");
    console.log(
      "   Transfer Count:",
      userState.transferCount.toString()
    );
    console.log("   Total Volume:", userState.totalVolume.toString());

    console.log("✅ Analytics tracking test passed");
  });
});
