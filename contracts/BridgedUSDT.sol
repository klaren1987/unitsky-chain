// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title BridgedUSDT — Tether USD bridged to Chain 778889
///
/// Operator (bridge relayer) watches Ethereum mainnet for USDT deposits to
/// the bridge treasury wallet, then calls bridgeMint() here.
/// To withdraw back to Ethereum, user calls bridgeBurn() — the relayer
/// detects the BridgeWithdraw event and sends real USDT on Ethereum.
///
contract BridgedUSDT {

    string  public constant name     = "Bridged USDT";
    string  public constant symbol   = "USDT";
    uint8   public constant decimals = 6;   // matches real Tether (6 decimals)

    uint256 public totalSupply;
    address public operator;            // bridge relayer — can mint
    address public pendingOperator;     // two-step operator transfer

    mapping(address => uint256)                     public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    /// @notice Emitted when relayer mints tokens after detecting Ethereum deposit
    event BridgeDeposit(address indexed to, uint256 amount, bytes32 indexed ethTxHash);
    /// @notice Emitted when user burns tokens to request withdrawal to Ethereum
    event BridgeWithdraw(address indexed from, uint256 amount, string ethAddress);

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event OperatorTransferStarted(address indexed newOperator);
    event OperatorTransferred(address indexed oldOperator, address indexed newOperator);

    error NotOperator();
    error ZeroAddress();
    error InsufficientBalance();
    error InsufficientAllowance();
    error AlreadyProcessed();
    error InvalidAmount();

    /// Ethereum deposit tx hash → already processed (dedup guard)
    mapping(bytes32 => bool) public processedDeposits;

    constructor(address _operator) {
        if (_operator == address(0)) revert ZeroAddress();
        operator = _operator;
    }

    // ─── ERC-20 core ────────────────────────────────────────────────────────

    function transfer(address to, uint256 amount) external returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 allowed = allowance[from][msg.sender];
        if (allowed != type(uint256).max) {
            if (allowed < amount) revert InsufficientAllowance();
            allowance[from][msg.sender] = allowed - amount;
        }
        _transfer(from, to, amount);
        return true;
    }

    function _transfer(address from, address to, uint256 amount) internal {
        if (to == address(0)) revert ZeroAddress();
        if (balanceOf[from] < amount) revert InsufficientBalance();
        balanceOf[from] -= amount;
        balanceOf[to]   += amount;
        emit Transfer(from, to, amount);
    }

    // ─── Bridge: deposit (Ethereum → Chain 778889) ──────────────────────────

    /// @notice Called by relayer after detecting real USDT deposit on Ethereum.
    /// @param to         Recipient on Chain 778889
    /// @param amount     Amount in 6-decimal units (same as Tether)
    /// @param ethTxHash  Ethereum tx hash — prevents double-processing
    function bridgeMint(address to, uint256 amount, bytes32 ethTxHash) external {
        if (msg.sender != operator) revert NotOperator();
        if (to == address(0)) revert ZeroAddress();
        if (amount == 0) revert InvalidAmount();
        if (processedDeposits[ethTxHash]) revert AlreadyProcessed();
        processedDeposits[ethTxHash] = true;
        totalSupply      += amount;
        balanceOf[to]    += amount;
        emit Transfer(address(0), to, amount);
        emit BridgeDeposit(to, amount, ethTxHash);
    }

    // ─── Bridge: withdrawal (Chain 778889 → Ethereum) ───────────────────────

    /// @notice Burn BridgedUSDT and request real USDT back on Ethereum.
    /// @param amount     Amount in 6-decimal units
    /// @param ethAddress Your Ethereum address to receive USDT
    function bridgeBurn(uint256 amount, string calldata ethAddress) external {
        if (amount == 0) revert InvalidAmount();
        if (balanceOf[msg.sender] < amount) revert InsufficientBalance();
        balanceOf[msg.sender] -= amount;
        totalSupply           -= amount;
        emit Transfer(msg.sender, address(0), amount);
        emit BridgeWithdraw(msg.sender, amount, ethAddress);
    }

    // ─── Operator transfer (two-step) ────────────────────────────────────────

    function transferOperator(address newOperator) external {
        if (msg.sender != operator) revert NotOperator();
        if (newOperator == address(0)) revert ZeroAddress();
        pendingOperator = newOperator;
        emit OperatorTransferStarted(newOperator);
    }

    function acceptOperator() external {
        if (msg.sender != pendingOperator) revert NotOperator();
        emit OperatorTransferred(operator, pendingOperator);
        operator        = pendingOperator;
        pendingOperator = address(0);
    }
}
