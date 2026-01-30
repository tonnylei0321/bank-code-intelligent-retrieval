"""
日志配置模块

使用loguru库配置应用日志系统，提供：
1. 彩色控制台输出（开发环境友好）
2. 文件日志输出（支持按日期轮转）
3. 错误日志单独记录
4. 自动压缩历史日志
5. 可配置的日志级别

日志文件保存在logs/目录下：
- app_YYYY-MM-DD.log: 所有级别的日志
- error_YYYY-MM-DD.log: 仅错误日志
"""
import sys
from pathlib import Path
from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """
    配置应用日志系统
    
    配置内容：
    1. 控制台输出：彩色格式化，便于开发调试
    2. 文件输出：按日期轮转，保留30天
    3. 错误日志：单独文件，保留90天
    4. 自动压缩：历史日志自动压缩为zip格式
    
    日志级别由配置文件中的LOG_LEVEL控制（DEBUG/INFO/WARNING/ERROR）
    """
    # 移除默认的日志处理器
    logger.remove()
    
    # 添加控制台处理器（彩色输出）
    # 格式：时间 | 级别 | 模块:函数:行号 - 消息
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,  # 使用配置的日志级别
        colorize=True  # 启用彩色输出
    )
    
    # 创建日志目录（如果不存在）
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 添加文件处理器（按日期轮转）
    # 记录所有级别的日志，每天午夜轮转，保留30天
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",  # 文件记录所有DEBUG及以上级别的日志
        rotation="00:00",  # 每天午夜轮转日志文件
        retention="30 days",  # 保留最近30天的日志
        compression="zip"  # 压缩旧日志文件
    )
    
    # 添加错误日志处理器
    # 单独记录ERROR级别的日志，保留时间更长（90天）
    logger.add(
        "logs/error_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",  # 仅记录ERROR级别的日志
        rotation="00:00",  # 每天午夜轮转
        retention="90 days",  # 错误日志保留更长时间
        compression="zip"  # 压缩旧日志
    )
    
    logger.info(f"日志系统已配置 - 日志级别: {settings.LOG_LEVEL}")


# 导出logger和setup_logging供其他模块使用
# 使用方式：from app.core.logging import logger
__all__ = ["logger", "setup_logging"]
