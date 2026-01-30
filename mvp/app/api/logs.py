"""
Logs API Endpoints - 日志查询API端点

本模块提供应用日志查询相关的API端点。

端点列表：
    - GET /logs: 查询应用日志（支持筛选和分页）
    - GET /logs/files: 列出可用的日志文件

功能特性：
    - 日志文件解析：自动解析loguru格式的日志文件
    - 多维度筛选：支持按时间、级别、任务ID、关键词筛选
    - 分页支持：支持大量日志的分页查询
    - 实时查询：查询最新的日志文件

筛选参数：
    - start_time: 开始时间（ISO格式）
    - end_time: 结束时间（ISO格式）
    - level: 日志级别（INFO, WARNING, ERROR）
    - task_id: 训练任务ID
    - search: 关键词搜索

权限要求：
    - 仅管理员可以访问日志

日志格式：
    2026-01-10 12:34:56 | INFO     | module:function:123 - message

使用示例：
    >>> # 查询最近的错误日志
    >>> response = requests.get(
    ...     "http://localhost:8000/logs?level=ERROR&page=1&page_size=50",
    ...     headers={"Authorization": f"Bearer {admin_token}"}
    ... )
    >>> 
    >>> # 查询特定训练任务的日志
    >>> response = requests.get(
    ...     "http://localhost:8000/logs?task_id=1",
    ...     headers={"Authorization": f"Bearer {admin_token}"}
    ... )
    >>> 
    >>> # 列出所有日志文件
    >>> response = requests.get(
    ...     "http://localhost:8000/logs/files",
    ...     headers={"Authorization": f"Bearer {admin_token}"}
    ... )
"""
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.deps import get_db, get_current_user
from app.core.permissions import require_admin
from app.models.user import User


router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


class LogEntry(BaseModel):
    """Log entry model"""
    timestamp: str
    level: str
    module: str
    function: str
    line: int
    message: str


class LogsResponse(BaseModel):
    """Logs query response"""
    total: int
    page: int
    page_size: int
    logs: List[LogEntry]


class LogFilter(BaseModel):
    """Log filter parameters"""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    level: Optional[str] = None
    task_id: Optional[int] = None
    search: Optional[str] = None


def parse_log_line(line: str) -> Optional[LogEntry]:
    """
    Parse a log line into LogEntry
    
    Expected format:
    2026-01-10 12:34:56 | INFO     | module:function:123 - message
    
    Args:
        line: Log line string
    
    Returns:
        LogEntry or None if parsing fails
    """
    try:
        # Split by pipe separator
        parts = line.split(" | ")
        if len(parts) < 4:
            return None
        
        timestamp = parts[0].strip()
        level = parts[1].strip()
        location = parts[2].strip()
        message = parts[3].strip()
        
        # Parse location (module:function:line)
        location_parts = location.split(":")
        if len(location_parts) >= 3:
            module = location_parts[0]
            function = location_parts[1]
            line_num = int(location_parts[2]) if location_parts[2].isdigit() else 0
        else:
            module = location
            function = ""
            line_num = 0
        
        return LogEntry(
            timestamp=timestamp,
            level=level,
            module=module,
            function=function,
            line=line_num,
            message=message
        )
    except Exception:
        return None


def filter_logs(
    log_entries: List[LogEntry],
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    level: Optional[str] = None,
    task_id: Optional[int] = None,
    search: Optional[str] = None
) -> List[LogEntry]:
    """
    Filter log entries based on criteria
    
    Args:
        log_entries: List of log entries
        start_time: Start time filter (ISO format)
        end_time: End time filter (ISO format)
        level: Log level filter
        task_id: Task ID filter (searches in message)
        search: Text search in message
    
    Returns:
        Filtered list of log entries
    """
    filtered = log_entries
    
    # Filter by time range
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            filtered = [
                log for log in filtered
                if datetime.fromisoformat(log.timestamp.replace("Z", "+00:00")) >= start_dt
            ]
        except ValueError:
            pass
    
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            filtered = [
                log for log in filtered
                if datetime.fromisoformat(log.timestamp.replace("Z", "+00:00")) <= end_dt
            ]
        except ValueError:
            pass
    
    # Filter by level
    if level:
        level_upper = level.upper()
        filtered = [log for log in filtered if log.level == level_upper]
    
    # Filter by task ID
    if task_id is not None:
        task_str = f"job {task_id}" if "job" not in str(task_id) else str(task_id)
        filtered = [
            log for log in filtered
            if task_str.lower() in log.message.lower()
        ]
    
    # Filter by search text
    if search:
        search_lower = search.lower()
        filtered = [
            log for log in filtered
            if search_lower in log.message.lower()
        ]
    
    return filtered


@router.get("", response_model=LogsResponse)
async def get_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Page size"),
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    level: Optional[str] = Query(None, description="Log level (INFO, WARNING, ERROR)"),
    task_id: Optional[int] = Query(None, description="Training job ID"),
    search: Optional[str] = Query(None, description="Search text in message"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get application logs with filtering and pagination
    
    Only administrators can access logs.
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Number of logs per page (default: 100, max: 1000)
    - start_time: Filter logs after this time (ISO format)
    - end_time: Filter logs before this time (ISO format)
    - level: Filter by log level (INFO, WARNING, ERROR)
    - task_id: Filter logs related to specific training job
    - search: Search text in log messages
    
    Returns:
        LogsResponse with filtered and paginated logs
    
    Raises:
        HTTPException 403: If user is not an administrator
        HTTPException 404: If log file not found
    """
    # Check admin permission
    require_admin(current_user)
    
    # Determine which log file to read
    # For now, read today's log file
    log_dir = Path("logs")
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"app_{today}.log"
    
    if not log_file.exists():
        # Try to find the most recent log file
        log_files = sorted(log_dir.glob("app_*.log"), reverse=True)
        if not log_files:
            raise HTTPException(
                status_code=404,
                detail="No log files found"
            )
        log_file = log_files[0]
    
    # Read and parse log file
    log_entries = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                entry = parse_log_line(line)
                if entry:
                    log_entries.append(entry)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read log file: {str(e)}"
        )
    
    # Filter logs
    filtered_logs = filter_logs(
        log_entries,
        start_time=start_time,
        end_time=end_time,
        level=level,
        task_id=task_id,
        search=search
    )
    
    # Sort by timestamp (newest first)
    filtered_logs.sort(key=lambda x: x.timestamp, reverse=True)
    
    # Paginate
    total = len(filtered_logs)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_logs = filtered_logs[start_idx:end_idx]
    
    return LogsResponse(
        total=total,
        page=page,
        page_size=page_size,
        logs=paginated_logs
    )


@router.get("/files", response_model=List[str])
async def list_log_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List available log files
    
    Only administrators can access this endpoint.
    
    Returns:
        List of log file names
    
    Raises:
        HTTPException 403: If user is not an administrator
    """
    # Check admin permission
    require_admin(current_user)
    
    log_dir = Path("logs")
    if not log_dir.exists():
        return []
    
    # Get all log files
    log_files = sorted(log_dir.glob("app_*.log"), reverse=True)
    
    return [f.name for f in log_files]
