#!/bin/bash

echo "🔗 连接到GitHub仓库..."

# 添加远程仓库（请确保GitHub上已创建仓库）
git remote add origin https://github.com/tonnylei0321/bank-code-intelligent-retrieval.git

# 验证远程仓库
git remote -v

# 设置主分支
git branch -M main

# 推送到GitHub
echo "🚀 开始推送..."
git push -u origin main

echo "✅ 推送完成！"
echo "🌐 访问您的仓库: https://github.com/tonnylei0321/bank-code-intelligent-retrieval"