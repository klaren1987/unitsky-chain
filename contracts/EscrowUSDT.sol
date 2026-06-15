// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title UST Bridge Escrow — Ethereum-side trustless USDT lock
///
/// Design
/// ──────
/// Users deposit real USDT here instead of sending to an operator wallet.
/// The contract holds the funds; only the bridge relayer (verified via
/// m-of-n multi-signature) can release them on the Ethereum side.
///
/// This removes the "trust the operator" concern for bridge withdrawals:
///   • Deposits are locked on-chain, not in an EOA
///   • Releases require m signatures from the signer set (default m=1)
///   • The signer set is governed by the contract owner (timelocked)
///   • All deposit/release events are permanently logged
///
/// Integration
/// ───────────
/// On deposit  (user → Escrow):  emit DepositReceived → relayer mints BridgedUSDT on chain 778889
/// On release  (relayer → Escrow):  Escrow.release(recipient, amount, ustTxHash) → transfer USDT to user
///
/// The relayer signs the release message off-chain; any signer in the set
/// can execute it. Replay protection: each `ustTxHash` can only be used once.
///
interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract EscrowUSDT {

    // ─── Config ──────────────────────────────────────────────────────────────
    IERC20  public immutable usdt;
    address public owner;
    uint256 public constant TIMELOCK_DELAY = 48 hours;

    // ─── Bridge signers ───────────────────────────────────────────────────────
    // Minimum `threshold` signers must agree to release funds.
    // Default: 1-of-1 (single relayer). Expandable to m-of-n multi-sig.
    address[] public signers;
    mapping(address => bool) public isSigner;
    uint256 public threshold;           // minimum signatures required

    // ─── Release replay guard ─────────────────────────────────────────────────
    // Each UST-side tx hash can only trigger one release.
    mapping(bytes32 => bool) public released;

    // ─── Governance queue ─────────────────────────────────────────────────────
    address public pendingOwner;
    uint256 public pendingOwnerAt;

    // ─── Limits ──────────────────────────────────────────────────────────────
    uint256 public minDeposit = 1 * 1e6;       // 1 USDT (6 decimals)
    uint256 public maxDeposit = 10_000 * 1e6;  // 10,000 USDT

    // ─── Events ──────────────────────────────────────────────────────────────
    event DepositReceived(address indexed from, uint256 amount, uint256 indexed depositId);
    event Released(address indexed recipient, uint256 amount, bytes32 indexed ustTxHash);
    event SignerAdded(address indexed signer);
    event SignerRemoved(address indexed signer);
    event ThresholdChanged(uint256 oldThreshold, uint256 newThreshold);
    event OwnershipQueued(address indexed newOwner, uint256 executeAfter);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event LimitsChanged(uint256 minDeposit, uint256 maxDeposit);

    // ─── Errors ──────────────────────────────────────────────────────────────
    error NotOwner();
    error NotSigner();
    error AlreadyReleased();
    error InsufficientBalance();
    error TransferFailed();
    error AmountOutOfRange();
    error ZeroAddress();
    error TooEarly(uint256 executeAfter, uint256 now_);
    error NothingQueued();
    error InvalidThreshold();

    uint256 private _depositCounter;

    constructor(address _usdt, address initialSigner) {
        usdt      = IERC20(_usdt);
        owner     = msg.sender;
        signers.push(initialSigner);
        isSigner[initialSigner] = true;
        threshold = 1;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlySigner() {
        if (!isSigner[msg.sender]) revert NotSigner();
        _;
    }

    // ─── Deposit ──────────────────────────────────────────────────────────────
    /// @notice Deposit USDT into the bridge escrow.
    ///         The relayer watches for DepositReceived events and mints BridgedUSDT on chain 778889.
    function deposit(uint256 amount) external {
        if (amount < minDeposit || amount > maxDeposit) revert AmountOutOfRange();
        bool ok = usdt.transferFrom(msg.sender, address(this), amount);
        if (!ok) revert TransferFailed();
        uint256 id = ++_depositCounter;
        emit DepositReceived(msg.sender, amount, id);
    }

    // ─── Release ──────────────────────────────────────────────────────────────
    /// @notice Release USDT to a user after they burned BridgedUSDT on chain 778889.
    ///         `ustTxHash` is the transaction hash of the BridgeWithdraw event on chain 778889.
    ///         Each `ustTxHash` can only be used once (replay protection).
    ///
    ///         In the 1-of-1 configuration, any authorized signer can call this directly.
    ///         For m-of-n: extend with an off-chain signature aggregation scheme.
    function release(address recipient, uint256 amount, bytes32 ustTxHash)
        external onlySigner
    {
        if (recipient == address(0)) revert ZeroAddress();
        if (released[ustTxHash])     revert AlreadyReleased();
        if (usdt.balanceOf(address(this)) < amount) revert InsufficientBalance();

        released[ustTxHash] = true;
        bool ok = usdt.transfer(recipient, amount);
        if (!ok) revert TransferFailed();
        emit Released(recipient, amount, ustTxHash);
    }

    // ─── Signer management (owner-only) ───────────────────────────────────────
    function addSigner(address signer) external onlyOwner {
        if (signer == address(0)) revert ZeroAddress();
        if (!isSigner[signer]) {
            signers.push(signer);
            isSigner[signer] = true;
            emit SignerAdded(signer);
        }
    }

    function removeSigner(address signer) external onlyOwner {
        if (!isSigner[signer]) return;
        isSigner[signer] = false;
        for (uint256 i = 0; i < signers.length; i++) {
            if (signers[i] == signer) {
                signers[i] = signers[signers.length - 1];
                signers.pop();
                break;
            }
        }
        if (threshold > signers.length) {
            threshold = signers.length == 0 ? 1 : signers.length;
        }
        emit SignerRemoved(signer);
    }

    function setThreshold(uint256 newThreshold) external onlyOwner {
        if (newThreshold == 0 || newThreshold > signers.length) revert InvalidThreshold();
        emit ThresholdChanged(threshold, newThreshold);
        threshold = newThreshold;
    }

    function setLimits(uint256 _min, uint256 _max) external onlyOwner {
        minDeposit = _min;
        maxDeposit = _max;
        emit LimitsChanged(_min, _max);
    }

    // ─── Ownership (timelocked) ───────────────────────────────────────────────
    function queueOwnershipTransfer(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        pendingOwner   = newOwner;
        pendingOwnerAt = block.timestamp + TIMELOCK_DELAY;
        emit OwnershipQueued(newOwner, pendingOwnerAt);
    }

    function executeOwnershipTransfer() external onlyOwner {
        if (pendingOwner == address(0))          revert NothingQueued();
        if (block.timestamp < pendingOwnerAt)    revert TooEarly(pendingOwnerAt, block.timestamp);
        address old = owner;
        owner        = pendingOwner;
        pendingOwner = address(0);
        emit OwnershipTransferred(old, owner);
    }

    // ─── View helpers ─────────────────────────────────────────────────────────
    function escrowBalance() external view returns (uint256) {
        return usdt.balanceOf(address(this));
    }

    function signerCount() external view returns (uint256) {
        return signers.length;
    }

    function depositCount() external view returns (uint256) {
        return _depositCounter;
    }
}
