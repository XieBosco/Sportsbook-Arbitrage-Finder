<#
.SYNOPSIS
Launches Google Chrome with Remote Debugging enabled on port 19222 for CDP interception.
#>

param (
    [int]$Port = 19222,
    [string]$ProfileDir = "$env:TEMP\chrome_cdp_profile"
)

$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chromeExe = $null
foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        $chromeExe = $path
        break
    }
}

if (-not $chromeExe) {
    Write-Error "Google Chrome executable not found in default installation paths."
    exit 1
}

Write-Host "[*] Launching Chrome with CDP remote debugging on port $Port..." -ForegroundColor Green
Write-Host "    Executable: $chromeExe" -ForegroundColor Gray
Write-Host "    Profile   : $ProfileDir" -ForegroundColor Gray

Start-Process -FilePath $chromeExe -ArgumentList "--remote-debugging-port=$Port", "--user-data-dir=`"$ProfileDir`""
