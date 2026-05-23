param(
    [string]$RemoteUrl = 'https://github.com/GenX0Gravity/Hyper-Local-SMB-Dynamic-Pricing-Agent.git',
    [string]$Branch = 'feature/pricepulse-mvp'
)

# Usage: set env var $env:GITHUB_PAT = 'ghp_...'; then run ./scripts/push_to_github.ps1
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git is not installed or not in PATH"
    exit 1
}

if (-not $env:GITHUB_PAT) {
    Write-Host "Environment variable GITHUB_PAT not found."
    Write-Host "You can enter a Personal Access Token (scopes: repo) now, or press Enter to abort."
    $token = Read-Host -AsSecureString "Enter PAT (leave blank to abort)"
    if (-not $token) {
        Write-Error "No token supplied. Aborting."
        exit 1
    }
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($token)
    $plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
    $env:GITHUB_PAT = $plain
}

$token = $env:GITHUB_PAT
# Make a token-backed URL for one-time push
$remoteWithToken = $RemoteUrl -replace 'https://', "https://$token@"

# Ensure git identity
if (-not (git config user.name)) { git config user.name "PricePulse Bot" }
if (-not (git config user.email)) { git config user.email "devnull@example.com" }

# Create branch if not present
$curr = git rev-parse --abbrev-ref HEAD
if ($curr -ne $Branch) {
    git checkout -b $Branch
}

# Stage and commit changes
git add -A
try {
    git commit -m "MVP: orchestrator, langgraph agent, frontend Dockerfile, compose updates, README" -q
} catch {
    Write-Host "No new changes to commit or commit failed (it may already be committed). Continuing to push."
}

# Push to remote using token URL (will not save token in remote config)
Write-Host "Pushing branch $Branch to $RemoteUrl..."
$pushResult = & git push $remoteWithToken $Branch --set-upstream
if ($LASTEXITCODE -eq 0) {
    Write-Host "Push succeeded."
    exit 0
} else {
    Write-Error "Push failed. Exit code: $LASTEXITCODE"
    exit $LASTEXITCODE
}
