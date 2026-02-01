#!/usr/bin/env python3
"""
调试Redis搜索问题
"""

import asyncio
import redis.asyncio as redis
from typing import Dict, Any, List

async def debug_redis_search():
    """调试Redis搜索功能"""
    print("🔍 调试Redis搜索功能")
    print("=" * 50)
    
    # 连接Redis
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True  # 重要：自动解码响应
    )
    
    try:
        # 1. 检查Redis连接
        await redis_client.ping()
        print("✅ Redis连接成功")
        
        # 2. 检查特定银行数据
        print("\n📋 检查特定银行数据...")
        bank_id = await redis_client.get("bank_code:code:102290002916")
        print(f"联行号102290002916对应的bank_id: {bank_id}")
        
        if bank_id:
            bank_data = await redis_client.hgetall(f"bank_code:bank:{bank_id}")
            print(f"银行详细信息:")
            for key, value in bank_data.items():
                print(f"  {key}: {value}")
        
        # 3. 测试不同的搜索方式
        print("\n🔍 测试搜索功能...")
        
        # 测试1: 精确联行号搜索
        print("\n测试1: 精确联行号搜索")
        code_key = "bank_code:code:102290002916"
        result = await redis_client.get(code_key)
        print(f"搜索key: {code_key}")
        print(f"结果: {result}")
        
        # 测试2: 银行名称搜索
        print("\n测试2: 银行名称搜索")
        test_names = [
            "中国工商银行股份有限公司上海市西虹桥支行",
            "工商银行",
            "西虹桥",
            "上海"
        ]
        
        for name in test_names:
            print(f"\n搜索名称: {name}")
            
            # 精确名称匹配
            name_key = f"bank_code:name:{name}"
            exact_result = await redis_client.get(name_key)
            print(f"  精确匹配key: {name_key}")
            print(f"  精确匹配结果: {exact_result}")
            
            # 模糊名称匹配
            pattern = f"bank_code:name:*{name}*"
            keys = await redis_client.keys(pattern)
            print(f"  模糊匹配pattern: {pattern}")
            print(f"  找到keys数量: {len(keys)}")
            if keys:
                print(f"  前5个keys: {keys[:5]}")
        
        # 测试3: 关键词搜索
        print("\n测试3: 关键词搜索")
        keywords = ["工商银行", "西虹桥", "上海"]
        
        for keyword in keywords:
            print(f"\n搜索关键词: {keyword}")
            
            # 精确关键词匹配
            keyword_key = f"bank_code:keyword:{keyword}"
            keyword_result = await redis_client.smembers(keyword_key)
            print(f"  精确关键词key: {keyword_key}")
            print(f"  精确关键词结果: {list(keyword_result)}")
            
            # 模糊关键词匹配
            pattern = f"bank_code:keyword:*{keyword}*"
            keys = await redis_client.keys(pattern)
            print(f"  模糊关键词pattern: {pattern}")
            print(f"  找到keys数量: {len(keys)}")
            if keys:
                print(f"  前5个keys: {keys[:5]}")
        
        # 4. 检查所有银行名称的样本
        print("\n📋 检查银行名称样本...")
        name_keys = await redis_client.keys("bank_code:name:*")
        print(f"总共有 {len(name_keys)} 个银行名称")
        
        # 显示前10个银行名称
        for i, key in enumerate(name_keys[:10]):
            name = key.replace("bank_code:name:", "")
            bank_id = await redis_client.get(key)
            print(f"  {i+1}. {name} -> bank_id: {bank_id}")
        
        # 5. 检查是否有包含"西虹桥"的银行
        print("\n🔍 查找包含'西虹桥'的银行...")
        pattern = "bank_code:name:*西虹桥*"
        matching_keys = await redis_client.keys(pattern)
        print(f"找到 {len(matching_keys)} 个包含'西虹桥'的银行:")
        for key in matching_keys:
            name = key.replace("bank_code:name:", "")
            bank_id = await redis_client.get(key)
            print(f"  {name} -> bank_id: {bank_id}")
        
        # 6. 模拟智能问答服务的搜索逻辑
        print("\n🤖 模拟智能问答搜索逻辑...")
        query = "中国工商银行股份有限公司上海市西虹桥支行的联行号是什么？"
        
        # 自动检测搜索类型
        if len(query) == 12 and query.isdigit():
            search_type = "code"
        elif any(keyword in query for keyword in ["银行", "行", "支行", "分行"]):
            search_type = "name"
        else:
            search_type = "keyword"
        
        print(f"查询: {query}")
        print(f"检测到的搜索类型: {search_type}")
        
        # 执行搜索
        bank_ids = set()
        
        if search_type == "name":
            # 尝试提取银行名称
            bank_names = [
                "中国工商银行股份有限公司上海市西虹桥支行",
                "工商银行上海市西虹桥支行",
                "工商银行西虹桥支行"
            ]
            
            for bank_name in bank_names:
                print(f"\n尝试搜索银行名称: {bank_name}")
                
                # 精确匹配
                name_key = f"bank_code:name:{bank_name}"
                bank_id = await redis_client.get(name_key)
                if bank_id:
                    print(f"  精确匹配成功: {bank_id}")
                    bank_ids.add(int(bank_id))
                
                # 模糊匹配
                pattern = f"bank_code:name:*{bank_name}*"
                keys = await redis_client.keys(pattern)
                print(f"  模糊匹配找到 {len(keys)} 个结果")
                for key in keys[:5]:
                    bank_id = await redis_client.get(key)
                    if bank_id:
                        bank_ids.add(int(bank_id))
        
        print(f"\n找到的bank_ids: {list(bank_ids)}")
        
        # 获取银行详细信息
        for bank_id in bank_ids:
            bank_key = f"bank_code:bank:{bank_id}"
            bank_data = await redis_client.hgetall(bank_key)
            print(f"\nBank ID {bank_id} 详细信息:")
            for key, value in bank_data.items():
                print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"❌ 调试过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await redis_client.close()

if __name__ == "__main__":
    asyncio.run(debug_redis_search())