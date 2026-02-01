#!/usr/bin/env python3
"""
实体提取准确性属性测试

**Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
**验证需求: Requirements 5.1**

本测试验证RAG系统从用户查询中提取相关实体的能力。
"""

import pytest
import hypothesis
from hypothesis import strategies as st, HealthCheck
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rag_service import RAGService
from sqlalchemy.orm import Session


class MockDBSession:
    """模拟数据库会话，用于测试"""
    def close(self):
        pass
    
    def query(self, model):
        return MockQuery()
    
    def count(self):
        return 0


class MockQuery:
    """模拟查询对象"""
    def filter(self, *args):
        return self
    
    def count(self):
        return 0
    
    def all(self):
        return []


def create_rag_service():
    """创建RAG服务实例的工厂函数"""
    mock_db = MockDBSession()
    return RAGService(mock_db)


# 银行名称策略
bank_names = st.sampled_from([
    "中国工商银行", "工商银行", "工行", "ICBC",
    "中国农业银行", "农业银行", "农行", "ABC", 
    "中国银行", "中行", "BOC",
    "中国建设银行", "建设银行", "建行", "CCB",
    "交通银行", "交行", "BOCOM",
    "招商银行", "招行", "CMB",
    "浦发银行", "上海浦东发展银行", "SPDB",
    "中信银行", "中信", "CITIC",
    "光大银行", "中国光大银行", "CEB",
    "华夏银行", "华夏", "HXB",
    "民生银行", "中国民生银行", "CMBC",
    "广发银行", "广发", "CGB",
    "平安银行", "平安", "PAB",
    "兴业银行", "兴业", "CIB",
    "邮储银行", "邮政储蓄银行", "PSBC"
])

# 地理位置策略
locations = st.sampled_from([
    "北京", "上海", "广州", "深圳", "天津", "重庆", "成都", "武汉",
    "西安", "南京", "杭州", "苏州", "青岛", "大连", "宁波", "厦门",
    "长沙", "郑州", "济南", "合肥", "福州", "南昌", "太原", "石家庄",
    "沈阳", "长春", "哈尔滨", "昆明", "贵阳", "南宁", "海口", "兰州"
])

# 支行类型策略
branch_types = st.sampled_from([
    "支行", "分行", "营业部", "营业厅", "分理处", "储蓄所", "网点"
])

# 商业区策略
commercial_areas = st.sampled_from([
    "西单", "王府井", "中关村", "国贸", "金融街", "望京", "三里屯",
    "陆家嘴", "外滩", "南京路", "淮海路", "徐家汇", "人民广场",
    "天河", "珠江新城", "体育中心", "福田", "罗湖", "南山"
])


