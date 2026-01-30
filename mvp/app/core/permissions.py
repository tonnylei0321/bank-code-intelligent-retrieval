"""
权限控制工具模块

提供基于角色的访问控制（RBAC）功能，包括：
1. 角色验证装饰器
2. 权限检查函数
3. 管理员权限验证

用于保护API端点，确保只有具有相应权限的用户才能访问。
"""
from functools import wraps
from typing import Callable
from fastapi import HTTPException, status

from app.models.user import UserRole


def require_role(*allowed_roles: UserRole):
    """
    要求特定角色才能访问端点的装饰器
    
    使用此装饰器可以限制API端点只允许特定角色的用户访问。
    如果用户角色不在允许列表中，将返回403 Forbidden错误。
    
    Args:
        *allowed_roles: 一个或多个允许的UserRole枚举值
        
    Returns:
        装饰器函数
        
    使用示例:
        @require_role(UserRole.ADMIN)
        async def admin_only_endpoint(current_user: User = Depends(get_current_user)):
            # 只有管理员可以访问此端点
            ...
        
        @require_role(UserRole.ADMIN, UserRole.MANAGER)
        async def privileged_endpoint(current_user: User = Depends(get_current_user)):
            # 管理员和经理都可以访问
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中提取当前用户
            current_user = kwargs.get('current_user')
            
            # 检查用户是否已认证
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="未认证：需要登录"
                )
            
            # 检查用户角色是否在允许的角色列表中
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足：需要更高级别的权限"
                )
            
            # 权限验证通过，执行原函数
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(func: Callable):
    """
    要求管理员角色才能访问端点的装饰器
    
    这是require_role(UserRole.ADMIN)的便捷包装器，
    用于快速限制端点只允许管理员访问。
    
    Args:
        func: 要装饰的函数
    
    Returns:
        装饰后的函数
    
    使用示例:
        @require_admin
        async def admin_endpoint(current_user: User = Depends(get_current_user)):
            # 只有管理员可以访问
            ...
    """
    return require_role(UserRole.ADMIN)(func)


def check_permission(user_role: str, required_role: UserRole) -> bool:
    """
    检查用户角色是否具有所需权限
    
    验证用户的角色是否满足操作所需的权限要求。
    管理员角色具有所有权限。
    
    Args:
        user_role: 用户当前角色（字符串格式）
        required_role: 操作所需的角色
        
    Returns:
        如果用户具有权限返回True，否则返回False
    
    注意:
        - 管理员角色自动具有所有权限
        - 如果user_role不是有效的UserRole值，返回False
    """
    try:
        # 将字符串角色转换为枚举类型
        user_role_enum = UserRole(user_role)
        # 检查角色是否匹配或用户是管理员
        return user_role_enum == required_role or user_role_enum == UserRole.ADMIN
    except ValueError:
        # 无效的角色值
        return False
