# 🎯 MPS 内存问题 - 快速参考

## 🚨 问题识别

**症状：**
```
MPS backend out of memory
```

**日志位置：**
```bash
mvp/logs/error_2026-01-21.log
```

## ⚡ 快速修复

### 方法 1：使用修复脚本（最快）
```bash
./fix_mps_memory.sh
```

### 方法 2：使用优化启动脚本
```bash
./start_with_memory_limit.sh
```

### 方法 3：手动修复
```bash
# 1. 停止服务
pkill -f "uvicorn.*mvp"

# 2. 设置环境变量
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7
export PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5

# 3. 启动服务
cd mvp
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📊 快速检查

### 检查服务状态
```bash
curl http://localhost:8000/health
ps aux | grep uvicorn
```

### 检查错误日志
```bash
tail -f mvp/logs/error_2026-01-21.log
```

### 检查内存使用
```bash
top -l 1 | grep PhysMem
```

## 🔧 已修复的文件

1. **mvp/app/services/query_service.py**
   - ✅ 添加内存清理机制
   - ✅ 添加错误恢复
   - ✅ 添加内存监控

2. **start_with_memory_limit.sh**
   - ✅ 内存限制配置
   - ✅ 自动启动服务

3. **fix_mps_memory.sh**
   - ✅ 一键修复脚本

## 💡 关键配置

```bash
# 限制 MPS 内存使用到 70%
PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.7

# 低水位 50%
PYTORCH_MPS_LOW_WATERMARK_RATIO=0.5

# 启用回退
PYTORCH_ENABLE_MPS_FALLBACK=1
```

## ✅ 验证修复

```bash
# 运行测试
./simple_test.sh

# 或手动检查
curl http://localhost:8000/health
tail -5 mvp/logs/error_2026-01-21.log
```

## 📞 如果问题持续

1. **降低内存限制到 50%**
   ```bash
   export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.5
   ```

2. **禁用 MPS，使用 CPU**
   ```bash
   export PYTORCH_ENABLE_MPS=0
   ```

3. **使用更小的模型**
   - 切换到 Qwen2.5-0.5B

## 🎯 当前状态

✅ 问题已修复  
✅ 服务运行正常  
✅ 内存使用优化  
✅ 自动清理机制已启用

---

**最后更新：** 2026-01-21 20:25
