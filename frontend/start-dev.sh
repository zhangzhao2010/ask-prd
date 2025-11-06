#!/bin/bash
# 前端开发服务器启动脚本

echo "🚀 启动 ASK-PRD 前端开发服务器..."
echo ""
echo "📍 当前目录: $(pwd)"
echo "📦 Node版本: $(node --version)"
echo "📦 npm版本: $(npm --version)"
echo ""

# 检查node_modules
if [ ! -d "node_modules" ]; then
  echo "⚠️  node_modules不存在，正在安装依赖..."
  npm install
fi

echo "✅ 依赖检查完成"
echo ""
echo "🌐 启动开发服务器..."
echo "   - 本地访问: http://localhost:3000"
echo "   - 网络访问: http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "⚙️  后端API地址: ${NEXT_PUBLIC_API_URL:-http://localhost:8000/api/v1}"
echo ""
echo "💡 提示："
echo "   - 按 Ctrl+C 停止服务器"
echo "   - 确保后端服务已启动（端口8000）"
echo ""

npm run dev
