# 바탕화면에 "푸드벨 시작" / "푸드벨 저장" / "푸드벨 견적서" 바로가기(아이콘)를 만든다.
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

# 견적서는 인터넷 주소를 바로 여는 아이콘 (미리보기 서버를 안 켜도 열린다)
# .url 파일은 아이콘 경로의 한글이 깨져서, explorer 로 주소를 여는 .lnk 로 만든다.
function New-UrlLink($name, $url, $desc) {
    $lnk = $shell.CreateShortcut((Join-Path $desktop ($name + '.lnk')))
    $lnk.TargetPath = Join-Path $env:WINDIR 'explorer.exe'
    $lnk.Arguments = $url
    if (Test-Path $icon) { $lnk.IconLocation = "$icon,0" }
    $lnk.Description = $desc
    $lnk.Save()
    Write-Host ("  만듦: " + $name)
}

New-Link '푸드벨 시작' '시작.bat' '푸드벨 사이트 - 최신 받기 + 미리보기'
New-Link '푸드벨 저장' '저장.bat' '푸드벨 사이트 - GitHub 에 올리기'
New-UrlLink '푸드벨 견적서' 'https://parksangick-lgtm.github.io/-foodbell-site/sije-quote.html' '시제 상차림 견적서 - 편집 · 인쇄 · 고객에게 보내기'

Write-Host ''
Write-Host '바탕화면을 확인하세요. (F5 로 새로고침)'
