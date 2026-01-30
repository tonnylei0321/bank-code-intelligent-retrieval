"""
Property-based tests for authentication
认证功能的属性测试

Feature: bank-code-retrieval, Property 19: JWT Token有效性
"""
import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
from jose import jwt

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password
)
from app.core.config import settings as app_settings


@pytest.mark.property
class TestJWTTokenProperties:
    """Property-based tests for JWT tokens"""
    
    @given(
        user_id=st.integers(min_value=1, max_value=1000000),
        username=st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        role=st.sampled_from(['admin', 'user'])
    )
    @settings(max_examples=100)
    def test_token_contains_user_data(self, user_id, username, role):
        """
        Feature: bank-code-retrieval, Property 19: JWT Token有效性
        
        For any successful login request, the returned JWT Token should be valid 
        for 24 hours and contain user_id and role information.
        
        Property: Token contains correct user data
        """
        # Create token
        token = create_access_token(
            data={"user_id": user_id, "username": username, "role": role}
        )
        
        # Decode token
        payload = decode_access_token(token)
        
        # Verify token contains correct data
        assert payload is not None
        assert payload["user_id"] == user_id
        assert payload["username"] == username
        assert payload["role"] == role
    
    @given(
        user_id=st.integers(min_value=1, max_value=1000000),
        username=st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        role=st.sampled_from(['admin', 'user'])
    )
    @settings(max_examples=100)
    def test_token_expires_in_24_hours(self, user_id, username, role):
        """
        Feature: bank-code-retrieval, Property 19: JWT Token有效性
        
        Property: Token expires in 24 hours
        """
        # Create token and capture creation time
        now = datetime.utcnow()
        token = create_access_token(
            data={"user_id": user_id, "username": username, "role": role}
        )
        
        # Decode token
        payload = decode_access_token(token)
        
        # Verify expiration time
        assert payload is not None
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
        
        # Token should expire approximately 24 hours from now (allow 1 minute tolerance)
        expected_expiry = now + timedelta(hours=app_settings.ACCESS_TOKEN_EXPIRE_HOURS)
        time_diff = abs((exp_datetime - expected_expiry).total_seconds())
        assert time_diff < 60, f"Token expiry time difference: {time_diff} seconds"
    
    @given(
        user_id=st.integers(min_value=1, max_value=1000000),
        username=st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        role=st.sampled_from(['admin', 'user'])
    )
    @settings(max_examples=100)
    def test_token_can_be_decoded(self, user_id, username, role):
        """
        Feature: bank-code-retrieval, Property 19: JWT Token有效性
        
        Property: Valid tokens can always be decoded
        """
        # Create token
        token = create_access_token(
            data={"user_id": user_id, "username": username, "role": role}
        )
        
        # Token should be decodable
        payload = decode_access_token(token)
        assert payload is not None
    
    def test_expired_token_cannot_be_decoded(self):
        """
        Feature: bank-code-retrieval, Property 19: JWT Token有效性
        
        Property: Expired tokens cannot be decoded
        """
        # Create token that expires immediately
        token = create_access_token(
            data={"user_id": 1, "username": "test", "role": "user"},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        
        # Expired token should not be decodable
        payload = decode_access_token(token)
        assert payload is None
    
    def test_invalid_token_cannot_be_decoded(self):
        """
        Feature: bank-code-retrieval, Property 19: JWT Token有效性
        
        Property: Invalid tokens cannot be decoded
        """
        # Invalid token
        invalid_token = "invalid.token.string"
        
        # Should return None
        payload = decode_access_token(invalid_token)
        assert payload is None
    
    def test_tampered_token_cannot_be_decoded(self):
        """
        Feature: bank-code-retrieval, Property 19: JWT Token有效性
        
        Property: Tampered tokens cannot be decoded
        """
        # Create valid token
        token = create_access_token(
            data={"user_id": 1, "username": "test", "role": "user"}
        )
        
        # Tamper with token signature (change characters in the signature part)
        parts = token.split('.')
        if len(parts) == 3:
            # Modify the signature part (last part)
            signature = parts[2]
            if len(signature) > 5:
                # Change multiple characters in the middle of signature
                tampered_sig = signature[:5] + ('X' if signature[5] != 'X' else 'Y') + signature[6:]
                tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"
            else:
                tampered_token = token[:-1] + ('a' if token[-1] != 'a' else 'b')
        else:
            tampered_token = token[:-1] + ('a' if token[-1] != 'a' else 'b')
        
        # Tampered token should not be decodable
        payload = decode_access_token(tampered_token)
        assert payload is None


@pytest.mark.property
class TestPasswordHashingProperties:
    """Property-based tests for password hashing"""
    
    @given(password=st.text(min_size=6, max_size=100).filter(lambda x: '\x00' not in x))
    @settings(max_examples=100, deadline=2000)  # Increased deadline for bcrypt
    def test_password_hash_is_different_from_original(self, password):
        """
        Property: Hashed password is different from original
        """
        hashed = get_password_hash(password)
        assert hashed != password
    
    @given(password=st.text(min_size=6, max_size=100).filter(lambda x: '\x00' not in x))
    @settings(max_examples=100, deadline=2000)  # Increased deadline for bcrypt
    def test_password_verification_works(self, password):
        """
        Property: Password verification works correctly
        """
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
    
    @given(
        password=st.text(min_size=6, max_size=100).filter(lambda x: '\x00' not in x),
        wrong_password=st.text(min_size=6, max_size=100).filter(lambda x: '\x00' not in x)
    )
    @settings(max_examples=100, deadline=1000)
    def test_wrong_password_fails_verification(self, password, wrong_password):
        """
        Property: Wrong password fails verification
        """
        # Skip if passwords are the same
        if password == wrong_password:
            return
        
        hashed = get_password_hash(password)
        assert verify_password(wrong_password, hashed) is False
    
    @given(password=st.text(min_size=6, max_size=100).filter(lambda x: '\x00' not in x))
    @settings(max_examples=100, deadline=2000)
    def test_same_password_produces_different_hashes(self, password):
        """
        Property: Same password produces different hashes (due to salt)
        """
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different (bcrypt uses random salt)
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
