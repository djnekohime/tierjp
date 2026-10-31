Set-Location C:\Users\himic\tier-site
$d = Get-Date -Format yyyy-MM-dd
$log = "C:\Users\himic\tier-site\daily\run_$d.log"
git pull --rebase 2>&1 | Out-File $log -Encoding utf8
$p = Get-Content C:\Users\himic\tier-site\daily\prompt.md -Raw -Encoding utf8
& C:\Users\himic\.local\bin\claude.exe -p $p --permission-mode acceptEdits --allowedTools "Bash" "Read" "Write" "Edit" "Glob" "Grep" "WebSearch" "WebFetch" 2>&1 | Out-File $log -Append -Encoding utf8
