# 🚀 并行训练数据生成系统使用指南

## 📋 系统概述

本系统使用多线程和多个LLM API并行生成大规模银行训练数据，专为处理15万条样本数据设计，每条样本生成7个训练样本，总计105万条训练数据。

### 🎯 核心特性

- **多LLM并行**: 同时使用阿里通义千问、DeepSeek等多个API
- **多线程处理**: 每个LLM使用4个线程并发处理，总共8个线程
- **数据库优化**: 批量写入，提高存储效率
- **进度监控**: 实时查看生成进度和性能指标
- **错误恢复**: 自动重试和备用方案
- **内存优化**: 避免内存溢出，支持大规模数据处理

### 📊 性能指标

- **处理速度**: 预计每分钟处理100-200个银行
- **生成效率**: 每个银行7个样本，平均2-3秒
- **并发能力**: 8个线程同时工作
- **API限制**: 每个API每分钟100次请求

## 🛠️ 快速开始

### 1. 环境检查

```bash
# 检查Python版本
python3 --version

# 安装依赖
python3 -m pip install aiohttp asyncio

# 测试LLM API连接
python3 test_llm_apis.py
```

### 2. 启动生成

#### 方式一：使用快速启动脚本（推荐）

```bash
# 给脚本执行权限
chmod +x quick_start_generation.sh

# 启动脚本
./quick_start_generation.sh
```

#### 方式二：直接运行Python脚本

```bash
# 测试模式（处理1000个银行）
python3 start_parallel_generation.py

# 生产模式（处理所有银行）
python3 start_parallel_generation.py --production
```

### 3. 监控进度

```bash
# 启动进度监控
python3 monitor_generation.py

# 监控特定数据集
python3 monitor_generation.py <dataset_id>

# 自定义刷新间隔（秒）
python3 monitor_generation.py <dataset_id> 10
```

## 📁 文件说明

### 核心文件

- `parallel_training_generator.py` - 主要生成器类
- `start_parallel_generation.py` - 启动脚本
- `monitor_generation.py` - 进度监控脚本
- `test_llm_apis.py` - API连接测试
- `llm_config.json` - LLM配置文件

### 配置文件

- `llm_config.json` - LLM API配置和生成参数
- `quick_start_generation.sh` - 快速启动脚本

### 日志文件

- `parallel_generation_*.log` - 生成过程日志
- `logs/generation_*.log` - 后台运行日志

## ⚙️ 配置说明

### LLM配置

编辑 `llm_config.json` 文件：

```json
{
  "llm_configs": [
    {
      "name": "阿里通义千问",
      "base_url": "https://dashscope.aliyuncs.com/api/v1/services/aigc",
      "api_key": "your-api-key",
      "model_name": "qwen-turbo",
      "max_requests_per_minute": 100,
      "enabled": true
    }
  ],
  "generation_settings": {
    "samples_per_bank": 7,
    "max_workers": 12,
    "batch_size": 100
  }
}
```

### 性能调优

- `max_workers`: 总线程数（建议12-16）
- `batch_size`: 数据库批量写入大小（建议100-200）
- `max_requests_per_minute`: API请求频率限制
- `timeout_seconds`: API请求超时时间

## 📊 监控界面

监控脚本提供实时信息：

```
🚀 训练数据生成监控
================================================================================
数据集: 大规模银行训练数据集_20260130_143022
开始时间: 2026-01-30 14:30:22
当前时间: 2026-01-30 14:45:15
================================================================================
📊 进度统计
总银行数: 150,000
已处理银行: 12,500
生成样本数: 87,500
完成进度: 8.33%
进度条: [████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 8.3%
--------------------------------------------------------------------------------
⚡ 性能指标
样本生成速度: 98.50 样本/秒
银行处理速度: 14.07 银行/分钟
区间速度: 102.30 样本/秒
运行时间: 14.9 分钟
预计完成时间: 2026-01-30 22:15:30
剩余时间: 457.8 分钟
--------------------------------------------------------------------------------
📈 质量指标
平均每银行样本数: 7.00
✅ 样本生成质量正常
================================================================================
```

## 🔧 故障排除

### 常见问题

1. **API连接失败**
   ```bash
   # 测试API连接
   python3 test_llm_apis.py
   
   # 检查网络连接
   curl -I https://api.deepseek.com
   ```

2. **内存不足**
   ```bash
   # 减少并发线程数
   # 编辑 llm_config.json，降低 max_workers
   ```

3. **数据库连接错误**
   ```bash
   # 检查数据库文件权限
   ls -la data/
   
   # 重启数据库连接
   # 重新运行生成脚本
   ```

4. **生成速度慢**
   ```bash
   # 检查API响应时间
   python3 test_llm_apis.py
   
   # 调整并发参数
   # 编辑 llm_config.json
   ```

### 错误代码

- `404`: API端点或模型不存在
- `429`: API请求频率超限
- `500`: API服务器内部错误
- `timeout`: 请求超时

### 恢复操作

1. **中断恢复**
   - 系统支持断点续传
   - 重新启动会跳过已生成的银行

2. **数据验证**
   ```bash
   # 检查生成的数据
   python3 -c "
   from app.core.database import get_db
   from app.models.qa_pair import QAPair
   db = next(get_db())
   count = db.query(QAPair).count()
   print(f'已生成样本数: {count:,}')
   "
   ```

## 📈 性能优化建议

### 硬件要求

- **CPU**: 8核以上推荐
- **内存**: 16GB以上推荐
- **网络**: 稳定的互联网连接
- **存储**: SSD推荐，至少10GB可用空间

### 软件优化

1. **并发调优**
   - 根据CPU核心数调整线程数
   - 监控系统资源使用情况

2. **网络优化**
   - 使用稳定的网络连接
   - 考虑使用代理提高API访问速度

3. **数据库优化**
   - 定期清理日志文件
   - 使用SSD存储数据库文件

## 🎯 最佳实践

### 生产环境部署

1. **后台运行**
   ```bash
   nohup python3 start_parallel_generation.py > generation.log 2>&1 &
   ```

2. **定期监控**
   ```bash
   # 设置定时任务检查进度
   crontab -e
   # 添加: */10 * * * * python3 /path/to/monitor_generation.py --check
   ```

3. **日志管理**
   ```bash
   # 定期清理日志
   find logs/ -name "*.log" -mtime +7 -delete
   ```

### 数据质量保证

1. **样本验证**
   - 定期检查生成样本的质量
   - 监控平均每银行样本数

2. **错误处理**
   - 记录失败的银行记录
   - 手动处理特殊情况

3. **数据备份**
   ```bash
   # 定期备份数据库
   cp data/bank_code.db data/backup/bank_code_$(date +%Y%m%d).db
   ```

## 📞 技术支持

如遇到问题，请：

1. 查看日志文件获取详细错误信息
2. 运行 `python3 test_llm_apis.py` 检查API状态
3. 检查系统资源使用情况
4. 参考本文档的故障排除部分

---

**预计处理时间**: 15万条银行数据预计需要8-12小时完成
**最终输出**: 105万条高质量训练样本