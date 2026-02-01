# Redis集成使用指南

## 概述

本项目已完全集成Redis缓存系统，为智能问答提供高性能的数据存储和检索支持。

## Redis集成功能

### 1. 自动化管理
- ✅ 启动脚本自动检查和启动Redis
- ✅ 清理脚本包含Redis停止和数据清理
- ✅ 专用Redis管理脚本

### 2. 数据缓存
- ✅ 银行数据的Redis缓存存储
- ✅ 多种索引（名称、联行号、关键词）
- ✅ 批量数据加载和同步
- ✅ 自动过期和内存管理

### 3. 智能检索
- ✅ 毫秒级精确匹配
- ✅ 模糊搜索支持
- ✅ 多策略检索整合
- ✅ 缓存命中率优化

## 使用方法

### 1. 启动系统（包含Redis）

```bash
# 使用增强的启动脚本
./mvp/start_intelligent_qa.sh

# 或使用清理重启脚本
./cleanup_and_restart.sh
```

### 2. Redis管理

```bash
# 查看Redis状态
./redis_manager.sh status

# 启动Redis
./redis_manager.sh start

# 停止Redis
./redis_manager.sh stop

# 重启Redis
./redis_manager.sh restart

# 查看详细信息
./redis_manager.sh info

# 性能测试
./redis_manager.sh test

# 备份数据
./redis_manager.sh backup

# 清空数据
./redis_manager.sh clean
```

### 3. API接口使用

#### 加载银行数据到Redis
```bash
curl -X POST "http://localhost:8000/api/redis/load-data" \
  -H "Authorization: Bearer <token>"
```

#### 搜索银行信息
```bash
curl "http://localhost:8000/api/redis/search?query=工商银行&search_type=name&limit=10" \
  -H "Authorization: Bearer <token>"
```

#### 获取Redis统计信息
```bash
curl "http://localhost:8000/api/redis/stats" \
  -H "Authorization: Bearer <token>"
```

#### 智能问答（使用Redis缓存）
```bash
curl -X POST "http://localhost:8000/api/intelligent-qa/ask" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"question": "工商银行西单支行联行号", "retrieval_strategy": "redis_only"}'
```

## 配置说明

### 环境变量配置

```env
# Redis连接配置
REDIS_URL=redis://localhost:6379/0
REDIS_CONNECTION_TIMEOUT=10
REDIS_SOCKET_TIMEOUT=5
REDIS_MAX_CONNECTIONS=20

# Redis数据管理
REDIS_KEY_PREFIX=bank_code:
REDIS_DEFAULT_TTL=86400
REDIS_BATCH_SIZE=1000

# 智能问答Redis配置
QA_REDIS_SEARCH_LIMIT=10
QA_CACHE_ANSWERS=true
QA_CACHE_TTL=3600
```

### Redis数据结构

```
bank_code:bank:123        # 银行详细信息 (Hash)
bank_code:name:工商银行     # 名称索引 (String -> ID)
bank_code:code:102100099996 # 联行号索引 (String -> ID)
bank_code:keyword:工行      # 关键词索引 (Set of IDs)
bank_code:stats           # 统计信息 (Hash)
bank_code:count           # 总数量 (String)
```

## 性能优化

### 1. 内存优化
- 使用Hash结构存储银行数据
- 设置合理的TTL避免内存溢出
- 批量操作减少网络开销

### 2. 检索优化
- 多级索引提高查询速度
- 关键词预处理和标准化
- 结果缓存减少重复计算

### 3. 连接优化
- 连接池管理
- 异步操作支持
- 自动重连机制

## 监控和维护

### 1. 状态监控

```bash
# 检查Redis状态
./redis_manager.sh status

# 查看详细信息
./redis_manager.sh info

# 监控Redis日志
tail -f /var/log/redis/redis-server.log
```

### 2. 性能监控

