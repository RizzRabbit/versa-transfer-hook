use anchor_lang::prelude::*;
use anchor_spl::token_interface::{Mint, TokenAccount};

declare_id!("9WBmvVwg9LqodhDrh1FVLqxf4cZ22qNvQ4qEX88fewST");

/// Fee tier thresholds (in tokens)
pub const TIER_1_THRESHOLD: u64 = 100_000_000; // 0.1 token (assuming 9 decimals)
pub const TIER_2_THRESHOLD: u64 = 1_000_000_000; // 1 token
pub const TIER_3_THRESHOLD: u64 = 10_000_000_000; // 10 tokens

/// Fee basis points per tier (1 bp = 0.01%)
pub const TIER_1_FEE_BPS: u16 = 100; // 1%
pub const TIER_2_FEE_BPS: u16 = 50;  // 0.5%
pub const TIER_3_FEE_BPS: u16 = 25;  // 0.25%
pub const TIER_4_FEE_BPS: u16 = 10;  // 0.1% (over tier 3)

/// Loyalty reward thresholds
pub const LOYALTY_BRONZE: u64 = 10;  // 10 transfers
pub const LOYALTY_SILVER: u64 = 50;  // 50 transfers
pub const LOYALTY_GOLD: u64 = 100;   // 100 transfers

#[program]
pub mod versa_transfer_hook {
    use super::*;

    /// Initialize the transfer hook configuration
    pub fn initialize(
        ctx: Context<Initialize>,
        fee_collector: Pubkey,
    ) -> Result<()> {
        let config = &mut ctx.accounts.hook_config;
        config.authority = ctx.accounts.authority.key();
        config.fee_collector = fee_collector;
        config.is_paused = false;
        config.total_transfers = 0;
        config.total_volume = 0;
        config.total_fees_collected = 0;
        
        msg!("✅ Versa Transfer Hook initialized!");
        msg!("Authority: {}", config.authority);
        msg!("Fee Collector: {}", config.fee_collector);
        
        Ok(())
    }

    /// Initialize extra account meta list for the transfer hook
    pub fn initialize_extra_account_meta_list(
        _ctx: Context<InitializeExtraAccountMetaList>,
    ) -> Result<()> {
        msg!("✅ Extra account meta list initialized!");
        Ok(())
    }

    /// Main transfer hook logic - executes on every transfer
    pub fn transfer_hook(
        ctx: Context<TransferHook>,
        amount: u64,
    ) -> Result<()> {
        let config = &mut ctx.accounts.hook_config;
        let user_state = &mut ctx.accounts.user_state;

        // Check if hook is paused
        require!(!config.is_paused, ErrorCode::HookPaused);

        // Check whitelist/blacklist
        if user_state.is_blacklisted {
            return err!(ErrorCode::UserBlacklisted);
        }

        // Initialize user state if first transfer
        if user_state.transfer_count == 0 {
            user_state.owner = ctx.accounts.owner.key();
            user_state.first_transfer_timestamp = Clock::get()?.unix_timestamp;
        }

        // Calculate dynamic fee based on amount
        let fee_bps = calculate_fee_tier(amount);
        let fee_amount = (amount as u128)
            .checked_mul(fee_bps as u128)
            .unwrap()
            .checked_div(10000)
            .unwrap() as u64;

        // Apply loyalty discount
        let loyalty_tier = get_loyalty_tier(user_state.transfer_count);
        let discount_bps = match loyalty_tier {
            LoyaltyTier::Bronze => 10,  // 0.1% discount
            LoyaltyTier::Silver => 25,  // 0.25% discount
            LoyaltyTier::Gold => 50,    // 0.5% discount
            LoyaltyTier::None => 0,
        };
        
        let final_fee = fee_amount.saturating_sub(
            (amount as u128)
                .checked_mul(discount_bps)
                .unwrap()
                .checked_div(10000)
                .unwrap() as u64
        );

        // Update user statistics
        user_state.transfer_count = user_state.transfer_count.saturating_add(1);
        user_state.total_volume = user_state.total_volume.saturating_add(amount);
        user_state.last_transfer_timestamp = Clock::get()?.unix_timestamp;

        // Update global statistics
        config.total_transfers = config.total_transfers.saturating_add(1);
        config.total_volume = config.total_volume.saturating_add(amount);
        config.total_fees_collected = config.total_fees_collected.saturating_add(final_fee);

        // Log transfer details
        msg!("🎯 Transfer Hook Executed!");
        msg!("Amount: {}", amount);
        msg!("Base Fee ({}bps): {}", fee_bps, fee_amount);
        msg!("Loyalty Tier: {:?}", loyalty_tier);
        msg!("Final Fee: {}", final_fee);
        msg!("User Transfers: {}", user_state.transfer_count);
        msg!("Global Transfers: {}", config.total_transfers);

        Ok(())
    }

    /// Admin: Pause the hook
    pub fn set_pause(ctx: Context<AdminAction>, paused: bool) -> Result<()> {
        let config = &mut ctx.accounts.hook_config;
        config.is_paused = paused;
        
        msg!("🛑 Hook pause status: {}", paused);
        Ok(())
    }

