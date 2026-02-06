use anchor_lang::prelude::*;
use anchor_spl::{
    token_2022::Token2022,
    token_interface::{Mint, TokenAccount},
};
use spl_tlv_account_resolution::{account::ExtraAccountMeta, seeds::Seed, state::ExtraAccountMetaList};
use spl_transfer_hook_interface::instruction::{ExecuteInstruction, TransferHookInstruction};

declare_id!("9WBmvVwg9LqodhDrh1FVLqxf4cZ22qNvQ4qEX88fewST");

#[program]
pub mod versa_transfer_hook {
    use super::*;

    pub fn initialize_extra_account_meta_list(
        ctx: Context<InitializeExtraAccountMetaList>,
    ) -> Result<()> {
        // Initialize extra account metas for transfer hook
        // This can be customized based on your transfer hook requirements
        Ok(())
    }

    pub fn transfer_hook(ctx: Context<TransferHook>, amount: u64) -> Result<()> {
        msg!("Transfer Hook: amount = {}", amount);
        
        // Add your custom transfer hook logic here
        // For example: fee calculations, access control, token gating, etc.
        
        Ok(())
    }
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
    #[account(token::mint = mint, token::authority = owner)]
    pub source_token: InterfaceAccount<'info, TokenAccount>,
    
    pub mint: InterfaceAccount<'info, Mint>,
    
    #[account(token::mint = mint)]
    pub destination_token: InterfaceAccount<'info, TokenAccount>,
    
    /// CHECK: Source token account owner
    pub owner: UncheckedAccount<'info>,
    
    /// CHECK: Extra account meta list
    #[account(seeds = [b"extra-account-metas", mint.key().as_ref()], bump)]
    pub extra_account_meta_list: UncheckedAccount<'info>,
    
    pub token_program: Program<'info, Token2022>,
}
