#!/usr/bin/env python3
"""
测试修复后的样本生成功能
"""
import requests
import json
import time

# 配置
BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin123"

def get_auth_token():
    """获取认证token"""
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        data={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"登录失败: {response.text}")
        return None

def test_teacher_model_direct():
    """直接测试TeacherModelAPI"""
    print("🔧 测试TeacherModelAPI直接调用...")
    
    try:
        import sys
        sys.path.append('mvp')
        
        from app.core.database import SessionLocal
        from app.models.bank_code import BankCode
        from app.services.teacher_model import TeacherModelAPI
        
        db = SessionLocal()
        
        # 获取一个银行记录
        bank_record = db.query(BankCode).filter(BankCode.is_valid == 1).first()
        if not bank_record:
            print("❌ 没有找到有效的银行记录")
            return False
        
        print(f"📋 测试银行: {bank_record.bank_name}")
        print(f"📋 联行号: {bank_record.bank_code}")
        
        # 创建TeacherModelAPI实例
        teacher_api = TeacherModelAPI()
        
        # 测试生成问答对
        for question_type in ["exact", "fuzzy", "reverse", "natural"]:
            print(f"\n🔍 测试问题类型: {question_type}")
            
            result = teacher_api.generate_qa_pair(bank_record, question_type)
            
            if result:
                question, answer = result
                print(f"✅ 生成成功:")
                print(f"   问题: {question}")
                print(f"   答案: {answer[:100]}...")
            else:
                print(f"❌ 生成失败")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_qa_generator():
    """测试QAGenerator"""
    print("\n🔧 测试QAGenerator...")
    
    try:
        import sys
        sys.path.append('mvp')
        
        from app.core.database import SessionLocal
        from app.models.dataset import Dataset
        from app.services.qa_generator import QAGenerator
        
        db = SessionLocal()
        
        # 获取第一个数据集
        dataset = db.query(Dataset).first()
        if not dataset:
            print("❌ 没有找到数据集")
            return False
        
        print(f"📋 测试数据集: {dataset.filename} (ID: {dataset.id})")
        
        # 创建QAGenerator实例
        generator = QAGenerator(db)
        
        # 生成少量样本进行测试
        print("🚀 开始生成样本...")
        
        def progress_callback(current, total, record_id):
            print(f"   进度: {current}/{total} (记录ID: {record_id})")
        
        results = generator.generate_for_dataset(
            dataset_id=dataset.id,
            question_types=["exact", "natural"],  # 只测试两种类型
            progress_callback=progress_callback,
            max_records=3  # 只处理3条记录
        )
        
        print(f"\n✅ 生成完成:")
        print(f"   总尝试: {results['total_attempts']}")
        print(f"   成功: {results['successful']}")
        print(f"   失败: {results['failed']}")
        print(f"   创建问答对: {results['qa_pairs_created']}")
        
        if results['failed_records']:
            print(f"   失败记录: {len(results['failed_records'])}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sample_generation_api(token):
    """测试样本生成API"""
    print("\n🔧 测试样本生成API...")
    
    try:
        # 获取数据集列表
        response = requests.get(f"{BASE_URL}/api/v1/datasets", {
            "headers": {"Authorization": f"Bearer {token}"}
        })
        
        if response.status_code != 200:
            print(f"❌ 获取数据集失败: {response.text}")
            return False
        
        datasets = response.json()
        if not datasets:
            print("❌ 没有数据集")
            return False
        
        dataset_id = datasets[0]["id"]
        print(f"📋 使用数据集: {datasets[0]['filename']} (ID: {dataset_id})")
        
        # 启动样本生成任务
        request_data = {
            "dataset_id": dataset_id,
            "selection_strategy": "all",
            "selection_filters": {},
            "record_count_strategy": "custom",
            "custom_count": 2,  # 只处理2条记录
            "llm_strategies": ["natural_language"],
            "questions_per_record": 2,
            "model_type": "local",
            "task_name": "测试任务",
            "description": "API测试"
        }
        
        print("🚀 启动样本生成任务...")
        response = requests.post(
            f"{BASE_URL}/api/sample-generation/start",
            json=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
        )
        
        if response.status_code != 200:
            print(f"❌ 启动任务失败: {response.text}")
            return False
        
        result = response.json()
        task_id = result["task_id"]
        print(f"✅ 任务已启动: {task_id}")
        
        # 监控任务状态
        print("📊 监控任务进度...")
        for i in range(30):  # 最多等待30秒
            response = requests.get(
                f"{BASE_URL}/api/sample-generation/status/{task_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                status_data = response.json()
                print(f"   状态: {status_data['status']}, 进度: {status_data['progress']:.1f}%")
                
                if status_data["status"] in ["completed", "failed"]:
                    print(f"✅ 任务完成: {status_data['status']}")
                    print(f"   生成样本: {status_data['generated_samples']}")
                    print(f"   错误数量: {status_data['error_count']}")
                    return status_data["status"] == "completed"
            
            time.sleep(1)
        
        print("⏰ 任务超时")
        return False
        
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return False

def main():
    print("🔍 测试修复后的样本生成功能")
    print("=" * 50)
    
    # 1. 测试TeacherModelAPI直接调用
    success1 = test_teacher_model_direct()
    
    # 2. 测试QAGenerator
    success2 = test_qa_generator()
    
    # 3. 获取认证token并测试API
    print("\n3. 获取认证token...")
    token = get_auth_token()
    if not token:
        print("❌ 无法获取认证token")
        return
    
    success3 = test_sample_generation_api(token)
    
    print("\n" + "=" * 50)
    print("🎉 测试结果汇总:")
    print(f"   TeacherModelAPI: {'✅ 通过' if success1 else '❌ 失败'}")
    print(f"   QAGenerator: {'✅ 通过' if success2 else '❌ 失败'}")
    print(f"   样本生成API: {'✅ 通过' if success3 else '❌ 失败'}")
    
    if success1 and success2 and success3:
        print("\n🎉 所有测试通过！样本生成功能已修复")
    else:
        print("\n⚠️  部分测试失败，需要进一步检查")

if __name__ == "__main__":
    main()