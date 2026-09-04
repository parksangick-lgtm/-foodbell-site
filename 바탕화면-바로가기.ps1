# 바탕화면에 "푸드벨 시작" / "푸드벨 저장" 바로가기(아이콘)를 만든다.
# 바탕화면-바로가기.bat 이 이 파일을 실행한다. 각 컴퓨터에서 한 번만 하면 된다.

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktop = [Environment]::GetFolderPath('Desktop')
$icon = Join-Path $repo '아이콘.ico'
$shell = New-Object -ComObject WScript.Shell

function New-Link($name, $bat, $desc) {
    $lnk = $shell.CreateShortcut((Join-Path $desktop ($name + '.lnk')))
    $lnk.TargetPath = Join-Path $repo $bat
    $lnk.WorkingDirectory = $repo
    if (Test-Path $icon) { $lnk.IconLocation = "$icon,0" }
    $lnk.Description = $desc
    $lnk.Save()
    Write-Host ("  만듦: " + $name)
}

New-Link '푸드벨 시작' '시작.bat' '푸드벨 사이트 - 최신 받기 + 미리보기'
New-Link '푸드벨 저장' '저장.bat' '푸드벨 사이트 - GitHub 에 올리기'

Write-Host ''
Write-Host '바탕화면을 확인하세요. (F5 로 새로고침)'
