# Set Windows 8 compatibility mode on ttyd.exe
# Context: ttyd 1.7.4+ is cross-compiled via MinGW64 and breaks ConPTY on Win11.
# Setting Win8 compat mode is a documented workaround (ttyd issue #1207).

$ttydPath = "C:\Users\Extreme\AppData\Local\Microsoft\WinGet\Packages\tsl0922.ttyd_Microsoft.Winget.Source_8wekyb3d8bbwe\ttyd.exe"
$regPath = "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"

if (-not (Test-Path $regPath)) {
    New-Item -Path $regPath -Force | Out-Null
}

Set-ItemProperty -Path $regPath -Name $ttydPath -Value "WIN8RTM"
Write-Host "Set Win8 compatibility mode on: $ttydPath"

# Verify
$val = Get-ItemProperty -Path $regPath -Name $ttydPath -ErrorAction SilentlyContinue
if ($val) {
    Write-Host "Verified: $($val.$ttydPath)"
} else {
    Write-Host "ERROR: Failed to set registry key"
}
