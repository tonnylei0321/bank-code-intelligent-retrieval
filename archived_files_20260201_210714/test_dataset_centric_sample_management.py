#!/usr/bin/env python3
"""
测试数据集中心化样本管理功能

本脚本测试：
1. 数据集中心化的样本管理界面
2. 单个样本删除功能
3. 批量样本删除功能
4. 数据集选择和切换功能
"""

import requests
import json
import time
from typing import Dict, Any, List

# 配置
BASE_URL = "http://localhost:8000"
TEST_USERNAME = "admin"
TEST_PASSWORD = "admin123"

class SampleManagementTester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.test_dataset_id = None
        self.test_qa_pairs = []
    
    def login(self) -> bool:
        """登录获取访问令牌"""
        try:
            response = self.session.post(
                f"{BASE_URL}/api/v1/auth/login",
                data={
                    "username": TEST_USERNAME,
                    "password": TEST_PASSWORD
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}"
                })
                print("✅ 登录成功")
                return True
            else:
                print(f"❌ 登录失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 登录异常: {e}")
            return False
    
    def get_datasets(self) -> List[Dict[str, Any]]:
        """获取数据集列表"""
        try:
            response = self.session.get(f"{BASE_URL}/api/v1/datasets")
            
            if response.status_code == 200:
                datasets = response.json()
                print(f"✅ 获取到 {len(datasets)} 个数据集")
                return datasets
            else:
                print(f"❌ 获取数据集失败: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ 获取数据集异常: {e}")
            return []
    
    def get_qa_pairs_for_dataset(self, dataset_id: int) -> List[Dict[str, Any]]:
        """获取指定数据集的问答对"""
        try:
            response = self.session.get(f"{BASE_URL}/api/v1/qa-pairs/{dataset_id}")
            
            if response.status_code == 200:
                qa_pairs = response.json()
                print(f"✅ 数据集 {dataset_id} 有 {len(qa_pairs)} 个问答对")
                return qa_pairs
            else:
                print(f"❌ 获取问答对失败: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ 获取问答对异常: {e}")
            return []
    
    def delete_single_qa_pair(self, qa_pair_id: int) -> bool:
        """删除单个问答对"""
        try:
            response = self.session.delete(f"{BASE_URL}/api/v1/qa-pairs/single/{qa_pair_id}")
            
            if response.status_code == 204:
                print(f"✅ 成功删除问答对 {qa_pair_id}")
                return True
            else:
                print(f"❌ 删除问答对失败: {response.status_code}")
                if response.content:
                    print(f"   错误详情: {response.json()}")
                return False
        except Exception as e:
            print(f"❌ 删除问答对异常: {e}")
            return False
    
    def delete_all_qa_pairs_for_dataset(self, dataset_id: int) -> bool:
        """删除数据集的所有问答对"""
        try:
            response = self.session.delete(f"{BASE_URL}/api/v1/qa-pairs/{dataset_id}")
            
            if response.status_code == 204:
                print(f"✅ 成功删除数据集 {dataset_id} 的所有问答对")
                return True
            else:
                print(f"❌ 删除数据集问答对失败: {response.status_code}")
                if response.content:
                    print(f"   错误详情: {response.json()}")
                return False
        except Exception as e:
            print(f"❌ 删除数据集问答对异常: {e}")
            return False
    
    def test_dataset_centric_workflow(self):
        """测试数据集中心化工作流程"""
        print("\n🧪 测试数据集中心化样本管理工作流程")
        
        # 1. 获取数据集列表
        datasets = self.get_datasets()
        if not datasets:
            print("❌ 没有可用的数据集，跳过测试")
            return
        
        # 选择第一个数据集进行测试
        test_dataset = datasets[0]
        self.test_dataset_id = test_dataset["id"]
        print(f"📊 选择测试数据集: {test_dataset['filename']} (ID: {self.test_dataset_id})")
        
        # 2. 获取该数据集的问答对
        qa_pairs = self.get_qa_pairs_for_dataset(self.test_dataset_id)
        if not qa_pairs:
            print("❌ 该数据集没有问答对，跳过删除测试")
            return
        
        self.test_qa_pairs = qa_pairs
        print(f"📝 找到 {len(qa_pairs)} 个问答对")
        
        # 3. 测试单个问答对删除
        if len(qa_pairs) > 0:
            test_qa_id = qa_pairs[0]["id"]
            print(f"\n🗑️ 测试删除单个问答对 (ID: {test_qa_id})")
            
            if self.delete_single_qa_pair(test_qa_id):
                # 验证删除后的数量
                remaining_qa_pairs = self.get_qa_pairs_for_dataset(self.test_dataset_id)
                expected_count = len(qa_pairs) - 1
                if len(remaining_qa_pairs) == expected_count:
                    print(f"✅ 单个删除验证成功: {len(remaining_qa_pairs)} 个剩余")
                else:
                    print(f"❌ 单个删除验证失败: 期望 {expected_count}，实际 {len(remaining_qa_pairs)}")
        
        # 4. 测试批量删除（删除剩余的所有问答对）
        remaining_qa_pairs = self.get_qa_pairs_for_dataset(self.test_dataset_id)
        if len(remaining_qa_pairs) > 1:
            print(f"\n🗑️ 测试批量删除 {min(3, len(remaining_qa_pairs))} 个问答对")
            
            # 删除前3个问答对（模拟批量删除）
            delete_count = 0
            for i in range(min(3, len(remaining_qa_pairs))):
                qa_id = remaining_qa_pairs[i]["id"]
                if self.delete_single_qa_pair(qa_id):
                    delete_count += 1
            
            print(f"✅ 批量删除完成: 成功删除 {delete_count} 个问答对")
            
            # 验证批量删除后的数量
            final_qa_pairs = self.get_qa_pairs_for_dataset(self.test_dataset_id)
            expected_final_count = len(remaining_qa_pairs) - delete_count
            if len(final_qa_pairs) == expected_final_count:
                print(f"✅ 批量删除验证成功: {len(final_qa_pairs)} 个剩余")
            else:
                print(f"❌ 批量删除验证失败: 期望 {expected_final_count}，实际 {len(final_qa_pairs)}")
    
    def test_api_endpoints(self):
        """测试API端点"""
        print("\n🔌 测试API端点")
        
        # 测试获取所有问答对（不指定数据集）
        try:
            response = self.session.get(f"{BASE_URL}/api/v1/qa-pairs")
            if response.status_code == 200:
                all_qa_pairs = response.json()
                print(f"✅ 获取所有问答对成功: {len(all_qa_pairs)} 个")
            else:
                print(f"❌ 获取所有问答对失败: {response.status_code}")
        except Exception as e:
            print(f"❌ 获取所有问答对异常: {e}")
        
        # 测试获取问答对统计信息
        if self.test_dataset_id:
            try:
                response = self.session.get(f"{BASE_URL}/api/v1/qa-pairs/{self.test_dataset_id}/stats")
                if response.status_code == 200:
                    stats = response.json()
                    print(f"✅ 获取统计信息成功: {stats}")
                else:
                    print(f"❌ 获取统计信息失败: {response.status_code}")
            except Exception as e:
                print(f"❌ 获取统计信息异常: {e}")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始测试数据集中心化样本管理功能")
        print("=" * 60)
        
        # 登录
        if not self.login():
            return
        
        # 测试API端点
        self.test_api_endpoints()
        
        # 测试数据集中心化工作流程
        self.test_dataset_centric_workflow()
        
        print("\n" + "=" * 60)
        print("✅ 测试完成")

def main():
    """主函数"""
    tester = SampleManagementTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()