git reset --hard HEAD
git clean -fd
pkill -f bot.py && python3 bot.py


git add .
git commit -m "Your commit message"
git push