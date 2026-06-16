from solcx import compile_files, install_solc, set_solc_version
install_solc('0.8.20')
set_solc_version('0.8.20')

compiled = compile_files(['/app/contracts/BridgedUSDT.sol'], output_values=['bin', 'bin-runtime', 'abi'], evm_version='paris')
for k, v in compiled.items():
    if ':BridgedUSDT' in k:
        bc = v['bin']
        rt = v['bin-runtime']
        print('Deploy bytecode len:', len(bc)//2, 'bytes')
        print('Runtime bytecode len:', len(rt)//2, 'bytes')
        print('Deploy[0:40]:', bc[:40])
        # PC 387 = byte offset 387 = hex offset 774
        print('Deploy[387*2:410*2] (PUSH2 area):', bc[774:820])
        # check if bytecode ends correctly
        print('Last 10 bytes:', bc[-20:])
        
        # Also try without evm_version
        break

# Also compile without evm_version
compiled2 = compile_files(['/app/contracts/BridgedUSDT.sol'], output_values=['bin', 'bin-runtime'])
for k, v in compiled2.items():
    if ':BridgedUSDT' in k:
        bc2 = v['bin']
        rt2 = v['bin-runtime']
        print('\n--- Without evm_version ---')
        print('Deploy bytecode len:', len(bc2)//2, 'bytes')
        print('Runtime bytecode len:', len(rt2)//2, 'bytes')
        print('Same bytecode?', bc == bc2)
        break
