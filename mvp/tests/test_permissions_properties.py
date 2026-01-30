"""
Property-based tests for permission control
权限控制的属性测试

Feature: bank-code-retrieval, Property 20: 权限控制一致性
"""
import pytest
from hypothesis import given, strategies as st, settings
from fastapi import HTTPException, status
from unittest.mock import Mock

from app.core.permissions import require_role, require_admin, check_permission
from app.models.user import User, UserRole


@pytest.mark.property
class TestPermissionControlProperties:
    """Property-based tests for permission control"""
    
    @given(
        user_id=st.integers(min_value=1, max_value=1000000),
        username=st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=100)
    def test_admin_user_can_access_admin_endpoints(self, user_id, username):
        """
        Feature: bank-code-retrieval, Property 20: 权限控制一致性
        
        For any admin user, they should be able to access admin-only endpoints.
        
        Property: Admin users have admin access
        """
        # Create mock admin user
        admin_user = Mock(spec=User)
        admin_user.id = user_id
        admin_user.username = username
        admin_user.role = UserRole.ADMIN
        admin_user.is_admin = True
        
        # Test with require_admin decorator
        @require_admin
        async def admin_endpoint(current_user: User):
            return {"message": "success"}
        
        # Should not raise exception
        result = None
        try:
            import asyncio
            result = asyncio.run(admin_endpoint(current_user=admin_user))
        except HTTPException:
            pytest.fail("Admin user should be able to access admin endpoint")
        
        assert result == {"message": "success"}
    
    @given(
        user_id=st.integers(min_value=1, max_value=1000000),
        username=st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=100)
    def test_regular_user_cannot_access_admin_endpoints(self, user_id, username):
        """
        Feature: bank-code-retrieval, Property 20: 权限控制一致性
        
        For any regular user, they should NOT be able to access admin-only endpoints
        and should receive 403 status code.
        
        Property: Regular users are denied admin access
        """
        # Create mock regular user
        regular_user = Mock(spec=User)
        regular_user.id = user_id
        regular_user.username = username
        regular_user.role = UserRole.USER
        regular_user.is_admin = False
        
        # Test with require_admin decorator
        @require_admin
        async def admin_endpoint(current_user: User):
            return {"message": "success"}
        
        # Should raise 403 exception
        with pytest.raises(HTTPException) as exc_info:
            import asyncio
            asyncio.run(admin_endpoint(current_user=regular_user))
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Permission denied" in exc_info.value.detail or "insufficient privileges" in exc_info.value.detail
    
    @given(
        user_id=st.integers(min_value=1, max_value=1000000),
        username=st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        role=st.sampled_from([UserRole.ADMIN, UserRole.USER])
    )
    @settings(max_examples=100)
    def test_users_can_access_their_own_role_endpoints(self, user_id, username, role):
        """
        Feature: bank-code-retrieval, Property 20: 权限控制一致性
        
        For any user with a specific role, they should be able to access endpoints
        that require their role.
        
        Property: Users can access endpoints matching their role
        """
        # Create mock user
        user = Mock(spec=User)
        user.id = user_id
        user.username = username
        user.role = role
        user.is_admin = (role == UserRole.ADMIN)
        
        # Test with require_role decorator
        @require_role(role)
        async def role_endpoint(current_user: User):
            return {"message": "success"}
        
        # Should not raise exception
        result = None
        try:
            import asyncio
            result = asyncio.run(role_endpoint(current_user=user))
        except HTTPException:
            pytest.fail(f"User with role {role} should be able to access endpoint requiring {role}")
        
        assert result == {"message": "success"}
    
    @given(
        user_id=st.integers(min_value=1, max_value=1000000),
        username=st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=100)
    def test_unauthenticated_request_returns_401(self, user_id, username):
        """
        Feature: bank-code-retrieval, Property 20: 权限控制一致性
        
        For any endpoint requiring authentication, requests without current_user
        should return 401 status code.
        
        Property: Unauthenticated requests are rejected with 401
        """
        # Test with require_admin decorator without current_user
        @require_admin
        async def admin_endpoint(current_user: User = None):
            return {"message": "success"}
        
        # Should raise 401 exception
        with pytest.raises(HTTPException) as exc_info:
            import asyncio
            asyncio.run(admin_endpoint(current_user=None))
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    @given(
        role_str=st.sampled_from(['admin', 'user'])
    )
    @settings(max_examples=50)
    def test_check_permission_admin_role(self, role_str):
        """
        Feature: bank-code-retrieval, Property 20: 权限控制一致性
        
        Property: check_permission correctly validates admin role
        """
        # Admin should have permission for admin role
        if role_str == 'admin':
            assert check_permission(role_str, UserRole.ADMIN) is True
        else:
            assert check_permission(role_str, UserRole.ADMIN) is False
    
    @given(
        role_str=st.sampled_from(['admin', 'user'])
    )
    @settings(max_examples=50)
    def test_check_permission_user_role(self, role_str):
        """
        Feature: bank-code-retrieval, Property 20: 权限控制一致性
        
        Property: check_permission correctly validates user role
        """
        # Both admin and user should have permission for user role
        # (admin has all permissions)
        assert check_permission(role_str, UserRole.USER) is True
    
    def test_check_permission_invalid_role(self):
        """
        Feature: bank-code-retrieval, Property 20: 权限控制一致性
        
        Property: check_permission rejects invalid roles
        """
        # Invalid role should return False
        assert check_permission('invalid_role', UserRole.ADMIN) is False
        assert check_permission('invalid_role', UserRole.USER) is False
    
    @given(
        user_id=st.integers(min_value=1, max_value=1000000),
        username=st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=100)
    def test_admin_can_access_user_endpoints(self, user_id, username):
        """
        Feature: bank-code-retrieval, Property 20: 权限控制一致性
        
        For any admin user, they should be able to access both admin and user endpoints.
        
        Property: Admin users have access to all endpoints
        """
        # Create mock admin user
        admin_user = Mock(spec=User)
        admin_user.id = user_id
        admin_user.username = username
        admin_user.role = UserRole.ADMIN
        admin_user.is_admin = True
        
        # Test with require_role(USER) decorator
        @require_role(UserRole.USER, UserRole.ADMIN)
        async def user_endpoint(current_user: User):
            return {"message": "success"}
        
        # Should not raise exception
        result = None
        try:
            import asyncio
            result = asyncio.run(user_endpoint(current_user=admin_user))
        except HTTPException:
            pytest.fail("Admin user should be able to access user endpoint")
        
        assert result == {"message": "success"}
    
    @given(
        user_id=st.integers(min_value=1, max_value=1000000),
        username=st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @settings(max_examples=100)
    def test_permission_denied_message_is_clear(self, user_id, username):
        """
        Feature: bank-code-retrieval, Property 20: 权限控制一致性
        
        For any permission denied error, the error message should clearly indicate
        insufficient privileges.
        
        Property: Permission errors have clear messages
        """
        # Create mock regular user
        regular_user = Mock(spec=User)
        regular_user.id = user_id
        regular_user.username = username
        regular_user.role = UserRole.USER
        regular_user.is_admin = False
        
        # Test with require_admin decorator
        @require_admin
        async def admin_endpoint(current_user: User):
            return {"message": "success"}
        
        # Should raise 403 exception with clear message
        with pytest.raises(HTTPException) as exc_info:
            import asyncio
            asyncio.run(admin_endpoint(current_user=regular_user))
        
        # Check error message contains permission-related keywords
        error_detail = exc_info.value.detail.lower()
        assert any(keyword in error_detail for keyword in ['permission', 'privileges', 'forbidden', 'denied'])
