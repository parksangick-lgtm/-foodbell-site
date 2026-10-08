# Append one folder to the USER Path without expanding %VARIABLES% or changing the value kind.
# [Environment]::SetEnvironmentVariable('Path', ..., 'User') rewrites the value as REG_SZ with
# every %USERPROFILE% already expanded - a silent change nobody asked for.
# Default is a dry run. Add -Apply to write. A backup of the old value goes to %TEMP%.
#   powershell -NoProfile -ExecutionPolicy Bypass -File add-user-path.ps1 -Add 'C:\flutter\bin'
#   powershell -NoProfile -ExecutionPolicy Bypass -File add-user-path.ps1 -Add 'C:\flutter\bin' -Apply
param([string]$Add = 'C:\flutter\bin', [switch]$Apply)

$key = Get-Item 'HKCU:\Environment'
$raw = $key.GetValue('Path', '', 'DoNotExpandEnvironmentNames')
$kind = 'None'
if ($key.GetValueNames() -contains 'Path') { $kind = $key.GetValueKind('Path') }
Write-Output "kind:    $kind"
Write-Output "current: $raw"

$parts = @($raw -split ';' | Where-Object { $_ -ne '' })
$norm = $parts | ForEach-Object { $_.TrimEnd('\') }
if ($norm -contains $Add.TrimEnd('\')) {
  Write-Output "already present: $Add (nothing to do)"
  exit 0
}

$new = (@($parts) + $Add) -join ';'
Write-Output "new:     $new"
if (-not $Apply) {
  Write-Output 'DRY RUN - nothing written. Add -Apply to write.'
  exit 0
}

$backup = Join-Path $env:TEMP ('user-path-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.txt')
Set-Content -Path $backup -Value $raw -Encoding UTF8
New-ItemProperty -Path 'HKCU:\Environment' -Name 'Path' -Value $new -PropertyType ExpandString -Force | Out-Null
Write-Output "written as ExpandString. backup: $backup"
Write-Output 'Open a NEW terminal / restart VS Code to pick it up.'
