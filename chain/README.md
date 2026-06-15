# Chain Genesis

## IMPORTANT — Before deploying a new chain

The `genesis.json` file is a **template**. Before running a new chain:

1. **Generate a unique signer keypair:**
   ```bash
   python scripts/create-miner-wallet.py
   ```

2. **Replace the placeholder signer address** in `genesis.json`:
   - In `extradata`: replace `f39Fd6e51aad88F6F4ce6aB8827279cffFb92266` with your signer address (no `0x` prefix, zero-padded to fill the field)
   - In `alloc`: replace `"0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"` with your signer address

3. **Set the keys in `.env`:**
   ```env
   USST_SIGNER_KEY=0x<your_signer_private_key>
   USST_SIGNER_ADDRESS=0x<your_signer_address>
   USST_DEPLOYER_KEY=0x<your_deployer_private_key>
   ```

4. **Never reuse the address in the template** — its private key is publicly known (Hardhat account #0).

> The `alloc` section pre-funds the signer and deployer wallets so they have gas for the initial deploy.  
> Adjust balances as needed, then `docker compose up --build -d`.
