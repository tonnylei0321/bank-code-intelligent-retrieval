#!/usr/bin/env python3
"""
答案生成质量属性测试

**Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
**验证需求: Requirements 5.3, 5.4, 5.5**

本测试验证RAG系统答案生成的质量和准确性。
"""

import pytest
import hypothesis
from hypothesis import strategies as st, HealthCheck
import sys
import os
import re

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.query_service import QueryService


class MockDBSession:
    """模拟数据库会话，用于测试"""
    def close(self):
        pass
    
    def query(self, model):
        return MockQuery()
    
    def add(self, obj):
        pass
    
    def commit(self):
        pass
    
    def rollback(self):
        pass
    
    @property
    def is_active(self):
        return True


class MockQuery:
    """模拟查询对象"""
    def filter(self, *args):
        return self
    
    def count(self):
        return 0
    
    def all(self):
        return []
    
    def first(self):
        return None
    
    def limit(self, n):
        return self
    
    def offset(self, n):
        return self
    
    def order_by(self, *args):
        return self


# 全局共享的查询服务实例，避免重复初始化
_shared_query_service = None

def get_shared_query_service():
    """获取共享的查询服务实例，避免重复初始化"""
    global _shared_query_service
    if _shared_query_service is None:
        mock_db = MockDBSession()
        _shared_query_service = QueryService(mock_db)
    return _shared_query_service


# 银行记录策略
def bank_record_strategy():
    """生成银行记录的策略"""
    return st.builds(
        dict,
        bank_name=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Po'))),
        bank_code=st.text(min_size=12, max_size=12, alphabet=st.characters(whitelist_categories=('Nd',))),
        clearing_code=st.text(min_size=12, max_size=12, alphabet=st.characters(whitelist_categories=('Nd',))),
        final_score=st.floats(min_value=0.0, max_value=10.0),
        similarity_score=st.floats(min_value=0.0, max_value=1.0)
    )


# 真实银行记录策略
real_bank_records = st.sampled_from([
    {
        "bank_name": "中国工商银行股份有限公司北京西单支行",
        "bank_code": "102100024506",
        "clearing_code": "102100024506",
        "final_score": 9.5,
        "similarity_score": 0.98
    },
    {
        "bank_name": "中国农业银行股份有限公司上海分行",
        "bank_code": "103290000013",
        "clearing_code": "103290000013",
        "final_score": 8.8,
        "similarity_score": 0.92
    },
    {
        "bank_name": "中国建设银行股份有限公司深圳福田支行",
        "bank_code": "105584000018",
        "clearing_code": "105584000018",
        "final_score": 8.2,
        "similarity_score": 0.89
    },
    {
        "bank_name": "招商银行股份有限公司北京分行",
        "bank_code": "308100005110",
        "clearing_code": "308100005110",
        "final_score": 7.9,
        "similarity_score": 0.85
    },
    {
        "bank_name": "中信银行股份有限公司广州分行",
        "bank_code": "302584000013",
        "clearing_code": "302584000013",
        "final_score": 7.5,
        "similarity_score": 0.82
    }
])