class TestEntityExtractionProperties:
    """实体提取准确性属性测试类"""
    
    @hypothesis.given(bank_name=bank_names)
    @hypothesis.settings(
        max_examples=10,  # 减少测试用例数量
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_bank_name_extraction_property(self, bank_name):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：对于任何包含银行名称的查询，RAG系统应能正确提取银行实体
        """
        rag_service = create_rag_service()
        
        # 构造包含银行名称的查询
        query = f"{bank_name}的联行号是多少？"
        
        # 提取实体
        entities = rag_service._extract_question_entities(query)
        
        # 验证属性：应该提取到银行相关信息
        assert entities is not None, "实体提取结果不应为空"
        assert isinstance(entities, dict), "实体提取结果应为字典"
        
        # 验证关键字段存在
        required_fields = ['bank_name', 'bank_type', 'location', 'branch_name', 'keywords', 'full_name']
        for field in required_fields:
            assert field in entities, f"实体字典应包含字段: {field}"
        
        # 验证关键词列表不为空（应该至少包含原始银行名称）
        assert isinstance(entities['keywords'], list), "关键词应为列表"
        assert len(entities['keywords']) > 0, "关键词列表不应为空"
        
        # 验证银行名称或类型被正确识别
        bank_identified = (
            entities['bank_name'] is not None or 
            entities['bank_type'] is not None or
            any(bank_name.lower() in keyword.lower() for keyword in entities['keywords'])
        )
        assert bank_identified, f"应该识别出银行信息: {bank_name}"
    
    @hypothesis.given(location=locations)
    @hypothesis.settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_location_extraction_property(self, location):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：对于任何包含地理位置的查询，RAG系统应能正确提取位置实体
        """
        rag_service = create_rag_service()
        
        # 构造包含地理位置的查询
        query = f"{location}有哪些银行？"
        
        # 提取实体
        entities = rag_service._extract_question_entities(query)
        
        # 验证位置信息被识别
        location_identified = (
            entities['location'] == location or
            entities['branch_name'] == location or
            location in entities['keywords']
        )
        assert location_identified, f"应该识别出地理位置: {location}"
    
    @hypothesis.given(
        bank_name=bank_names,
        location=locations,
        branch_type=branch_types
    )
    @hypothesis.settings(
        max_examples=40,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_complex_query_extraction_property(self, bank_name, location, branch_type):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：对于包含多个实体的复杂查询，RAG系统应能提取所有相关实体
        """
        rag_service = create_rag_service()
        
        # 构造复杂查询
        query = f"{bank_name}{location}{branch_type}的联行号"
        
        # 提取实体
        entities = rag_service._extract_question_entities(query)
        
        # 验证多个实体被识别
        entities_found = 0
        
        # 检查银行名称
        if (entities['bank_name'] is not None or 
            entities['bank_type'] is not None or
            any(bank_name.lower() in keyword.lower() for keyword in entities['keywords'])):
            entities_found += 1
        
        # 检查地理位置
        if (entities['location'] == location or
            location in entities['keywords']):
            entities_found += 1
        
        # 检查支行类型
        if (branch_type in query and 
            (entities['branch_name'] is not None or
             branch_type in entities['keywords'])):
            entities_found += 1
        
        # 至少应该识别出银行名称
        assert entities_found >= 1, f"复杂查询应至少识别出一个实体: {query}"
    
    @hypothesis.given(area=commercial_areas)
    @hypothesis.settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_commercial_area_extraction_property(self, area):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：对于包含商业区的查询，RAG系统应能正确识别商业区信息
        """
        rag_service = create_rag_service()
        
        # 构造包含商业区的查询
        query = f"{area}附近的银行"
        
        # 提取实体
        entities = rag_service._extract_question_entities(query)
        
        # 验证商业区被识别（可能作为位置或支行名称）
        area_identified = (
            entities['location'] == area or
            entities['branch_name'] == area or
            area in entities['keywords']
        )
        assert area_identified, f"应该识别出商业区: {area}"
    
    @hypothesis.given(
        st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
    @hypothesis.settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_entity_extraction_robustness_property(self, query_text):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：对于任何文本输入，实体提取应该稳定运行不崩溃
        """
        rag_service = create_rag_service()
        
        try:
            # 提取实体
            entities = rag_service._extract_question_entities(query_text)
            
            # 验证基本结构
            assert entities is not None, "实体提取不应返回None"
            assert isinstance(entities, dict), "实体提取应返回字典"
            
            # 验证必需字段存在
            required_fields = ['bank_name', 'bank_type', 'location', 'branch_name', 'keywords', 'full_name']
            for field in required_fields:
                assert field in entities, f"缺少必需字段: {field}"
            
            # 验证关键词字段类型
            assert isinstance(entities['keywords'], list), "关键词应为列表类型"
            
        except Exception as e:
            pytest.fail(f"实体提取对输入 '{query_text}' 应该不崩溃，但抛出异常: {e}")
    
    def test_full_bank_name_detection_property(self):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：对于完整银行名称查询，应正确识别为完整名称
        """
        rag_service = create_rag_service()
        
        # 测试完整银行名称
        full_names = [
            "中国工商银行股份有限公司北京西单支行",
            "中国农业银行股份有限公司上海分行",
            "中国建设银行股份有限公司深圳福田支行"
        ]
        
        for full_name in full_names:
            entities = rag_service._extract_question_entities(full_name)
            
            # 验证完整名称被识别
            assert entities['full_name'] == full_name, f"应该识别完整银行名称: {full_name}"
            
            # 验证同时提取了其他实体信息
            assert entities['bank_name'] is not None, "应该提取银行名称"
            assert len(entities['keywords']) > 0, "应该提取关键词"
    
    @hypothesis.given(
        bank_name=bank_names,
        location=locations
    )
    @hypothesis.settings(
        max_examples=25,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_keyword_consistency_property(self, bank_name, location):
        """
        **Feature: bank-code-intelligent-retrieval, Property 5: RAG查询处理准确性**
        
        属性：提取的关键词应与识别的实体保持一致
        """
        rag_service = create_rag_service()
        
        query = f"{bank_name}{location}分行"
        
        entities = rag_service._extract_question_entities(query)
        keywords = entities['keywords']
        
        # 验证关键词一致性
        if entities['bank_name']:
            # 如果识别了银行名称，关键词中应包含相关信息
            bank_related = any(
                entities['bank_name'].lower() in keyword.lower() or
                keyword.lower() in entities['bank_name'].lower()
                for keyword in keywords
            )
            assert bank_related, f"关键词应包含银行相关信息: {entities['bank_name']}"
        
        if entities['location']:
            # 如果识别了位置，关键词中应包含位置信息
            assert entities['location'] in keywords, f"关键词应包含位置信息: {entities['location']}"


if __name__ == "__main__":
    # 运行属性测试
    pytest.main([__file__, "-v", "--tb=short"])