# Prepare Chainlist PR for UST Network (778889).
# Requires: gh auth login

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  Write-Error "Install GitHub CLI: https://cli.github.com/"
  exit 1
}

gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Run: gh auth login"
  exit 1
}

$tmpdir = Join-Path $env:TEMP "chainlist-ust-$(Get-Random)"
git clone --depth 1 https://github.com/DefiLlama/chainlist.git $tmpdir
Copy-Item "chainlist/chainid-778889.js" "$tmpdir/constants/additionalChainRegistry/chainid-778889.js"
Set-Location $tmpdir
git checkout -b add-ust-778889
git add constants/additionalChainRegistry/chainid-778889.js
git commit -m "Add UST Network (778889)"
gh pr create --title "Add UST Network (778889)" --body @"
## Summary
- Chain ID 778889 — UST Network (UST)
- HTTPS RPC: https://147-45-143-23.sslip.io/rpc
- Explorer: https://147-45-143-23.sslip.io

## Test plan
- [ ] eth_chainId returns 0xbe289
- [ ] HTTPS RPC responds
"@

Write-Host "Done. Clean up: Remove-Item -Recurse -Force $tmpdir"
