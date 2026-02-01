#!/usr/bin/env python3
"""
答案生成质量简化测试

**Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
**验证需求: Requirements 5.3, 5.4, 5.5**

本测试验证RAG系统答案生成的核心功能。
"""

import pytest
import sys
import os

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


class TestAnswerGenerationSimple:
    """答案生成简化测试类"""
    
    def test_single_bank_answer_generation(self):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        测试单个银行记录的答案生成
        """
        query_service = get_shared_query_service()
        
        # 测试数据
        question = "中国工商银行股份有限公司北京西单支行"
        rag_results = [{
            "bank_name": "中国工商银行股份有限公司北京西单支行",
            "bank_code": "102100024506",
            "clearing_code": "102100024506",
            "final_score": 9.5,
            "similarity_score": 0.98
        }]
        
        # 生成答案
        answer = query_service.generate_answer_with_small_model(question, rag_results)
        
        # 验证答案
        assert answer is not None, "答案不应为空"
        assert isinstance(answer, str), "答案应为字符串类型"
        assert len(answer.strip()) > 0, "答案不应为空字符串"
        assert "中国工商银行股份有限公司北京西单支行" in answer, "答案应包含银行名称"
        assert "102100024506" in answer, "答案应包含联行号"
    
    def test_multiple_banks_answer_generation(self):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        测试多个银行记录的答案生成
        """
        query_service = get_shared_query_service()
        
        # 测试数据
        question = "工商银行"
        rag_results = [
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
            }
        ]
        
        # 生成答案
        answer = query_service.generate_answer_with_small_model(question, rag_results)
        
        # 验证答案
        assert answer is not None, "答案不应为空"
        assert isinstance(answer, str), "答案应为字符串类型"
        assert len(answer.strip()) > 0, "答案不应为空字符串"
        
        # 验证答案包含至少一个银行的信息
        contains_bank_info = False
        for bank in rag_results:
            if bank['bank_name'] in answer or bank['bank_code'] in answer:
                contains_bank_info = True
                break
        assert contains_bank_info, "答案应包含至少一个银行的信息"
    
    def test_no_results_answer_generation(self):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        测试无结果时的答案生成
        """
        query_service = get_shared_query_service()
        
        # 测试无结果答案
        answer = query_service._format_no_match_answer("不存在的银行")
        
        # 验证答案
        assert answer is not None, "无结果答案不应为空"
        assert len(answer) > 10, "无结果答案应提供足够的信息"
        assert "抱歉" in answer or "未找到" in answer, "无结果答案应包含道歉或说明"
    
    def test_confidence_calculation(self):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        测试置信度计算
        """
        query_service = get_shared_query_service()
        
        # 测试数据
        question = "中国工商银行股份有限公司北京西单支行"
        bank_record = {
            "bank_name": "中国工商银行股份有限公司北京西单支行",
            "bank_code": "102100024506",
            "clearing_code": "102100024506",
            "final_score": 9.5,
            "similarity_score": 0.98
        }
        
        # 计算置信度
        confidence = query_service._calculate_single_result_confidence(question, bank_record)
        
        # 验证置信度
        assert 0.0 <= confidence <= 1.0, f"置信度应在0.0-1.0范围内，实际：{confidence}"
        assert confidence >= 0.9, "完全匹配的置信度应该很高"
    
    def test_enhanced_entity_extraction(self):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        测试增强实体提取功能
        """
        query_service = get_shared_query_service()
        
        # 测试数据
        question = "中国工商银行股份有限公司北京西单支行"
        
        # 执行实体提取
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
        
        # 验证具体提取结果
        assert entities['is_full_name'] == True, "应识别为完整银行名称"
        assert "中国工商银行" in entities['bank_names'], "应提取出银行名称"
        assert "北京" in entities['locations'], "应提取出地理位置"
        assert entities['query_type'] == 'full_name', "查询类型应为full_name"


if __name__ == "__main__":
    # 运行简化测试
    pytest.main([__file__, "-v", "--tb=short"])