```bash
# Redis性能测试
./redis_manager.sh test

# 查看内存使用
redis-cli info memory

# 查看连接数
redis-cli info clients

# 查看命令统计
redis-cli info commandstats
```

### 3. 数据管理

```bash
# 查看键数量
redis-cli dbsize

# 查看特定模式的键
redis-cli keys "bank_code:*"

# 查看键的过期时间
redis-cli ttl "bank_code:bank:123"

# 手动清理过期键
redis-cli eval "return redis.call('del', unpack(redis.call('keys', ARGV[1])))" 0 "bank_code:temp:*"
```

## 故障排除

### 常见问题

1. **Redis连接失败**
   ```bash
   # 检查Redis是否运行
   ./redis_manager.sh status
   
   # 检查端口占用
   lsof -i:6379
   
   # 重启Redis
   ./redis_manager.sh restart
   ```

2. **内存不足**
   ```bash
   # 查看内存使用
   redis-cli info memory
   
   # 清理过期数据
   redis-cli eval "return #redis.call('keys', '*')" 0
   
   # 设置内存限制
   redis-cli config set maxmemory 256mb
   ```

3. **性能问题**
   ```bash
   # 查看慢查询
   redis-cli slowlog get 10
   
   # 监控命令执行
   redis-cli monitor
   
   # 性能测试
   ./redis_manager.sh test
   ```

### 数据恢复

```bash
# 备份数据
./redis_manager.sh backup

# 从备份恢复
redis-cli shutdown
cp redis_backups/redis_backup_20260201_120000.rdb /var/lib/redis/dump.rdb
./redis_manager.sh start
```

## 集成测试

### 1. 基础功能测试

```bash
# 运行简单测试
python mvp/test_intelligent_qa_simple.py

# 测试Redis连接
redis-cli ping

# 测试数据加载
curl -X POST "http://localhost:8000/api/redis/load-data" \
  -H "Authorization: Bearer <token>"
```

### 2. 性能测试

```bash
# Redis性能测试
./redis_manager.sh test

# 智能问答性能测试
python mvp/test_intelligent_qa_performance.py
```

### 3. 集成测试

```bash
# 完整系统测试
python mvp/scripts/init_intelligent_qa.py

# API端点测试
curl "http://localhost:8000/api/redis/health" \
  -H "Authorization: Bearer <token>"
```

## 最佳实践

### 1. 数据管理
- 定期备份Redis数据
- 监控内存使用情况
- 设置合理的过期时间
- 使用批量操作提高效率

### 2. 性能优化
- 选择合适的数据结构
- 避免大键值对
- 使用管道减少网络延迟
- 合理配置连接池

### 3. 安全考虑
- 限制Redis访问IP
- 使用密码认证
- 定期更新Redis版本
- 监控异常访问

## 脚本说明

### cleanup_and_restart.sh 增强功能
- ✅ 自动停止Redis服务
- ✅ 可选的Redis数据清理
- ✅ Redis服务重启
- ✅ Redis状态检查和测试
- ✅ 环境变量设置

### redis_manager.sh 专用功能
- ✅ Redis服务启动/停止/重启
- ✅ 状态检查和信息显示
- ✅ 性能测试和基准测试
- ✅ 数据备份和恢复
- ✅ 数据清理和维护

### start_intelligent_qa.sh 集成功能
- ✅ 自动检查和启动Redis
- ✅ 依赖检查和安装
- ✅ 环境配置验证
- ✅ 基础功能测试
- ✅ 系统初始化选项

## 总结

Redis已完全集成到智能问答系统中，提供：

1. **高性能缓存**: 毫秒级数据访问
2. **智能检索**: 多策略数据检索
3. **自动管理**: 一键启动和维护
4. **完整监控**: 状态监控和性能分析
5. **故障恢复**: 备份恢复和错误处理

通过这些脚本和配置，您可以轻松管理Redis服务，充分发挥智能问答系统的性能优势。

---

**更新时间**: 2026-02-01  
**版本**: 1.0.0  
**状态**: ✅ 完成