"""
Example usage of TeacherModelAPI
示例：如何使用大模型API客户端

注意：需要配置有效的QWEN_API_KEY才能运行此示例
"""
from app.services.teacher_model import TeacherModelAPI
from app.models.bank_code import BankCode
from unittest.mock import Mock


def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("示例 1: 基本使用")
    print("=" * 60)
    
    # 创建API客户端
    api = TeacherModelAPI(
        api_key="your_api_key_here",  # 替换为实际的API key
        max_retries=3,
        timeout=30
    )
    
    # 创建一个模拟的银行记录
    bank_record = Mock(spec=BankCode)
    bank_record.id = 1
    bank_record.bank_name = "中国工商银行北京分行"
    bank_record.bank_code = "102100000026"
    bank_record.clearing_code = "102100000000"
    
    print(f"\n银行记录:")
    print(f"  ID: {bank_record.id}")
    print(f"  名称: {bank_record.bank_name}")
    print(f"  联行号: {bank_record.bank_code}")
    print(f"  清算行行号: {bank_record.clearing_code}")
    
    # 生成不同类型的问答对
    question_types = ["exact", "fuzzy", "reverse", "natural"]
    
    print(f"\n生成问答对:")
    for q_type in question_types:
        print(f"\n  问题类型: {q_type}")
        
        # 注意：这里会实际调用API，需要有效的API key
        # result = api.generate_qa_pair(bank_record, q_type)
        # if result:
        #     question, answer = result
        #     print(f"    问题: {question}")
        #     print(f"    答案: {answer}")
        # else:
        #     print(f"    生成失败")
        
        # 演示prompt构建（不实际调用API）
        prompt = api._build_prompt(bank_record, q_type)
        print(f"    Prompt预览: {prompt[:100]}...")


def example_batch_generation():
    """批量生成示例"""
    print("\n" + "=" * 60)
    print("示例 2: 批量生成")
    print("=" * 60)
    
    # 创建API客户端
    api = TeacherModelAPI(
        api_key="your_api_key_here",
        max_retries=3
    )
    
    # 创建多个模拟的银行记录
    records = []
    banks = [
        ("中国工商银行北京分行", "102100000026", "102100000000"),
        ("中国农业银行上海分行", "103290000017", "103290000000"),
        ("中国银行广州分行", "104581000013", "104581000000"),
    ]
    
    for i, (name, code, clearing) in enumerate(banks, 1):
        record = Mock(spec=BankCode)
        record.id = i
        record.bank_name = name
        record.bank_code = code
        record.clearing_code = clearing
        records.append(record)
    
    print(f"\n准备生成 {len(records)} 条记录的问答对")
    print(f"问题类型: exact, fuzzy")
    
    # 批量生成（需要有效的API key）
    # results = api.generate_batch_qa_pairs(records, ["exact", "fuzzy"])
    # 
    # print(f"\n生成结果:")
    # print(f"  总记录数: {results['total_records']}")
    # print(f"  总尝试次数: {results['total_attempts']}")
    # print(f"  成功: {results['successful']}")
    # print(f"  失败: {results['failed']}")
    # print(f"  生成的问答对数量: {len(results['qa_pairs'])}")
    
    print("\n注意: 实际调用需要配置有效的QWEN_API_KEY")


def example_error_handling():
    """错误处理示例"""
    print("\n" + "=" * 60)
    print("示例 3: 错误处理和重试机制")
    print("=" * 60)
    
    print("\n特性:")
    print("  1. 自动重试机制（最多3次）")
    print("  2. 指数退避策略（1秒、2秒、4秒）")
    print("  3. 详细的日志记录")
    print("  4. 错误分类处理:")
    print("     - 认证错误: 不重试，立即返回")
    print("     - 限流错误: 自动重试")
    print("     - 超时错误: 自动重试")
    print("     - 服务器错误: 自动重试")
    
    print("\n日志示例:")
    print("  [INFO] Generating QA pair - Record ID: 1, Type: exact, Attempt: 1/3")
    print("  [WARNING] API call failed (attempt 1/3): Rate limit exceeded")
    print("  [INFO] Retrying in 1 seconds...")
    print("  [INFO] QA pair generated successfully - Record ID: 1, Type: exact, Time: 2.34s")


def example_response_parsing():
    """响应解析示例"""
    print("\n" + "=" * 60)
    print("示例 4: API响应解析")
    print("=" * 60)
    
    api = TeacherModelAPI(api_key="test_key")
    
    # 测试不同的响应格式
    test_cases = [
        ("中国工商银行北京分行的联行号是什么？|102100000026", True),
        ("  工行北京  |  中国工商银行北京分行的联行号是102100000026  ", True),
        ("Invalid response without separator", False),
        ("|", False),
    ]
    
    print("\n解析测试:")
    for response, should_succeed in test_cases:
        print(f"\n  输入: {response[:50]}...")
        try:
            question, answer = api._parse_response(response)
            print(f"  ✓ 成功")
            print(f"    问题: {question}")
            print(f"    答案: {answer}")
        except ValueError as e:
            if should_succeed:
                print(f"  ✗ 意外失败: {e}")
            else:
                print(f"  ✓ 预期失败: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TeacherModelAPI 使用示例")
    print("=" * 60)
    
    example_basic_usage()
    example_batch_generation()
    example_error_handling()
    example_response_parsing()
    
    print("\n" + "=" * 60)
    print("示例完成")
    print("=" * 60)
    print("\n提示: 要实际调用API，请在.env文件中配置QWEN_API_KEY")
