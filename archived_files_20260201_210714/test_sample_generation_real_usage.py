#!/usr/bin/env python3
"""
真实使用场景下的样本生成测试

模拟用户通过前端使用样本生成功能的完整流程
"""
import sys
import os

# 切换到mvp目录
current_dir = os.path.dirname(os.path.abspath(__file__))
mvp_dir = os.path.join(current_dir, 'mvp')
os.chdir(mvp_dir)
sys.path.insert(0, mvp_dir)

from app.main import app
from fastapi.testclient import TestClient
import json

def main():
    """主测试函数"""
    print("🚀 开始真实使用场景测试")
    print("=" * 60)
    
    client = TestClient(app)
    
    # 1. 登录
    print("\n1️⃣ 用户登录...")
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "admin",
            "password": "admin123"
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ 登录失败: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ 登录成功")
    
    # 2. 获取数据集列表
    print("\n2️⃣ 获取数据集列表...")
    datasets_response = client.get("/api/v1/datasets/", headers=headers)
    
    if datasets_response.status_code != 200:
        print(f"❌ 获取数据集失败: {datasets_response.text}")
        return
    
    datasets = datasets_response.json()
    if not datasets:
        print("❌ 没有可用的数据集")
        return
    
    dataset = datasets[0]
    dataset_id = dataset["id"]
    dataset_name = dataset.get("filename", "未命名数据集")
    print(f"✅ 找到数据集: {dataset_name} (ID: {dataset_id})")
    
    # 3. 生成样本（LLM方式）
    print("\n3️⃣ 使用LLM生成样本...")
    generation_data = {
        "dataset_id": dataset_id,
        "generation_type": "llm",
        "question_types": ["exact", "fuzzy"],
        "sample_count": 3
    }
    
    # 检查样本生成API端点
    print("   检查API端点...")
    
    # 尝试通过qa_pairs API生成
    qa_generation_response = client.post(
        "/api/v1/qa-pairs/generate",
        json=generation_data,
        headers=headers
    )
    
    print(f"   API响应状态: {qa_generation_response.status_code}")
    
    if qa_generation_response.status_code == 200:
        result = qa_generation_response.json()
        print(f"✅ 样本生成成功！")
        print(f"   生成数量: {result.get('generated_count', 0)}")
        print(f"   成功数量: {result.get('success_count', 0)}")
        print(f"   失败数量: {result.get('failed_count', 0)}")
        
        # 4. 查看生成的样本
        print("\n4️⃣ 查看生成的样本...")
        qa_pairs_response = client.get(
            f"/api/v1/qa-pairs/?dataset_id={dataset_id}&limit=5",
            headers=headers
        )
        
        if qa_pairs_response.status_code == 200:
            qa_pairs = qa_pairs_response.json()
            print(f"✅ 获取到 {len(qa_pairs)} 个样本")
            
            if qa_pairs:
                print("\n📝 样本示例:")
                for i, qa in enumerate(qa_pairs[:3], 1):
                    print(f"\n   样本 {i}:")
                    print(f"   问题: {qa['question']}")
                    print(f"   答案: {qa['answer'][:100]}...")
                    print(f"   类型: {qa.get('question_type', 'N/A')}")
        else:
            print(f"❌ 获取样本失败: {qa_pairs_response.text}")
    else:
        print(f"⚠️  样本生成API返回: {qa_generation_response.status_code}")
        print(f"   响应: {qa_generation_response.text}")
        
        # 尝试直接使用QAGenerator服务
        print("\n   尝试直接使用QAGenerator服务...")
        from app.services.qa_generator import QAGenerator
        from app.core.database import SessionLocal
        from app.models.bank_code import BankCode
        
        db = SessionLocal()
        try:
            # 获取一些银行记录
            bank_records = db.query(BankCode).limit(3).all()
            
            if bank_records:
                print(f"   找到 {len(bank_records)} 条银行记录")
                
                generator = QAGenerator()
                
                for record in bank_records:
                    print(f"\n   处理: {record.bank_name}")
                    
                    # 生成exact类型问答对
                    qa_pair = generator.generate_qa_pair(
                        record=record,
                        question_type="exact",
                        dataset_id=dataset_id
                    )
                    
                    if qa_pair:
                        print(f"   ✅ 生成成功")
                        print(f"      问题: {qa_pair.question}")
                        print(f"      答案: {qa_pair.answer[:80]}...")
                    else:
                        print(f"   ❌ 生成失败")
            else:
                print("   ❌ 没有找到银行记录")
        finally:
            db.close()
    
    print("\n" + "=" * 60)
    print("🎉 测试完成！")

if __name__ == "__main__":
    main()
