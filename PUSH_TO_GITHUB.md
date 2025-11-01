# GitHub এ Push করার জন্য

## Option 1: যদি GitHub repo already তৈরি থাকে

```bash
# আপনার GitHub repo URL দিয়ে remote add করুন
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push করুন
git branch -M main
git push -u origin main
```

## Option 2: নতুন repo তৈরি করতে হবে

1. https://github.com/new এ যান
2. Repository name দিন: `badshah-trading-bot`
3. Create repository করুন (README, .gitignore, license add করবেন না)
4. তারপর commands run করুন:

```bash
git remote add origin https://github.com/YOUR_USERNAME/badshah-trading-bot.git
git branch -M main
git push -u origin main
```

## Render Auto-Deploy

Render এ auto-deploy enable থাকলে push করার সাথে সাথে automatically deploy হয়ে যাবে! 🚀

