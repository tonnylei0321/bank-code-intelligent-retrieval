"""
Redis数据管理API

提供Redis缓存数据的管理接口：
1. 数据加载和同步
2. 数据查询和检索
3. 统计信息获取
4. 缓存管理操作
5. 文件上传和解析
"""

import os
import tempfile
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.deps import get_db, get_current_user
from app.core.permissions import require_admin_user, check_permission, require_permission
from app.services.redis_service import RedisService
from app.models.user import User
from app.models.bank_code import BankCode
from loguru import logger

router = APIRouter()


def get_redis_service(db: Session = Depends(get_db)) -> RedisService:
    """获取Redis服务实例"""
    redis_service = RedisService(db)
    return redis_service


@router.post("/upload-file")
async def upload_bank_data_file(
    file: UploadFile = File(...),
    force_reload: bool = Query(False, description="是否强制重新加载"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传银行数据文件并解析装载到Redis
    
    Args:
        file: 上传的文件
        force_reload: 是否强制重新加载
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        上传和解析结果
    """
    try:
        # 检查权限
        require_permission(current_user, "admin")
        
        # 检查文件类型
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 支持的文件扩展名
        allowed_extensions = ['.unl', '.txt', '.csv']
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型。支持的格式: {', '.join(allowed_extensions)}"
            )
        
        # 检查文件大小（限制为50MB）
        max_file_size = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        if len(file_content) > max_file_size:
            raise HTTPException(status_code=400, detail="文件大小不能超过50MB")
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=file_extension) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # 解析文件
            logger.info(f"开始解析上传的文件: {file.filename}")
            parsed_data = await parse_bank_data_file(temp_file_path, file.filename)
            
            if not parsed_data["success"]:
                raise HTTPException(status_code=400, detail=parsed_data["error"])
            
            # 保存到数据库
            logger.info(f"开始保存 {len(parsed_data['banks'])} 条银行记录到数据库")
            saved_count = await save_banks_to_database(db, parsed_data["banks"], current_user.id)
            
            # 加载到Redis
            redis_service = RedisService(db)
            if not await redis_service.initialize():
                raise HTTPException(status_code=500, detail="Redis连接失败")
            
            # 获取刚保存的银行记录
            new_bank_records = db.query(BankCode).filter(
                BankCode.bank_code.in_([bank["bank_code"] for bank in parsed_data["banks"]])
            ).all()
            
            # 更新Redis
            redis_success = await redis_service.update_bank_data(new_bank_records)
            if not redis_success:
                logger.warning("Redis更新失败，但数据库保存成功")
            
            await redis_service.close()
            
            logger.info(f"文件上传处理完成: {file.filename}")
            
            return {
                "success": True,
                "message": "文件上传和处理完成",
                "data": {
                    "filename": file.filename,
                    "file_size": len(file_content),
                    "parsed_count": len(parsed_data["banks"]),
                    "saved_count": saved_count,
                    "redis_updated": redis_success,
                    "processing_time": parsed_data.get("processing_time", 0),
                    "sample_data": parsed_data["banks"][:3] if parsed_data["banks"] else []
                }
            }
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")


async def parse_bank_data_file(file_path: str, filename: str) -> Dict[str, Any]:
    """
    解析银行数据文件
    
    Args:
        file_path: 文件路径
        filename: 文件名
    
    Returns:
        解析结果
    """
    try:
        start_time = datetime.now()
        banks = []
        
        logger.info(f"开始解析文件: {filename}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 如果UTF-8解码失败，尝试其他编码
        if not lines:
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    lines = f.readlines()
                logger.info("使用GBK编码解析文件")
            except:
                with open(file_path, 'r', encoding='latin-1') as f:
                    lines = f.readlines()
                logger.info("使用Latin-1编码解析文件")
        
        logger.info(f"文件包含 {len(lines)} 行数据")
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                # 根据文件扩展名选择解析方式
                if filename.endswith('.unl') or '|' in line:
                    # UNL格式：使用管道符分隔
                    parts = line.split('|')
                elif filename.endswith('.csv') or ',' in line:
                    # CSV格式：使用逗号分隔
                    parts = line.split(',')
                else:
                    # 默认使用制表符分隔
                    parts = line.split('\t')
                
                if len(parts) < 3:
                    logger.warning(f"第{line_num}行数据格式不正确，跳过: {line[:50]}...")
                    continue
                
                # 对于UNL文件，检查倒数第二个字段是否为0
                if filename.endswith('.unl') or '|' in line:
                    if len(parts) >= 3:
                        # 实际上是倒数第三个字段（索引为-3）
                        target_field = parts[-3].strip()
                        if target_field != '0':
                            logger.debug(f"第{line_num}行倒数第三个字段不为0({target_field})，跳过")
                            continue
                    else:
                        logger.warning(f"第{line_num}行字段数量不足，跳过: {line[:50]}...")
                        continue
                
                # 提取数据：第一列联行编号，第二列银行名称，第三列清算行行号
                bank_code = parts[0].strip()
                bank_name = parts[1].strip()
                clearing_code = parts[2].strip() if len(parts) > 2 else ""
                
                # 验证数据
                if not bank_code or not bank_name:
                    logger.warning(f"第{line_num}行数据不完整，跳过: {line[:50]}...")
                    continue
                
                # 验证联行号格式（通常是12位数字）
                if not bank_code.isdigit() or len(bank_code) != 12:
                    logger.warning(f"第{line_num}行联行号格式不正确，跳过: {bank_code}")
                    continue
                
                banks.append({
                    "bank_code": bank_code,
                    "bank_name": bank_name,
                    "clearing_code": clearing_code,
                    "line_number": line_num
                })
                
            except Exception as e:
                logger.warning(f"解析第{line_num}行时出错: {e}, 行内容: {line[:50]}...")
                continue
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"文件解析完成，成功解析 {len(banks)} 条银行记录，耗时 {processing_time:.2f}秒")
        
        return {
            "success": True,
            "banks": banks,
            "total_lines": len(lines),
            "parsed_count": len(banks),
            "processing_time": processing_time
        }
        
    except Exception as e:
        logger.error(f"文件解析失败: {e}")
        return {
            "success": False,
            "error": f"文件解析失败: {str(e)}",
            "banks": []
        }


async def save_banks_to_database(db: Session, banks: List[Dict[str, Any]], user_id: int) -> int:
    """
    保存银行数据到数据库
    
    Args:
        db: 数据库会话
        banks: 银行数据列表
        user_id: 用户ID
    
    Returns:
        保存的记录数量
    """
    try:
        saved_count = 0
        updated_count = 0
        
        for bank_data in banks:
            # 检查是否已存在相同的银行代码和数据集组合
            existing_bank = db.query(BankCode).filter(
                BankCode.bank_code == bank_data["bank_code"],
                BankCode.dataset_id == 1  # 默认数据集ID
            ).first()
            
            if existing_bank:
                # 更新现有记录
                existing_bank.bank_name = bank_data["bank_name"]
                existing_bank.clearing_code = bank_data["clearing_code"]
                existing_bank.updated_at = datetime.now().isoformat()
                existing_bank.is_valid = 1
                updated_count += 1
                logger.debug(f"更新银行记录: {bank_data['bank_code']}")
            else:
                # 创建新记录
                new_bank = BankCode(
                    bank_code=bank_data["bank_code"],
                    bank_name=bank_data["bank_name"],
                    clearing_code=bank_data["clearing_code"],
                    dataset_id=1,  # 默认数据集ID
                    is_valid=1,
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat()
                )
                db.add(new_bank)
                saved_count += 1
                logger.debug(f"创建银行记录: {bank_data['bank_code']}")
        
        # 提交事务
        db.commit()
        total_processed = saved_count + updated_count
        logger.info(f"成功处理 {total_processed} 条银行记录到数据库 (新增: {saved_count}, 更新: {updated_count})")
        
        return total_processed
        
    except Exception as e:
        db.rollback()
        logger.error(f"保存银行数据到数据库失败: {e}")
        raise e


@router.post("/parse-preview")
async def preview_bank_data_file(
    file: UploadFile = File(...),
    lines: int = Query(10, ge=1, le=100, description="预览行数"),
    current_user: User = Depends(get_current_user)
):
    """
    预览银行数据文件内容（不保存）
    
    Args:
        file: 上传的文件
        lines: 预览行数
        current_user: 当前用户
    
    Returns:
        文件预览结果
    """
    try:
        # 检查权限
        require_permission(current_user, "user")
        
        # 检查文件
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        # 读取文件内容
        file_content = await file.read()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.tmp') as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # 解析文件（仅预览）
            parsed_data = await parse_bank_data_file(temp_file_path, file.filename)
            
            if not parsed_data["success"]:
                raise HTTPException(status_code=400, detail=parsed_data["error"])
            
            # 返回预览数据
            preview_banks = parsed_data["banks"][:lines]
            
            return {
                "success": True,
                "data": {
                    "filename": file.filename,
                    "file_size": len(file_content),
                    "total_lines": parsed_data["total_lines"],
                    "parsed_count": parsed_data["parsed_count"],
                    "preview_count": len(preview_banks),
                    "preview_data": preview_banks,
                    "processing_time": parsed_data["processing_time"]
                }
            }
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件预览失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件预览失败: {str(e)}")


@router.post("/load-data")
async def load_bank_data_to_redis(
    force_reload: bool = Query(False, description="是否强制重新加载"),
    redis_service: RedisService = Depends(get_redis_service),
    current_user: User = Depends(get_current_user)
):
    """
    将银行数据加载到Redis
    
    Args:
        force_reload: 是否强制重新加载
        redis_service: Redis服务实例
        current_user: 当前用户
    
    Returns:
        加载结果
    """
    try:
        # 检查权限
        require_permission(current_user, "admin")
        
        # 初始化Redis连接
        if not await redis_service.initialize():
            raise HTTPException(status_code=500, detail="Failed to initialize Redis connection")
        
        # 加载数据
        result = await redis_service.load_bank_data_to_redis(force_reload=force_reload)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["error"])
        
        logger.info(f"User {current_user.username} loaded bank data to Redis: {result}")
        
        return {
            "success": True,
            "message": "银行数据加载完成",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load bank data to Redis: {e}")
        raise HTTPException(status_code=500, detail=f"加载数据失败: {str(e)}")
    finally:
        await redis_service.close()


@router.get("/stats")
async def get_redis_stats(
    redis_service: RedisService = Depends(get_redis_service),
    current_user: User = Depends(get_current_user)
):
    """
    获取Redis统计信息
    
    Args:
        redis_service: Redis服务实例
        current_user: 当前用户
    
    Returns:
        Redis统计信息
    """
    try:
        # 检查权限
        require_permission(current_user, "user")
        
        # 初始化Redis连接
        if not await redis_service.initialize():
            raise HTTPException(status_code=500, detail="Failed to initialize Redis connection")
        
        # 获取统计信息
        stats = await redis_service.get_redis_stats()
        
        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])
        
        return {
            "success": True,
            "data": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Redis stats: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
    finally:
        await redis_service.close()


@router.get("/search")
async def search_banks_in_redis(
    query: str = Query(..., description="搜索查询"),
    search_type: str = Query("auto", description="搜索类型: auto, name, code, keyword"),
    limit: int = Query(10, ge=1, le=50, description="返回结果数量限制"),
    redis_service: RedisService = Depends(get_redis_service),
    current_user: User = Depends(get_current_user)
):
    """
    在Redis中搜索银行信息
    
    Args:
        query: 搜索查询
        search_type: 搜索类型
        limit: 返回结果数量限制
        redis_service: Redis服务实例
        current_user: 当前用户
    
    Returns:
        搜索结果
    """
    try:
        # 检查权限
        require_permission(current_user, "user")
        
        # 初始化Redis连接
        if not await redis_service.initialize():
            raise HTTPException(status_code=500, detail="Failed to initialize Redis connection")
        
        # 执行搜索
        results = await redis_service.search_banks(
            query=query,
            search_type=search_type,
            limit=limit
        )
        
        return {
            "success": True,
            "data": {
                "query": query,
                "search_type": search_type,
                "results": results,
                "count": len(results)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search banks in Redis: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")
    finally:
        await redis_service.close()


@router.get("/bank/{bank_id}")
async def get_bank_by_id(
    bank_id: int,
    redis_service: RedisService = Depends(get_redis_service),
    current_user: User = Depends(get_current_user)
):
    """
    根据ID获取银行信息
    
    Args:
        bank_id: 银行ID
        redis_service: Redis服务实例
        current_user: 当前用户
    
    Returns:
        银行信息
    """
    try:
        # 检查权限
        require_permission(current_user, "user")
        
        # 初始化Redis连接
        if not await redis_service.initialize():
            raise HTTPException(status_code=500, detail="Failed to initialize Redis connection")
        
        # 获取银行信息
        bank_data = await redis_service.get_bank_by_id(bank_id)
        
        if not bank_data:
            raise HTTPException(status_code=404, detail="银行信息未找到")
        
        return {
            "success": True,
            "data": bank_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get bank by ID: {e}")
        raise HTTPException(status_code=500, detail=f"获取银行信息失败: {str(e)}")
    finally:
        await redis_service.close()


@router.get("/bank/code/{bank_code}")
async def get_bank_by_code(
    bank_code: str,
    redis_service: RedisService = Depends(get_redis_service),
    current_user: User = Depends(get_current_user)
):
    """
    根据联行号获取银行信息
    
    Args:
        bank_code: 联行号
        redis_service: Redis服务实例
        current_user: 当前用户
    
    Returns:
        银行信息
    """
    try:
        # 检查权限
        require_permission(current_user, "user")
        
        # 初始化Redis连接
        if not await redis_service.initialize():
            raise HTTPException(status_code=500, detail="Failed to initialize Redis connection")
        
        # 获取银行信息
        bank_data = await redis_service.get_bank_by_code(bank_code)
        
        if not bank_data:
            raise HTTPException(status_code=404, detail="银行信息未找到")
        
        return {
            "success": True,
            "data": bank_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get bank by code: {e}")
        raise HTTPException(status_code=500, detail=f"获取银行信息失败: {str(e)}")
    finally:
        await redis_service.close()


@router.delete("/clear-data")
async def clear_redis_data(
    redis_service: RedisService = Depends(get_redis_service),
    current_user: User = Depends(get_current_user)
):
    """
    清空Redis中的银行数据
    
    Args:
        redis_service: Redis服务实例
        current_user: 当前用户
    
    Returns:
        清空结果
    """
    try:
        # 检查权限
        require_permission(current_user, "admin")
        
        # 初始化Redis连接
        if not await redis_service.initialize():
            raise HTTPException(status_code=500, detail="Failed to initialize Redis connection")
        
        # 清空数据
        success = await redis_service.clear_redis_data()
        
        if not success:
            raise HTTPException(status_code=500, detail="清空数据失败")
        
        logger.info(f"User {current_user.username} cleared Redis data")
        
        return {
            "success": True,
            "message": "Redis数据已清空"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear Redis data: {e}")
        raise HTTPException(status_code=500, detail=f"清空数据失败: {str(e)}")
    finally:
        await redis_service.close()


@router.post("/sync-data")
async def sync_redis_data(
    redis_service: RedisService = Depends(get_redis_service),
    current_user: User = Depends(get_current_user)
):
    """
    同步Redis数据（增量更新）
    
    Args:
        redis_service: Redis服务实例
        current_user: 当前用户
    
    Returns:
        同步结果
    """
    try:
        # 检查权限
        require_permission(current_user, "admin")
        
        # 初始化Redis连接
        if not await redis_service.initialize():
            raise HTTPException(status_code=500, detail="Failed to initialize Redis connection")
        
        # 获取需要更新的银行记录
        from app.models.bank_code import BankCode
        from datetime import datetime, timedelta
        
        # 获取最近更新的记录（简化版本）
        recent_records = redis_service.db.query(BankCode)\
            .filter(BankCode.is_valid == True)\
            .filter(BankCode.updated_at >= datetime.now() - timedelta(days=1))\
            .all()
        
        if not recent_records:
            return {
                "success": True,
                "message": "没有需要同步的数据",
                "updated_count": 0
            }
        
        # 更新Redis数据
        success = await redis_service.update_bank_data(recent_records)
        
        if not success:
            raise HTTPException(status_code=500, detail="同步数据失败")
        
        logger.info(f"User {current_user.username} synced {len(recent_records)} records to Redis")
        
        return {
            "success": True,
            "message": f"成功同步 {len(recent_records)} 条记录",
            "updated_count": len(recent_records)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync Redis data: {e}")
        raise HTTPException(status_code=500, detail=f"同步数据失败: {str(e)}")
    finally:
        await redis_service.close()


@router.get("/health")
async def check_redis_health(
    redis_service: RedisService = Depends(get_redis_service),
    current_user: User = Depends(get_current_user)
):
    """
    检查Redis健康状态
    
    Args:
        redis_service: Redis服务实例
        current_user: 当前用户
    
    Returns:
        健康状态信息
    """
    try:
        # 检查权限
        require_permission(current_user, "user")
        
        # 尝试初始化Redis连接
        redis_available = await redis_service.initialize()
        
        if not redis_available:
            return {
                "success": False,
                "status": "unhealthy",
                "message": "Redis连接失败"
            }
        
        # 测试Redis操作
        try:
            await redis_service.redis_client.ping()
            redis_status = "healthy"
            redis_message = "Redis连接正常"
        except Exception as e:
            redis_status = "unhealthy"
            redis_message = f"Redis操作失败: {str(e)}"
        
        # 获取基本统计信息
        stats = await redis_service.get_redis_stats()
        
        return {
            "success": True,
            "status": redis_status,
            "message": redis_message,
            "stats": stats if "error" not in stats else None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to check Redis health: {e}")
        return {
            "success": False,
            "status": "error",
            "message": f"健康检查失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
    finally:
        await redis_service.close()