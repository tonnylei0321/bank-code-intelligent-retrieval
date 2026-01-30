#!/usr/bin/env python3
"""
测试LLM API连接

验证阿里通义千问和DeepSeek API是否可以正常访问
"""

import asyncio
import aiohttp
import json
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


async def test_qwen_api():
    """测试阿里通义千问API"""
    print("🧪 测试阿里通义千问API...")
    
    headers = {
        "Authorization": "Bearer sk-03f639acddb8425abd3c1b9722ec1014",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "qwen-turbo",
        "input": {
            "messages": [
                {"role": "user", "content": "你好，请回复'API连接正常'"}
            ]
        },
        "parameters": {
            "temperature": 0.7,
            "max_tokens": 100
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers=headers,
                json=data,
                timeout=30
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    reply = result.get("output", {}).get("text", "")
                    print(f"✅ 阿里通义千问: {reply}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ 阿里通义千问失败 ({response.status}): {error_text}")
                    return False
    except Exception as e:
        print(f"❌ 阿里通义千问连接错误: {e}")
        return False


async def test_deepseek_api():
    """测试DeepSeek API"""
    print("🧪 测试DeepSeek API...")
    
    headers = {
        "Authorization": "Bearer sk-9b923042a7714c9cb68ff338ab68d36d",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "你好，请回复'API连接正常'"}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    reply = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    print(f"✅ DeepSeek: {reply}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ DeepSeek失败 ({response.status}): {error_text}")
                    return False
    except Exception as e:
        print(f"❌ DeepSeek连接错误: {e}")
        return False


async def test_sample_generation():
    """测试样本生成"""
    print("\n🧪 测试样本生成...")
    
    bank_name = "中国工商银行股份有限公司北京市分行"
    bank_code = "102100099996"
    
    prompt = f"""你是一个银行业务专家。请为以下银行生成7种不同的自然语言查询方式。

银行信息：
- 完整名称：{bank_name}
- 联行号：{bank_code}

要求：
1. 生成7种用户可能的问法
2. 包括：完整名称、简称、口语化表达、地区+银行名、不完整描述等
3. 模拟真实用户的查询习惯（简短、自然、口语化）

请直接返回JSON格式：
{{
    "questions": [
        "问法1",
        "问法2", 
        "问法3",
        "问法4",
        "问法5",
        "问法6",
        "问法7"
    ]
}}"""

    # 使用DeepSeek测试
    headers = {
        "Authorization": "Bearer sk-9b923042a7714c9cb68ff338ab68d36d",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个专业的银行业务助手。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    reply = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # 尝试解析JSON
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', reply)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group())
                            questions = parsed.get("questions", [])
                            print(f"✅ 成功生成 {len(questions)} 个样本:")
                            for i, q in enumerate(questions, 1):
                                print(f"   {i}. {q}")
                            return True
                        except json.JSONDecodeError:
                            print(f"❌ JSON解析失败: {reply[:200]}...")
                            return False
                    else:
                        print(f"❌ 未找到JSON格式: {reply[:200]}...")
                        return False
                else:
                    error_text = await response.text()
                    print(f"❌ 样本生成失败 ({response.status}): {error_text}")
                    return False
    except Exception as e:
        print(f"❌ 样本生成错误: {e}")
        return False


async def main():
    """主函数"""
    print("🔍 LLM API连接测试")
    print("=" * 50)
    
    # 测试所有API
    results = []
    results.append(await test_qwen_api())
    results.append(await test_deepseek_api())
    
    # 测试样本生成
    generation_result = await test_sample_generation()
    
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print(f"阿里通义千问: {'✅ 正常' if results[0] else '❌ 失败'}")
    print(f"DeepSeek: {'✅ 正常' if results[1] else '❌ 失败'}")
    print(f"样本生成: {'✅ 正常' if generation_result else '❌ 失败'}")
    
    success_count = sum(results)
    print(f"\n可用API数量: {success_count}/2")
    
    if success_count >= 2:
        print("✅ 系统可以正常运行")
    elif success_count >= 1:
        print("⚠️  部分API不可用，但系统仍可运行")
    else:
        print("❌ 所有API都不可用，请检查配置")
    
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())