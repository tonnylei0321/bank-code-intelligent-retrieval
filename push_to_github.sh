#!/bin/bash

echo "🚀 开始推送到GitHub..."

# 添加远程仓库
git remote add origin https://github.com/tonnylei0321/bank-code-intelligent-retrieval.git

# 设置主分支名称
git branch -M main

# 推送代码到GitHub
git push -u origin main

echo "✅ 推送完成！"
echo "🌐 访问您的仓库: https://github.com/tonnylei0321/bank-code-intelligent-retrieval"