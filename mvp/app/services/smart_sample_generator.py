"""
智能训练样本生成器

使用 LLM 为银行数据生成多样化的自然语言训练样本
"""
import json
import re
from typing import List, Dict, Optional
from loguru import logger
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


class SmartSampleGenerator:
    """
    智能训练样本生成器
    
    使用大模型（如 Qwen2.5-7B）为每个银行生成多样化的自然语言问法，
    提高训练数据的丰富度和小模型的准确率。
    """
    
    def __init__(self, llm_model: str = "Qwen/Qwen2.5-1.5B-Instruct"):
        """
        初始化生成器
        
        Args:
            llm_model: 用于生成样本的大模型名称
        """
        self.llm_model = llm_model
        self.model = None
        self.tokenizer = None
        self.device = self._get_device()
        logger.info(f"SmartSampleGenerator initialized - Model: {llm_model}, Device: {self.device}")
    
    def _get_prompt_template(self, llm_name: str = "qwen") -> str:
        """
        获取LLM提示词模板
        
        Args:
            llm_name: LLM名称
            
        Returns:
            提示词模板字符串
        """
        try:
            from app.core.database import SessionLocal
            from app.models.llm_prompt import LLMPrompt
            
            db = SessionLocal()
            try:
                prompt_config = db.query(LLMPrompt).filter(
                    LLMPrompt.llm_name == llm_name,
                    LLMPrompt.is_active == True
                ).first()
                
                if prompt_config:
                    return prompt_config.prompt_template
                else:
                    logger.warning(f"未找到LLM '{llm_name}' 的提示词配置，使用默认提示词")
                    return self._get_default_prompt_template()
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取提示词模板失败: {e}")
            return self._get_default_prompt_template()
    
    def _get_default_prompt_template(self) -> str:
        """获取默认提示词模板"""
        return """你是一个银行业务专家。请为以下银行生成{num_samples}种不同的自然语言查询方式。

银行信息：
- 完整名称：{bank_name}
- 联行号：{bank_code}

要求：
1. 生成{num_samples}种用户可能的问法
2. 包括：完整名称、简称、口语化表达、地区+银行名、不完整描述等
3. 模拟真实用户的查询习惯（简短、自然、口语化）
4. 每种问法要自然、简洁，不要太长

请直接返回JSON格式（不要有其他文字）：
{{
    "questions": [
        "问法1",
        "问法2",
        "问法3",
        ...
    ]
}}

示例：
对于"中国工商银行股份有限公司北京市分行"，可能的问法包括：
- "工商银行北京分行"
- "北京工行"
- "ICBC北京"
- "工行北京市分行联行号"
- "北京的工商银行"
等等。"""
    
    def _get_device(self) -> str:
        """检测可用设备"""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    def load_model(self):
        """加载 LLM 模型"""
        if self.model is not None:
            logger.info("Model already loaded")
            return
        
        try:
            logger.info(f"Loading LLM model: {self.llm_model}")
            
            # 加载 tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.llm_model,
                trust_remote_code=True
            )
            
            # 加载模型
            if self.device == "cuda":
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.llm_model,
                    torch_dtype=torch.float16,
                    device_map="auto",
                    trust_remote_code=True
                )
            elif self.device == "mps":
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.llm_model,
                    torch_dtype=torch.float32,
                    trust_remote_code=True
                )
                self.model = self.model.to("mps")
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.llm_model,
                    torch_dtype=torch.float32,
                    trust_remote_code=True
                )
            
            self.model.eval()
            logger.info("LLM model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load LLM model: {e}")
            logger.warning("Will use rule-based generation as fallback")
    
    def generate_samples_for_bank(
        self, 
        bank_name: str, 
        bank_code: str,
        num_samples: int = 7,
        llm_name: str = "qwen"
    ) -> List[Dict]:
        """
        为单个银行生成多样化训练样本
        
        Args:
            bank_name: 银行完整名称
            bank_code: 联行号
            num_samples: 生成样本数量（默认7个）
        
        Returns:
            训练样本列表
        """
        # 如果模型未加载，使用规则生成
        if self.model is None:
            return self.generate_samples_rule_based(bank_name, bank_code, num_samples)
        
        try:
            # 使用 LLM 生成
            samples = self._generate_with_llm(bank_name, bank_code, num_samples, llm_name)
            
            # 如果 LLM 生成失败，回退到规则生成
            if not samples or len(samples) < 3:
                logger.warning(f"LLM generation insufficient, using rule-based for {bank_name}")
                return self.generate_samples_rule_based(bank_name, bank_code, num_samples)
            
            return samples
            
        except Exception as e:
            logger.error(f"Error generating samples with LLM: {e}")
            return self.generate_samples_rule_based(bank_name, bank_code, num_samples)
    
    def _generate_with_llm(
        self, 
        bank_name: str, 
        bank_code: str,
        num_samples: int,
        llm_name: str = "qwen"
    ) -> List[Dict]:
        """使用 LLM 生成样本"""
        
        # 获取自定义提示词模板
        prompt_template = self._get_prompt_template(llm_name)
        
        # 格式化提示词
        prompt = prompt_template.format(
            bank_name=bank_name,
            bank_code=bank_code,
            num_samples=num_samples
        )

        # 构建消息
        messages = [
            {"role": "system", "content": "你是一个专业的银行业务助手，擅长理解用户的各种查询方式。"},
            {"role": "user", "content": prompt}
        ]
        
        # 使用 tokenizer 的 chat template
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Tokenize
        inputs = self.tokenizer([text], return_tensors="pt").to(self.device)
        
        # 生成
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.7,
                top_p=0.8,
                do_sample=True
            )
        
        # 解码
        response = self.tokenizer.decode(
            outputs[0][len(inputs.input_ids[0]):],
            skip_special_tokens=True
        )
        
        # 解析 JSON
        try:
            # 提取 JSON 部分
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                questions = result.get("questions", [])
                
                # 构建训练样本
                samples = []
                for question in questions[:num_samples]:
                    if question and len(question.strip()) > 0:
                        samples.append({
                            "question": question.strip(),
                            "answer": f"{bank_name}: {bank_code}",
                            "bank_name": bank_name,
                            "bank_code": bank_code
                        })
                
                logger.info(f"Generated {len(samples)} samples for {bank_name[:30]}...")
                return samples
            else:
                logger.warning(f"No JSON found in LLM response for {bank_name}")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Response was: {response[:200]}")
            return []
    
    def generate_samples_rule_based(
        self, 
        bank_name: str, 
        bank_code: str,
        num_samples: int = 7
    ) -> List[Dict]:
        """
        基于规则的样本生成（备用方案）
        
        当 LLM 不可用或生成失败时使用
        """
        samples = []
        
        # 1. 完整名称
        samples.append({
            "question": bank_name,
            "answer": f"{bank_name}: {bank_code}",
            "bank_name": bank_name,
            "bank_code": bank_code
        })
        
        # 2. 提取简称
        short_name = self._extract_short_name(bank_name)
        if short_name != bank_name:
            samples.append({
                "question": short_name,
                "answer": f"{bank_name}: {bank_code}",
                "bank_name": bank_name,
                "bank_code": bank_code
            })
        
        # 3. 提取地区和银行主体
        location, main_bank = self._extract_location_and_bank(bank_name)
        
        if location and main_bank:
            # "地区+银行"
            samples.append({
                "question": f"{location}{main_bank}",
                "answer": f"{bank_name}: {bank_code}",
                "bank_name": bank_name,
                "bank_code": bank_code
            })
            
            # "银行+地区"
            samples.append({
                "question": f"{main_bank}{location}",
                "answer": f"{bank_name}: {bank_code}",
                "bank_name": bank_name,
                "bank_code": bank_code
            })
        
        # 4. 添加"的联行号"
        samples.append({
            "question": f"{bank_name}的联行号",
            "answer": f"{bank_name}: {bank_code}",
            "bank_name": bank_name,
            "bank_code": bank_code
        })
        
        # 5. 添加"联行号是多少"
        if short_name != bank_name:
            samples.append({
                "question": f"{short_name}联行号是多少",
                "answer": f"{bank_name}: {bank_code}",
                "bank_name": bank_name,
                "bank_code": bank_code
            })
        
        # 6. 简短查询
        if location and main_bank:
            # 提取银行简称（如"工行"）
            ultra_short = self._get_ultra_short_name(main_bank)
            if ultra_short:
                samples.append({
                    "question": f"{location}{ultra_short}",
                    "answer": f"{bank_name}: {bank_code}",
                    "bank_name": bank_name,
                    "bank_code": bank_code
                })
        
        logger.info(f"Generated {len(samples)} rule-based samples for {bank_name[:30]}...")
        return samples[:num_samples]
    
    def _extract_short_name(self, bank_name: str) -> str:
        """提取银行简称"""
        # 移除常见后缀
        short = bank_name
        for suffix in ["股份有限公司", "有限责任公司", "有限公司", "股份公司"]:
            short = short.replace(suffix, "")
        return short.strip()
    
    def _extract_location_and_bank(self, bank_name: str) -> tuple:
        """提取地区和银行主体"""
        # 常见地区关键词
        location_keywords = [
            "北京", "上海", "天津", "重庆",
            "省", "市", "区", "县", "自治区"
        ]
        
        # 查找地区
        location = None
        for keyword in location_keywords:
            if keyword in bank_name:
                # 提取地区部分
                idx = bank_name.find(keyword)
                # 向前查找地区名称
                start = max(0, idx - 10)
                location_part = bank_name[start:idx + len(keyword)]
                
                # 清理地区名称
                for prefix in ["中国", "股份有限公司", "有限公司"]:
                    location_part = location_part.replace(prefix, "")
                
                location = location_part.strip()
                break
        
        # 提取银行主体
        main_bank = bank_name
        for keyword in ["中国", "股份有限公司", "有限公司", "支行", "分行"]:
            main_bank = main_bank.replace(keyword, "")
        
        # 移除地区部分
        if location:
            main_bank = main_bank.replace(location, "")
        
        main_bank = main_bank.strip()
        
        return location, main_bank
    
    def _get_ultra_short_name(self, bank_name: str) -> Optional[str]:
        """获取超短银行名称（如"工行"）"""
        mapping = {
            "工商银行": "工行",
            "建设银行": "建行",
            "农业银行": "农行",
            "中国银行": "中行",
            "交通银行": "交行",
            "邮政储蓄银行": "邮储",
            "招商银行": "招行",
            "浦发银行": "浦发",
            "民生银行": "民生",
            "兴业银行": "兴业",
            "光大银行": "光大",
            "华夏银行": "华夏",
            "广发银行": "广发",
            "平安银行": "平安"
        }
        
        for full, short in mapping.items():
            if full in bank_name:
                return short
        
        return None
    
    def batch_generate(
        self, 
        bank_records: List[Dict],
        samples_per_bank: int = 7,
        batch_size: int = 100
    ) -> List[Dict]:
        """
        批量生成训练样本
        
        Args:
            bank_records: 银行记录列表 [{"name": "...", "code": "..."}, ...]
            samples_per_bank: 每个银行生成的样本数
            batch_size: 批处理大小（避免内存溢出）
        
        Returns:
            所有训练样本
        """
        all_samples = []
        total = len(bank_records)
        
        logger.info(f"Starting batch generation for {total} banks, {samples_per_bank} samples each")
        
        for i in range(0, total, batch_size):
            batch = bank_records[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} banks)")
            
            for j, record in enumerate(batch):
                try:
                    samples = self.generate_samples_for_bank(
                        record["name"],
                        record["code"],
                        samples_per_bank
                    )
                    all_samples.extend(samples)
                    
                    if (i + j + 1) % 100 == 0:
                        logger.info(f"Progress: {i+j+1}/{total} banks processed")
                        
                except Exception as e:
                    logger.error(f"Failed to generate samples for {record['name']}: {e}")
                    continue
        
        logger.info(f"Batch generation complete - Total samples: {len(all_samples)}")
        return all_samples
    
    def unload_model(self):
        """卸载模型释放内存"""
        if self.model is not None:
            logger.info("Unloading LLM model")
            del self.model
            del self.tokenizer
            self.model = None
            self.tokenizer = None
            
            # 清理缓存
            import gc
            gc.collect()
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
            elif torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info("LLM model unloaded")
