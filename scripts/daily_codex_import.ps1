# コーディクスの新しい完成画像を、ティアる。に取り込んで公開する（タスクスケジューラ用・1日2回）
# 流れ: completed.json から取り込み → ビルド確認 → codex/ og_codex/ に変化があれば commit & push
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$log = 'C:\Users\himic\HIMEKA避難所\ティアる\投稿パック\_取り込みログ.txt'
Set-Location 'C:\Users\himic\tier-site'
function L($m) { Add-Content -Path $log -Value $m -Encoding utf8 }
L "==== $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
python scripts\import_codex.py 2>&1 | Select-Object -Last 3 | ForEach-Object { L $_ }
$b = python build.py 2>&1
if ($LASTEXITCODE -ne 0) { L 'ビルド失敗のため公開しません'; exit 1 }
git add codex og_codex
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) { L '新しい画像なし'; exit 0 }
git commit -q -m 'Codex完成画像を追加（自動取り込み）' -m 'Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>' 2>&1 | ForEach-Object { L $_ }
git pull --rebase -q 2>&1 | ForEach-Object { L $_ }
git push 2>&1 | ForEach-Object { L $_ }
L '公開しました'
