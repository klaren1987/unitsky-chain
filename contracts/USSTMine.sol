// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title Unitsky String Technologies — Proof-of-Work mining pool
/// @notice Miners submit valid nonces and receive native UST from this contract.
contract USSTMine {
    uint256 public difficulty = 500_000;
    uint256 public reward = 1 ether;
    address public immutable owner;
    uint256 public totalMined;

    /// @dev Tracks nonces already claimed to prevent double-spending within the 10-block window.
    mapping(bytes32 => bool) private _usedWork;

    event Mined(address indexed miner, uint256 nonce, uint256 workBlock, uint256 amount);
    event FundAdded(address indexed sender, uint256 amount);
    event DifficultyChanged(uint256 oldDifficulty, uint256 newDifficulty);
    event RewardChanged(uint256 oldReward, uint256 newReward);

    error InvalidProof();
    error InsufficientPool();
    error NotOwner();
    error AlreadyClaimed();
    error TransferFailed();
    error DifficultyTooLow();
    error RewardTooLow();

    constructor() payable {
        owner = msg.sender;
    }

    receive() external payable {
        emit FundAdded(msg.sender, msg.value);
    }

    function fund() external payable {
        emit FundAdded(msg.sender, msg.value);
    }

    function poolBalance() external view returns (uint256) {
        return address(this).balance;
    }

    function target() public view returns (uint256) {
        return type(uint256).max / difficulty;
    }

    function verifyWork(
        address miner,
        uint256 nonce,
        uint256 workBlock
    ) public view returns (bool) {
        if (workBlock > block.number || block.number - workBlock > 10) {
            return false;
        }
        bytes32 hash = keccak256(abi.encodePacked(miner, nonce, workBlock));
        return uint256(hash) < target();
    }

    function mine(uint256 nonce, uint256 workBlock) external {
        bytes32 workKey = keccak256(abi.encodePacked(msg.sender, nonce, workBlock));
        if (_usedWork[workKey]) revert AlreadyClaimed();
        if (!verifyWork(msg.sender, nonce, workBlock)) revert InvalidProof();
        if (address(this).balance < reward) revert InsufficientPool();

        _usedWork[workKey] = true;
        totalMined += 1;

        (bool ok, ) = payable(msg.sender).call{value: reward}("");
        if (!ok) revert TransferFailed();

        emit Mined(msg.sender, nonce, workBlock, reward);
    }

    function setDifficulty(uint256 newDifficulty) external {
        if (msg.sender != owner) revert NotOwner();
        if (newDifficulty < 1) revert DifficultyTooLow();
        emit DifficultyChanged(difficulty, newDifficulty);
        difficulty = newDifficulty;
    }

    function setReward(uint256 newReward) external {
        if (msg.sender != owner) revert NotOwner();
        if (newReward == 0) revert RewardTooLow();
        emit RewardChanged(reward, newReward);
        reward = newReward;
    }

    /// @notice Emergency withdrawal by owner (e.g. to refund pool or redeploy).
    function withdrawOwner(uint256 amount) external {
        if (msg.sender != owner) revert NotOwner();
        if (amount > address(this).balance) revert InsufficientPool();
        (bool ok, ) = payable(owner).call{value: amount}("");
        if (!ok) revert TransferFailed();
    }
}
