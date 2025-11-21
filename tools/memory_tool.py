"""
Memory Tool - 用于获取用户的知识水平信息
"""
import json
from typing import List, Dict, Any


class MemoryTool:
    """管理和检索用户知识水平的工具"""
    
    def __init__(self, memory_file: str = "memory.json"):
        self.memory_file = memory_file
        self.memory_data = self._load_memory()
    
    def _load_memory(self) -> Dict[str, Any]:
        """加载记忆数据"""
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"警告: 找不到文件 {self.memory_file}")
            return {}
        except json.JSONDecodeError:
            print(f"警告: {self.memory_file} 不是有效的JSON文件")
            return {}
    
    def get_knowledge_level(self, subjects: List[str]) -> Dict[str, Any]:
        """
        获取指定学科的知识水平信息
        
        Args:
            subjects: 学科列表，如 ["calculus", "astronomy"]
        
        Returns:
            包含学科知识水平信息的字典
        """
        result = {
            "user_id": self.memory_data.get("user_id", "unknown"),
            "subjects_info": {}
        }
        
        knowledge_levels = self.memory_data.get("knowledge_levels", {})
        
        for subject in subjects:
            if subject in knowledge_levels:
                result["subjects_info"][subject] = {
                    "level": knowledge_levels[subject].get("level", "unknown"),
                    "detailed_description": knowledge_levels[subject].get("detailed_description", "")
                }
            else:
                result["subjects_info"][subject] = {
                    "level": "unknown",
                    "detailed_description": f"未找到关于 {subject} 的知识水平信息"
                }
        
        return result
    
    def get_all_subjects(self) -> List[str]:
        """获取所有可用的学科列表"""
        knowledge_levels = self.memory_data.get("knowledge_levels", {})
        return list(knowledge_levels.keys())
