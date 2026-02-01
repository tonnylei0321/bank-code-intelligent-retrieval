#!/usr/bin/env python3
"""
修复智能问答搜索问题

问题：智能问答服务没有检索到Redis中的数据
原因：小模型服务的回退分析没有正确提取银行名称
解决：改进回退分析的银行名称提取逻辑
"""

import re
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'mvp'))

def fix_fallback_analysis():
    """修复回退分析函数"""
    
    file_path = "mvp/app/services/small_model_service.py"
    
    # 读取原文件
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义新的回退分析函数
    new_fallback_analysis = '''    def _fallback_analysis(self, question: str) -> Dict[str, Any]:
        """
        备用分析方法（基于规则）
        
        Args:
            question: 用户问题
        
        Returns:
            基础分析结果
        """
        result = {
            "question_type": "general_query",
            "bank_name": None,
            "branch_name": None,
            "location": None,
            "bank_code": None,
            "intent": "查询银行相关信息",
            "keywords": [],
            "confidence": 0.6,
            "original_question": question,
            "model_used": "fallback_rules",
            "analysis_time": datetime.now().isoformat()
        }
        
        question_lower = question.lower()
        
        # 简单的规则匹配
        if "联行号" in question or "行号" in question:
            result["question_type"] = "bank_code_query"
            result["intent"] = "查询银行联行号"
        
        elif "支行" in question or "分行" in question:
            result["question_type"] = "branch_query"
            result["intent"] = "查询支行信息"
        
        elif any(bank in question for bank in ["工商银行", "农业银行", "中国银行", "建设银行"]):
            result["question_type"] = "bank_name_query"
            result["intent"] = "查询银行信息"
        
        # 改进的银行名称提取逻辑
        bank_name = self._extract_bank_name_from_question(question)
        if bank_name:
            result["bank_name"] = bank_name
            result["question_type"] = "bank_name_query"
            result["confidence"] = 0.8
        
        # 提取联行号
        bank_code = self._extract_bank_code_from_question(question)
        if bank_code:
            result["bank_code"] = bank_code
            result["question_type"] = "bank_code_query"
            result["confidence"] = 0.9
        
        # 提取关键词
        keywords = self._extract_keywords_from_question(question)
        result["keywords"] = keywords
        
        return result
    
    def _extract_bank_name_from_question(self, question: str) -> str:
        """从问题中提取银行名称"""
        # 常见银行名称模式
        bank_patterns = [
            r'(中国工商银行股份有限公司[^的？]*?支行)',
            r'(中国农业银行股份有限公司[^的？]*?支行)',
            r'(中国银行股份有限公司[^的？]*?支行)',
            r'(中国建设银行股份有限公司[^的？]*?支行)',
            r'(交通银行股份有限公司[^的？]*?支行)',
            r'(招商银行股份有限公司[^的？]*?支行)',
            r'(中国民生银行股份有限公司[^的？]*?支行)',
            r'(中信银行股份有限公司[^的？]*?支行)',
            r'(上海浦东发展银行股份有限公司[^的？]*?支行)',
            r'(兴业银行股份有限公司[^的？]*?支行)',
            r'(平安银行股份有限公司[^的？]*?支行)',
            r'(华夏银行股份有限公司[^的？]*?支行)',
            r'(光大银行股份有限公司[^的？]*?支行)',
            r'(广发银行股份有限公司[^的？]*?支行)',
            r'([^，。！？]*?银行[^，。！？]*?支行)',
            r'([^，。！？]*?银行[^，。！？]*?分行)',
        ]
        
        for pattern in bank_patterns:
            match = re.search(pattern, question)
            if match:
                bank_name = match.group(1).strip()
                # 清理银行名称
                bank_name = bank_name.replace('的', '').replace('？', '').replace('?', '')
                if len(bank_name) > 5:  # 确保是有效的银行名称
                    return bank_name
        
        return None
    
    def _extract_bank_code_from_question(self, question: str) -> str:
        """从问题中提取联行号"""
        # 联行号通常是12位数字
        code_pattern = r'(\\d{12})'
        match = re.search(code_pattern, question)
        if match:
            return match.group(1)
        return None
    
    def _extract_keywords_from_question(self, question: str) -> list:
        """从问题中提取关键词"""
        # 移除标点符号和常用词
        import jieba
        
        # 如果jieba不可用，使用简单分词
        try:
            words = jieba.lcut(question)
        except:
            # 简单分词
            words = []
            current_word = ""
            for char in question:
                if char.isalnum() or char in "中英文字符":
                    current_word += char
                else:
                    if current_word:
                        words.append(current_word)
                        current_word = ""
            if current_word:
                words.append(current_word)
        
        # 过滤停用词和短词
        stop_words = {'的', '是', '在', '有', '和', '与', '或', '但', '而', '了', '吗', '呢', '吧', '啊', '什么', '哪个', '怎么', '如何'}
        keywords = []
        for word in words:
            if len(word) >= 2 and word not in stop_words:
                keywords.append(word)
        
        return list(set(keywords))[:10]  # 限制关键词数量'''
    
    # 查找并替换_fallback_analysis函数
    pattern = r'    def _fallback_analysis\(self, question: str\) -> Dict\[str, Any\]:.*?return result'
    
    if re.search(pattern, content, re.DOTALL):
        # 替换函数
        new_content = re.sub(pattern, new_fallback_analysis, content, flags=re.DOTALL)
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ 成功修复小模型服务的回退分析函数")
        return True
    else:
        print("❌ 未找到_fallback_analysis函数")
        return False

def test_fixed_analysis():
    """测试修复后的分析功能"""
    print("\n🧪 测试修复后的分析功能...")
    
    # 导入修复后的服务
    try:
        from app.services.small_model_service import SmallModelService
        
        # 创建服务实例
        service = SmallModelService()
        
        # 测试问题
        test_question = "中国工商银行股份有限公司上海市西虹桥支行的联行号是什么？"
        
        # 调用回退分析
        result = service._fallback_analysis(test_question)
        
        print(f"问题: {test_question}")
        print(f"分析结果:")
        print(f"  问题类型: {result.get('question_type')}")
        print(f"  银行名称: {result.get('bank_name')}")
        print(f"  置信度: {result.get('confidence')}")
        print(f"  关键词: {result.get('keywords')}")
        
        if result.get('bank_name'):
            print("✅ 银行名称提取成功")
            return True
        else:
            print("❌ 银行名称提取失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 修复智能问答搜索问题")
    print("=" * 50)
    
    # 1. 修复回退分析函数
    print("1️⃣ 修复小模型服务的回退分析函数...")
    if not fix_fallback_analysis():
        print("修复失败，退出")
        return
    
    # 2. 测试修复结果
    print("\n2️⃣ 测试修复结果...")
    if test_fixed_analysis():
        print("\n🎉 修复完成！智能问答服务现在应该能够正确检索Redis中的数据了")
        print("\n📋 修复内容:")
        print("   - 改进了银行名称提取逻辑")
        print("   - 添加了联行号提取功能")
        print("   - 优化了关键词提取算法")
        print("   - 提高了分析置信度")
        
        print("\n🚀 建议:")
        print("   1. 重启后端服务以应用修复")
        print("   2. 重新测试智能问答功能")
        print("   3. 验证Redis检索是否正常工作")
    else:
        print("\n❌ 修复验证失败，请检查代码")

if __name__ == "__main__":
    main()