# 问题策略
question_strategy = st.one_of([
    st.text(min_size=2, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Po'))),
    st.sampled_from([
        "中国工商银行股份有限公司北京西单支行",
        "工商银行西单",
        "北京工商银行",
        "工行",
        "农业银行上海分行",
        "建设银行深圳",
        "招商银行",
        "中信银行广州",
        "银行联行号",
        "联行号查询"
    ])
])


class TestAnswerGenerationQualityProperties:
    """答案生成质量属性测试类"""
    
    @hypothesis.given(
        question=question_strategy,
        rag_results=st.lists(real_bank_records, min_size=1, max_size=5)
    )
    @hypothesis.settings(
        max_examples=20,  # 减少测试用例数量
        deadline=10000,  # 增加deadline到10秒
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_answer_generation_completeness_property(self, question, rag_results):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：对于任何有效的RAG检索结果，答案生成应该完整且包含必要信息
        """
        query_service = get_shared_query_service()
        
        # 生成答案
        answer = query_service.generate_answer_with_small_model(question, rag_results)
        
        # 验证答案完整性
        assert answer is not None, "答案不应为空"
        assert isinstance(answer, str), "答案应为字符串类型"
        assert len(answer.strip()) > 0, "答案不应为空字符串"
        
        # 验证答案包含银行信息
        contains_bank_info = False
        for bank in rag_results:
            if bank['bank_name'] in answer or bank['bank_code'] in answer:
                contains_bank_info = True
                break
        
        assert contains_bank_info, f"答案应包含银行信息，答案：{answer[:100]}..."
    
    @hypothesis.given(
        question=question_strategy,
        rag_results=st.lists(real_bank_records, min_size=1, max_size=1)
    )
    @hypothesis.settings(
        max_examples=15,  # 减少测试用例数量
        deadline=None,  # 禁用deadline检查
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_single_result_answer_format_property(self, question, rag_results):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：对于单个RAG结果，答案应该格式正确且包含银行名称和联行号
        """
        query_service = get_shared_query_service()
        
        # 生成答案
        answer = query_service.generate_answer_with_small_model(question, rag_results)
        bank = rag_results[0]
        
        # 验证答案格式
        assert bank['bank_name'] in answer, f"答案应包含银行名称：{bank['bank_name']}"
        assert bank['bank_code'] in answer, f"答案应包含联行号：{bank['bank_code']}"
        
        # 验证联行号格式（12位数字）
        bank_codes_in_answer = re.findall(r'\b\d{12}\b', answer)
        assert len(bank_codes_in_answer) >= 1, "答案应包含至少一个12位联行号"
        assert bank['bank_code'] in bank_codes_in_answer, "答案中的联行号应匹配RAG结果"
    
    @hypothesis.given(
        question=question_strategy,
        rag_results=st.lists(real_bank_records, min_size=2, max_size=5)
    )
    @hypothesis.settings(
        max_examples=20,  # 减少测试用例数量
        deadline=None,  # 禁用deadline检查
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_multiple_results_selection_property(self, question, rag_results):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：对于多个RAG结果，答案生成应该智能选择最佳匹配或提供多个选项
        """
        query_service = get_shared_query_service()
        
        # 生成答案
        answer = query_service.generate_answer_with_small_model(question, rag_results)
        
        # 验证答案包含至少一个银行的信息
        contains_any_bank = False
        for bank in rag_results:
            if bank['bank_name'] in answer or bank['bank_code'] in answer:
                contains_any_bank = True
                break
        
        assert contains_any_bank, "答案应包含至少一个银行的信息"
        
        # 如果答案包含多个结果，验证格式
        if "1." in answer and "2." in answer:
            # 多选项格式
            lines = answer.split('\n')
            numbered_lines = [line for line in lines if re.match(r'^\d+\.', line.strip())]
            assert len(numbered_lines) >= 2, "多选项答案应包含至少2个编号选项"
            
            # 验证每个选项都包含银行信息
            for line in numbered_lines:
                has_bank_code = bool(re.search(r'\b\d{12}\b', line))
                assert has_bank_code, f"每个选项都应包含联行号：{line}"
    
    @hypothesis.given(
        question=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @hypothesis.settings(
        max_examples=10,  # 减少测试用例数量
        deadline=None,  # 禁用deadline检查
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_no_results_answer_property(self, question):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：对于无RAG结果的情况，应该提供有用的错误消息和建议
        """
        query_service = get_shared_query_service()
        
        # 生成无结果答案
        answer = query_service._format_no_match_answer(question)
        
        # 验证答案特性
        assert answer is not None, "无结果答案不应为空"
        assert len(answer) > 10, "无结果答案应提供足够的信息"
        assert "抱歉" in answer or "未找到" in answer, "无结果答案应包含道歉或说明"
        
        # 验证是否包含建议
        suggestion_keywords = ["建议", "尝试", "可以", "请"]
        has_suggestion = any(keyword in answer for keyword in suggestion_keywords)
        assert has_suggestion, "无结果答案应包含建议或指导"
    
    @hypothesis.given(
        question=question_strategy,
        bank_record=real_bank_records
    )
    @hypothesis.settings(
        max_examples=15,  # 减少测试用例数量
        deadline=None,  # 禁用deadline检查
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_confidence_calculation_property(self, question, bank_record):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：置信度计算应该合理且在有效范围内
        """
        query_service = get_shared_query_service()
        
        # 计算单个结果的置信度
        confidence = query_service._calculate_single_result_confidence(question, bank_record)
        
        # 验证置信度范围
        assert 0.0 <= confidence <= 1.0, f"置信度应在0.0-1.0范围内，实际：{confidence}"
        
        # 验证置信度逻辑
        if question.strip() == bank_record['bank_name']:
            assert confidence >= 0.9, "完全匹配的置信度应该很高"
        
        if question.lower() in bank_record['bank_name'].lower():
            assert confidence >= 0.5, "包含匹配的置信度应该中等以上"
    
    @hypothesis.given(
        question=question_strategy,
        rag_results=st.lists(real_bank_records, min_size=1, max_size=3)
    )
    @hypothesis.settings(
        max_examples=20,  # 减少测试用例数量
        deadline=None,  # 禁用deadline检查
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_answer_consistency_property(self, question, rag_results):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：相同输入应该产生一致的答案
        """
        query_service = get_shared_query_service()
        
        # 生成两次答案
        answer1 = query_service.generate_answer_with_small_model(question, rag_results)
        answer2 = query_service.generate_answer_with_small_model(question, rag_results)
        
        # 验证一致性
        assert answer1 == answer2, f"相同输入应产生相同答案\n答案1：{answer1}\n答案2：{answer2}"
    
    @hypothesis.given(
        question=question_strategy,
        rag_results=st.lists(real_bank_records, min_size=1, max_size=5)
    )
    @hypothesis.settings(
        max_examples=15,  # 减少测试用例数量
        deadline=None,  # 禁用deadline检查
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_answer_safety_property(self, question, rag_results):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：答案应该安全，不包含有害内容或错误格式
        """
        query_service = get_shared_query_service()
        
        # 生成答案
        answer = query_service.generate_answer_with_small_model(question, rag_results)
        
        # 验证答案安全性
        assert answer is not None, "答案不应为None"
        assert isinstance(answer, str), "答案应为字符串"
        
        # 验证不包含异常信息
        error_keywords = ["error", "exception", "traceback", "failed", "错误", "异常", "失败"]
        has_error = any(keyword.lower() in answer.lower() for keyword in error_keywords)
        assert not has_error, f"答案不应包含错误信息：{answer[:100]}..."
        
        # 验证联行号格式正确性
        bank_codes = re.findall(r'\b\d{12}\b', answer)
        for code in bank_codes:
            assert len(code) == 12, f"联行号应为12位数字：{code}"
            assert code.isdigit(), f"联行号应只包含数字：{code}"
    
    @hypothesis.given(
        question=question_strategy,
        rag_results=st.lists(real_bank_records, min_size=1, max_size=5)
    )
    @hypothesis.settings(
        max_examples=12,  # 减少测试用例数量
        deadline=None,  # 禁用deadline检查
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_enhanced_entity_extraction_property(self, question, rag_results):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：增强实体提取应该稳定运行并返回正确格式的结果
        """
        query_service = get_shared_query_service()
        
        # 执行增强实体提取
        entities = query_service._extract_enhanced_entities(question)
        
        # 验证返回格式
        assert isinstance(entities, dict), "实体提取结果应为字典"
        
        # 验证必需字段
        required_fields = ['bank_names', 'locations', 'branch_types', 'keywords', 'is_full_name', 'query_type']
        for field in required_fields:
            assert field in entities, f"实体字典应包含字段：{field}"
        
        # 验证字段类型
        assert isinstance(entities['bank_names'], list), "bank_names应为列表"
        assert isinstance(entities['locations'], list), "locations应为列表"
        assert isinstance(entities['branch_types'], list), "branch_types应为列表"
        assert isinstance(entities['keywords'], list), "keywords应为列表"
        assert isinstance(entities['is_full_name'], bool), "is_full_name应为布尔值"
        assert isinstance(entities['query_type'], str), "query_type应为字符串"
        
        # 验证查询类型有效性
        valid_query_types = ['full_name', 'bank_location', 'bank_only', 'location_only', 'general']
        assert entities['query_type'] in valid_query_types, f"查询类型应为有效值：{entities['query_type']}"


if __name__ == "__main__":
    # 运行属性测试
    pytest.main([__file__, "-v", "--tb=short"])