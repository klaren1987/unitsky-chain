// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title UST Network — Proof-of-Work Mining Pool v4
///
/// Security fixes over v3 (audit findings addressed):
///   [CRITICAL-1] nonReentrant on mine() — prevents reentrancy drain
///   [CRITICAL-2] withdrawOwner now requires 7-day timelock — no instant rug
///   [HIGH-1]     MIN_DIFFICULTY constant — difficulty can never go trivially low
///   [HIGH-2]     Typed operations replace raw executeOp(callData) — no arbitrary call
///   [MEDIUM-3]   Queue reset protection — re-queuing extends, not resets, when closer
///   [INFO]       Added Withdrawn event, explicit error types, cleaner ABI
///
contract USSTMine {

    // ─── Reentrancy guard ────────────────────────────────────────────────────
    uint256 private _status;
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED     = 2;

    modifier nonReentrant() {
        if (_status == _ENTERED) revert Reentrancy();
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }

    // ─── Immutable tokenomics ────────────────────────────────────────────────
    uint256 public constant BASE_REWARD       = 0.1 ether;    // era-0 gross reward
    uint256 public constant HALVING_INTERVAL  = 50_000;       // proofs per era
    uint256 public constant MIN_REWARD        = 0.001 ether;  // floor after era 6
    uint256 public constant BURN_BPS          = 200;          // 2% burned per reward
    uint256 public constant TIMELOCK_DELAY    = 48 hours;     // difficulty / ownership
    uint256 public constant WITHDRAW_TIMELOCK = 7 days;       // pool withdrawal
    /// @dev Difficulty floor — prevents trivial proof grinding (was < 1 in v3)
    uint256 public constant MIN_DIFFICULTY    = 100_000;

    address public constant BURN_ADDRESS =
        0x000000000000000000000000000000000000dEaD;

    // ─── Mutable state ───────────────────────────────────────────────────────
    uint256 public difficulty   = 500_000;
    address public owner;
    uint256 public totalMined;
    uint256 public totalBurned;
    uint256 public immutable launchBlock;

    // ─── Typed pending operations ─────────────────────────────────────────────
    // Each operation has its own storage slot — no raw callData, no allowlist needed.

    uint256 public pendingDifficulty;
    uint256 public pendingDifficultyAt;   // earliest execution timestamp

    address public pendingOwner;
    uint256 public pendingOwnerAt;

    uint256 public pendingWithdrawAmount;
    address public pendingWithdrawTo;
    uint256 public pendingWithdrawAt;

    // ─── Double-spend guard ──────────────────────────────────────────────────
    mapping(bytes32 => bool) private _usedWork;

    // ─── Events ──────────────────────────────────────────────────────────────
    event Mined(address indexed miner, uint256 nonce, uint256 workBlock,
                uint256 minerReward, uint256 burned, uint256 era);
    event FundAdded(address indexed sender, uint256 amount);
    event HalvingReached(uint256 era, uint256 newReward);
    event Burned(uint256 amount, uint256 totalBurned);

    event DifficultyQueued(uint256 newDifficulty, uint256 executeAfter);
    event DifficultyChanged(uint256 oldDifficulty, uint256 newDifficulty);
    event DifficultyQueueCancelled();

    event OwnershipQueued(address indexed newOwner, uint256 executeAfter);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event OwnershipQueueCancelled();

    event WithdrawalQueued(address indexed to, uint256 amount, uint256 executeAfter);
    event Withdrawn(address indexed to, uint256 amount);
    event WithdrawalQueueCancelled();

    // ─── Errors ──────────────────────────────────────────────────────────────
    error InvalidProof();
    error InsufficientPool();
    error NotOwner();
    error AlreadyClaimed();
    error TransferFailed();
    error DifficultyTooLow();
    error TooEarly(uint256 executeAfter, uint256 now_);
    error ZeroAddress();
    error NothingQueued();
    error Reentrancy();
    error InvalidAmount();

    // ─── Constructor ─────────────────────────────────────────────────────────
    /// @param initialTotalMined Pass the v3 totalMined to preserve halving era on migration.
    ///                          Pass 0 for a fresh deployment.
    constructor(uint256 initialTotalMined) payable {
        owner         = msg.sender;
        launchBlock   = block.number;
        totalMined    = initialTotalMined;
        _status       = _NOT_ENTERED;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    receive() external payable { emit FundAdded(msg.sender, msg.value); }
    function fund() external payable { emit FundAdded(msg.sender, msg.value); }

    // ─── View helpers ─────────────────────────────────────────────────────────

    function currentEra() public view returns (uint256) {
        return totalMined / HALVING_INTERVAL;
    }

    function proofsTillHalving() public view returns (uint256) {
        return HALVING_INTERVAL - (totalMined % HALVING_INTERVAL);
    }

    /// @notice Current gross reward per proof (before burn). Halves each era.
    function reward() public view returns (uint256) {
        uint256 era = currentEra();
        if (era >= 7) return MIN_REWARD;
        uint256 r = BASE_REWARD >> era;
        return r < MIN_REWARD ? MIN_REWARD : r;
    }

    /// @notice Net reward the miner receives after 2% burn.
    function minerReward() public view returns (uint256) {
        uint256 gross = reward();
        return gross - (gross * BURN_BPS / 10_000);
    }

    function poolBalance() external view returns (uint256) {
        return address(this).balance;
    }

    function target() public view returns (uint256) {
        return type(uint256).max / difficulty;
    }

    function verifyWork(address miner, uint256 nonce, uint256 workBlock)
        public view returns (bool)
    {
        if (workBlock > block.number || block.number - workBlock > 10) return false;
        bytes32 hash = keccak256(abi.encodePacked(miner, nonce, workBlock));
        return uint256(hash) < target();
    }

    // ─── Core mining ──────────────────────────────────────────────────────────

    /// @notice Submit a valid proof-of-work to earn UST.
    ///         Protected by nonReentrant — reentrancy drain (CRITICAL-1 in v3) is impossible.
    function mine(uint256 nonce, uint256 workBlock) external nonReentrant {
        bytes32 workKey = keccak256(abi.encodePacked(msg.sender, nonce, workBlock));
        if (_usedWork[workKey])                         revert AlreadyClaimed();
        if (!verifyWork(msg.sender, nonce, workBlock))  revert InvalidProof();

        uint256 gross  = reward();
        uint256 burn   = gross * BURN_BPS / 10_000;
        uint256 net    = gross - burn;

        if (address(this).balance < gross) revert InsufficientPool();

        // CEI: all state changes before external calls
        _usedWork[workKey] = true;
        uint256 eraBefore  = currentEra();
        totalMined        += 1;
        totalBurned       += burn;
        uint256 eraAfter   = currentEra();

        // External calls last (reentrancy guard provides additional safety)
        (bool b,) = BURN_ADDRESS.call{value: burn}("");
        if (!b) revert TransferFailed();

        (bool ok,) = payable(msg.sender).call{value: net}("");
        if (!ok) revert TransferFailed();

        emit Mined(msg.sender, nonce, workBlock, net, burn, eraBefore);
        emit Burned(burn, totalBurned);
        if (eraAfter > eraBefore) emit HalvingReached(eraAfter, reward());
    }

    // ─── Difficulty governance (48 h timelock) ───────────────────────────────

    function queueDifficulty(uint256 newDifficulty) external onlyOwner {
        if (newDifficulty < MIN_DIFFICULTY) revert DifficultyTooLow();
        pendingDifficulty   = newDifficulty;
        pendingDifficultyAt = block.timestamp + TIMELOCK_DELAY;
        emit DifficultyQueued(newDifficulty, pendingDifficultyAt);
    }

    function executeDifficulty() external onlyOwner {
        if (pendingDifficulty == 0)                    revert NothingQueued();
        if (block.timestamp < pendingDifficultyAt)     revert TooEarly(pendingDifficultyAt, block.timestamp);
        uint256 old = difficulty;
        difficulty  = pendingDifficulty;
        pendingDifficulty = 0;
        emit DifficultyChanged(old, difficulty);
    }

    function cancelDifficulty() external onlyOwner {
        if (pendingDifficulty == 0) revert NothingQueued();
        pendingDifficulty = 0;
        emit DifficultyQueueCancelled();
    }

    // ─── Ownership transfer (48 h timelock) ──────────────────────────────────

    function queueOwnershipTransfer(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        pendingOwner   = newOwner;
        pendingOwnerAt = block.timestamp + TIMELOCK_DELAY;
        emit OwnershipQueued(newOwner, pendingOwnerAt);
    }

    function executeOwnershipTransfer() external onlyOwner {
        if (pendingOwner == address(0))             revert NothingQueued();
        if (block.timestamp < pendingOwnerAt)       revert TooEarly(pendingOwnerAt, block.timestamp);
        address old = owner;
        owner       = pendingOwner;
        pendingOwner = address(0);
        emit OwnershipTransferred(old, owner);
    }

    function cancelOwnershipTransfer() external onlyOwner {
        if (pendingOwner == address(0)) revert NothingQueued();
        pendingOwner = address(0);
        emit OwnershipQueueCancelled();
    }

    // ─── Pool withdrawal (7-day timelock — visible rug-proof window) ──────────
    //
    // Every withdrawal is public knowledge 7 days in advance.
    // Any miner who disagrees can stop contributing to the pool.

    function queueWithdraw(uint256 amount) external onlyOwner {
        if (amount == 0 || amount > address(this).balance) revert InvalidAmount();
        pendingWithdrawAmount = amount;
        pendingWithdrawTo     = owner;
        pendingWithdrawAt     = block.timestamp + WITHDRAW_TIMELOCK;
        emit WithdrawalQueued(owner, amount, pendingWithdrawAt);
    }

    function executeWithdraw() external onlyOwner {
        if (pendingWithdrawAmount == 0)             revert NothingQueued();
        if (block.timestamp < pendingWithdrawAt)    revert TooEarly(pendingWithdrawAt, block.timestamp);
        uint256 amount = pendingWithdrawAmount;
        address to     = pendingWithdrawTo;
        pendingWithdrawAmount = 0;
        pendingWithdrawTo     = address(0);
        if (amount > address(this).balance) revert InsufficientPool();
        (bool ok,) = payable(to).call{value: amount}("");
        if (!ok) revert TransferFailed();
        emit Withdrawn(to, amount);
    }

    function cancelWithdraw() external onlyOwner {
        if (pendingWithdrawAmount == 0) revert NothingQueued();
        pendingWithdrawAmount = 0;
        pendingWithdrawTo     = address(0);
        emit WithdrawalQueueCancelled();
    }
}
