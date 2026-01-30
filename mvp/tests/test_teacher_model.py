"""
Tests for Teacher Model API client
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx

from app.services.teacher_model import (
    TeacherModelAPI,
    TeacherModelAPIError,
    APIRateLimitError,
    APITimeoutError,
    APIAuthenticationError
)
from app.models.bank_code import BankCode


@pytest.fixture
def mock_bank_record():
    """Create a mock bank code record"""
    record = Mock(spec=BankCode)
    record.id = 1
    record.bank_name = "中国工商银行北京分行"
    record.bank_code = "102100000026"
    record.clearing_code = "102100000000"
    return record


@pytest.fixture
def teacher_api():
    """Create a TeacherModelAPI instance with test configuration"""
    return TeacherModelAPI(
        api_key="test_api_key",
        api_url="https://test.api.com/generate",
        max_retries=3,
        timeout=10,
        model="qwen-turbo"
    )


class TestTeacherModelAPI:
    """Test suite for TeacherModelAPI"""
    
    def test_initialization(self):
        """Test API client initialization"""
        api = TeacherModelAPI(
            api_key="test_key",
            api_url="https://test.com",
            max_retries=5,
            timeout=20,
            model="qwen-plus"
        )
        
        assert api.api_key == "test_key"
        assert api.api_url == "https://test.com"
        assert api.max_retries == 5
        assert api.timeout == 20
        assert api.model == "qwen-plus"
    
    def test_initialization_with_defaults(self):
        """Test API client initialization with default settings"""
        with patch('app.services.teacher_model.settings') as mock_settings:
            mock_settings.QWEN_API_KEY = "default_key"
            mock_settings.QWEN_API_URL = "https://default.com"
            
            api = TeacherModelAPI()
            
            assert api.api_key == "default_key"
            assert api.api_url == "https://default.com"
            assert api.max_retries == 3
            assert api.timeout == 30
    
    def test_build_prompt_exact(self, teacher_api, mock_bank_record):
        """Test prompt building for exact question type"""
        prompt = teacher_api._build_prompt(mock_bank_record, "exact")
        
        assert "中国工商银行北京分行" in prompt
        assert "102100000026" in prompt
        assert "精确查询" in prompt
        assert "问题|答案" in prompt
    
    def test_build_prompt_fuzzy(self, teacher_api, mock_bank_record):
        """Test prompt building for fuzzy question type"""
        prompt = teacher_api._build_prompt(mock_bank_record, "fuzzy")
        
        assert "中国工商银行北京分行" in prompt
        assert "102100000026" in prompt
        assert "模糊查询" in prompt
        assert "简称" in prompt
    
    def test_build_prompt_reverse(self, teacher_api, mock_bank_record):
        """Test prompt building for reverse question type"""
        prompt = teacher_api._build_prompt(mock_bank_record, "reverse")
        
        assert "中国工商银行北京分行" in prompt
        assert "102100000026" in prompt
        assert "反向查询" in prompt
    
    def test_build_prompt_natural(self, teacher_api, mock_bank_record):
        """Test prompt building for natural question type"""
        prompt = teacher_api._build_prompt(mock_bank_record, "natural")
        
        assert "中国工商银行北京分行" in prompt
        assert "102100000026" in prompt
        assert "自然语言" in prompt
    
    def test_build_prompt_invalid_type(self, teacher_api, mock_bank_record):
        """Test prompt building with invalid question type"""
        with pytest.raises(ValueError, match="Unknown question type"):
            teacher_api._build_prompt(mock_bank_record, "invalid_type")
    
    def test_parse_response_valid(self, teacher_api):
        """Test parsing valid API response"""
        response = "中国工商银行北京分行的联行号是什么？|102100000026"
        question, answer = teacher_api._parse_response(response)
        
        assert question == "中国工商银行北京分行的联行号是什么？"
        assert answer == "102100000026"
    
    def test_parse_response_with_whitespace(self, teacher_api):
        """Test parsing response with extra whitespace"""
        response = "  工行北京的联行号  |  中国工商银行北京分行的联行号是102100000026  "
        question, answer = teacher_api._parse_response(response)
        
        assert question == "工行北京的联行号"
        assert answer == "中国工商银行北京分行的联行号是102100000026"
    
    def test_parse_response_missing_separator(self, teacher_api):
        """Test parsing response without separator"""
        response = "Invalid response without separator"
        
        with pytest.raises(ValueError, match="missing separator"):
            teacher_api._parse_response(response)
    
    def test_parse_response_empty_parts(self, teacher_api):
        """Test parsing response with empty parts"""
        response = "|"
        
        with pytest.raises(ValueError, match="Empty question or answer"):
            teacher_api._parse_response(response)
    
    def test_parse_response_multiple_separators(self, teacher_api):
        """Test parsing response with multiple separators (should split on first)"""
        response = "Question with pipe|Answer with | in it"
        question, answer = teacher_api._parse_response(response)
        
        assert question == "Question with pipe"
        assert answer == "Answer with | in it"
    
    @patch('app.services.teacher_model.httpx.Client')
    def test_call_api_success(self, mock_client_class, teacher_api):
        """Test successful API call"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "output": {
                "choices": [
                    {
                        "message": {
                            "content": "Question|Answer"
                        }
                    }
                ]
            }
        }
        
        # Mock client
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        result = teacher_api._call_api("test prompt")
        
        assert result == "Question|Answer"
    
    @patch('app.services.teacher_model.httpx.Client')
    def test_call_api_authentication_error(self, mock_client_class, teacher_api):
        """Test API call with authentication error"""
        mock_response = Mock()
        mock_response.status_code = 401
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        with pytest.raises(APIAuthenticationError, match="authentication failed"):
            teacher_api._call_api("test prompt")
    
    @patch('app.services.teacher_model.httpx.Client')
    def test_call_api_rate_limit_error(self, mock_client_class, teacher_api):
        """Test API call with rate limit error"""
        mock_response = Mock()
        mock_response.status_code = 429
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        with pytest.raises(APIRateLimitError, match="rate limit exceeded"):
            teacher_api._call_api("test prompt")
    
    @patch('app.services.teacher_model.httpx.Client')
    def test_call_api_server_error(self, mock_client_class, teacher_api):
        """Test API call with server error"""
        mock_response = Mock()
        mock_response.status_code = 500
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        with pytest.raises(TeacherModelAPIError, match="server error"):
            teacher_api._call_api("test prompt")
    
    @patch('app.services.teacher_model.httpx.Client')
    def test_call_api_timeout(self, mock_client_class, teacher_api):
        """Test API call timeout"""
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client_class.return_value = mock_client
        
        with pytest.raises(APITimeoutError, match="timed out"):
            teacher_api._call_api("test prompt")
    
    @patch('app.services.teacher_model.httpx.Client')
    def test_call_api_invalid_response_format(self, mock_client_class, teacher_api):
        """Test API call with invalid response format"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"invalid": "format"}
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        with pytest.raises(TeacherModelAPIError, match="Invalid API response format"):
            teacher_api._call_api("test prompt")
    
    @patch.object(TeacherModelAPI, '_call_api')
    @patch.object(TeacherModelAPI, '_parse_response')
    def test_generate_qa_pair_success(self, mock_parse, mock_call, teacher_api, mock_bank_record):
        """Test successful QA pair generation"""
        mock_call.return_value = "Question|Answer"
        mock_parse.return_value = ("Question", "Answer")
        
        result = teacher_api.generate_qa_pair(mock_bank_record, "exact")
        
        assert result == ("Question", "Answer")
        assert mock_call.call_count == 1
        assert mock_parse.call_count == 1
    
    @patch.object(TeacherModelAPI, '_call_api')
    def test_generate_qa_pair_authentication_error_no_retry(self, mock_call, teacher_api, mock_bank_record):
        """Test QA pair generation with authentication error (should not retry)"""
        mock_call.side_effect = APIAuthenticationError("Auth failed")
        
        result = teacher_api.generate_qa_pair(mock_bank_record, "exact")
        
        assert result is None
        assert mock_call.call_count == 1  # No retries for auth errors
    
    @patch('app.services.teacher_model.time.sleep')
    @patch.object(TeacherModelAPI, '_call_api')
    def test_generate_qa_pair_retry_on_rate_limit(self, mock_call, mock_sleep, teacher_api, mock_bank_record):
        """Test QA pair generation with retry on rate limit error"""
        # First two calls fail, third succeeds
        mock_call.side_effect = [
            APIRateLimitError("Rate limit"),
            APIRateLimitError("Rate limit"),
            "Question|Answer"
        ]
        
        with patch.object(teacher_api, '_parse_response', return_value=("Q", "A")):
            result = teacher_api.generate_qa_pair(mock_bank_record, "exact")
        
        assert result == ("Q", "A")
        assert mock_call.call_count == 3
        assert mock_sleep.call_count == 2  # Exponential backoff
        
        # Check exponential backoff: 2^0=1, 2^1=2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
    
    @patch('app.services.teacher_model.time.sleep')
    @patch.object(TeacherModelAPI, '_call_api')
    def test_generate_qa_pair_max_retries_exceeded(self, mock_call, mock_sleep, teacher_api, mock_bank_record):
        """Test QA pair generation fails after max retries"""
        mock_call.side_effect = APITimeoutError("Timeout")
        
        result = teacher_api.generate_qa_pair(mock_bank_record, "exact")
        
        assert result is None
        assert mock_call.call_count == 3  # max_retries
        assert mock_sleep.call_count == 2  # Retries - 1
    
    @patch.object(TeacherModelAPI, 'generate_qa_pair')
    def test_generate_batch_qa_pairs(self, mock_generate, teacher_api, mock_bank_record):
        """Test batch QA pair generation"""
        # Create multiple records
        records = [mock_bank_record, mock_bank_record]
        question_types = ["exact", "fuzzy"]
        
        # Mock successful generation
        mock_generate.return_value = ("Question", "Answer")
        
        results = teacher_api.generate_batch_qa_pairs(records, question_types)
        
        assert results["total_records"] == 2
        assert results["total_attempts"] == 4  # 2 records * 2 types
        assert results["successful"] == 4
        assert results["failed"] == 0
        assert len(results["qa_pairs"]) == 4
        assert len(results["errors"]) == 0
    
    @patch.object(TeacherModelAPI, 'generate_qa_pair')
    def test_generate_batch_qa_pairs_with_failures(self, mock_generate, teacher_api, mock_bank_record):
        """Test batch QA pair generation with some failures"""
        records = [mock_bank_record, mock_bank_record]
        question_types = ["exact", "fuzzy"]
        
        # Mock alternating success and failure
        mock_generate.side_effect = [
            ("Q1", "A1"),  # Success
            None,          # Failure
            ("Q2", "A2"),  # Success
            None           # Failure
        ]
        
        results = teacher_api.generate_batch_qa_pairs(records, question_types)
        
        assert results["total_records"] == 2
        assert results["total_attempts"] == 4
        assert results["successful"] == 2
        assert results["failed"] == 2
        assert len(results["qa_pairs"]) == 2
        assert len(results["errors"]) == 2
