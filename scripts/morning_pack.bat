@echo off
rem 毎朝、コーディクスの今日の完成画像から投稿パックを作り、OneDriveへコピーする（タスクスケジューラ用）
set PYTHONIOENCODING=utf-8
cd /d C:\Users\himic\tier-site
python scripts\make_post_pack.py >> C:\Users\himic\HIMEKA避難所\ティアる\投稿パック\_実行ログ.txt 2>&1
