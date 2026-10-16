# 사무실 PC 에 "푸드벨 시제 PDF" 를 작업 스케줄러로 등록한다 — 윈도우에 로그온하면 저절로 시작.
# 하는 일: 5분마다 바뀐 행사 PDF, 하루 한 번 백업 엑셀 (tools\sije_web\office_agent.py).
# 실행: 이 파일을 오른쪽 클릭 → "PowerShell 에서 실행" (한 번만). 다시 실행하면 덮어쓴다.
# 미리 필요한 것: python -m pip install -r tools\sije_web\requirements.txt · python -m playwright install chromium
#                · 관리자 열쇠 C:\foodbell-keys\sije-admin.json

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$name = '푸드벨 시제 PDF'

$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) { throw 'pythonw.exe 를 찾지 못했습니다 — 파이썬을 먼저 설치하세요.' }
if (-not (Test-Path 'C:\foodbell-keys\sije-admin.json')) { throw '열쇠 파일이 없습니다: C:\foodbell-keys\sije-admin.json' }

$action = New-ScheduledTaskAction -Execute $pythonw -Argument '-m tools.sije_web.office_agent' -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings `
    -Description '시제행사 내역서 PDF 자동 · 하루 한 번 백업 (푸드벨)' -Force | Out-Null

Write-Host "등록했습니다: $name  (시작 위치 $repo)" -ForegroundColor Green
Write-Host '지금 바로 시작하려면: Start-ScheduledTask -TaskName ''푸드벨 시제 PDF'''
Write-Host "기록 파일: $env:LOCALAPPDATA\foodbell-sije\agent.log"