    /// Admin: Blacklist/whitelist a user
    pub fn set_blacklist(
        ctx: Context<SetUserStatus>,
        blacklisted: bool,
    ) -> Result<()> {
        let user_state = &mut ctx.accounts.user_state;
        user_state.is_blacklisted = blacklisted;
        
        msg!("🚫 User {} blacklist status: {}", 
            ctx.accounts.user.key(), blacklisted);
        Ok(())
    }

    /// Admin: Update fee collector
    pub fn update_fee_collector(
        ctx: Context<AdminAction>,
        new_collector: Pubkey,
    ) -> Result<()> {
        let config = &mut ctx.accounts.hook_config;
        config.fee_collector = new_collector;
        
        msg!("💰 Fee collector updated: {}", new_collector);
        Ok(())
    }
}

/// Calculate fee tier based on transfer amount
fn calculate_fee_tier(amount: u64) -> u16 {
    if amount < TIER_1_THRESHOLD {
        TIER_1_FEE_BPS
    } else if amount < TIER_2_THRESHOLD {
        TIER_2_FEE_BPS
    } else if amount < TIER_3_THRESHOLD {
        TIER_3_FEE_BPS
    } else {
        TIER_4_FEE_BPS
    }
}

/// Determine loyalty tier based on transfer count
fn get_loyalty_tier(transfer_count: u64) -> LoyaltyTier {
    if transfer_count >= LOYALTY_GOLD {
        LoyaltyTier::Gold
    } else if transfer_count >= LOYALTY_SILVER {
        LoyaltyTier::Silver
    } else if transfer_count >= LOYALTY_BRONZE {
        LoyaltyTier::Bronze
    } else {
        LoyaltyTier::None
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LoyaltyTier {
    None,
    Bronze,
    Silver,
    Gold,
}

// ============================================================================
// Account Structures
// ============================================================================

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + HookConfig::INIT_SPACE,
        seeds = [b"hook-config", mint.key().as_ref()],
        bump
    )]
    pub hook_config: Account<'info, HookConfig>,
    
    pub mint: InterfaceAccount<'info, Mint>,
    
    #[account(mut)]
    pub authority: Signer<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct InitializeExtraAccountMetaList<'info> {
    #[account(mut)]
    pub payer: Signer<'info>,
    
    /// CHECK: Extra account meta list account
    #[account(mut)]
    pub extra_account_meta_list: UncheckedAccount<'info>,
    
    pub mint: InterfaceAccount<'info, Mint>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct TransferHook<'info> {
    pub source_token: InterfaceAccount<'info, TokenAccount>,
    pub mint: InterfaceAccount<'info, Mint>,
    pub destination_token: InterfaceAccount<'info, TokenAccount>,
    
    /// CHECK: Source token account owner
    #[account(mut)]
    pub owner: Signer<'info>,
    
    #[account(
        mut,
        seeds = [b"hook-config", mint.key().as_ref()],
        bump
    )]
    pub hook_config: Account<'info, HookConfig>,
    
    #[account(
        init_if_needed,
        payer = owner,
        space = 8 + UserState::INIT_SPACE,
        seeds = [b"user-state", owner.key().as_ref(), mint.key().as_ref()],
        bump
    )]
    pub user_state: Account<'info, UserState>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct AdminAction<'info> {
    #[account(
        mut,
        seeds = [b"hook-config", mint.key().as_ref()],
        bump,
        has_one = authority
    )]
    pub hook_config: Account<'info, HookConfig>,
    
    pub mint: InterfaceAccount<'info, Mint>,
    
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct SetUserStatus<'info> {
    #[account(
        seeds = [b"hook-config", mint.key().as_ref()],
        bump,
        has_one = authority
    )]
    pub hook_config: Account<'info, HookConfig>,
    
    pub mint: InterfaceAccount<'info, Mint>,
    
    #[account(
        mut,
        seeds = [b"user-state", user.key().as_ref(), mint.key().as_ref()],
        bump
    )]
    pub user_state: Account<'info, UserState>,
    
    /// CHECK: User being blacklisted/whitelisted
    pub user: UncheckedAccount<'info>,
    
    pub authority: Signer<'info>,
}

// ============================================================================
// State Accounts
// ============================================================================

#[account]
#[derive(InitSpace)]
pub struct HookConfig {
    pub authority: Pubkey,
    pub fee_collector: Pubkey,
    pub is_paused: bool,
    pub total_transfers: u64,
    pub total_volume: u64,
    pub total_fees_collected: u64,
}

#[account]
#[derive(InitSpace)]
pub struct UserState {
    pub owner: Pubkey,
    pub transfer_count: u64,
    pub total_volume: u64,
    pub first_transfer_timestamp: i64,
    pub last_transfer_timestamp: i64,
    pub is_blacklisted: bool,
}

// ============================================================================
// Errors
// ============================================================================

#[error_code]
pub enum ErrorCode {
    #[msg("Transfer hook is currently paused")]
    HookPaused,
    
    #[msg("User is blacklisted from transfers")]
    UserBlacklisted,
    
    #[msg("Invalid fee configuration")]
    InvalidFeeConfig,
    
    #[msg("Arithmetic overflow")]
    ArithmeticOverflow,
}
