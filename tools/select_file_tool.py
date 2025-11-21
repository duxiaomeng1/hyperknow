"""
文件选择工具：根据用户需求从 metadata.json 中选择相关文件
"""
import json
import os


class SelectFileTool:
    """文件选择工具类"""
    
    def __init__(self, metadata_path: str = "metadata.json"):
        """
        初始化文件选择工具
        
        Args:
            metadata_path: metadata.json 文件的路径
        """
        self.metadata_path = metadata_path
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> dict:
        """加载 metadata.json 文件"""
        try:
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"错误: 找不到文件 {self.metadata_path}")
            return {"files": []}
        except json.JSONDecodeError:
            print(f"错误: {self.metadata_path} 不是有效的 JSON 文件")
            return {"files": []}
    
    def select_files_by_titles(self, titles: list[str]) -> dict:
        """
        根据文件标题列表选择文件
        
        Args:
            titles: 文件标题列表（例如：["301F09.Ch16.Sun.Slides.pdf"]）
        
        Returns:
            包含选中文件信息的字典，格式：
            {
                "selected_files": [
                    {
                        "title": "文件标题",
                        "file_path": "本地文件路径",
                        "file_uri": "Gemini API URI",
                        "content_summary": "内容摘要",
                        "topics": ["主题列表"]
                    },
                    ...
                ],
                "not_found": ["未找到的标题列表"]
            }
        """
        selected_files = []
        not_found = []
        
        # 创建标题到文件的映射（不区分大小写）
        title_map = {
            file_info["title"].lower(): file_info 
            for file_info in self.metadata.get("files", [])
        }
        
        for title in titles:
            title_lower = title.lower()
            if title_lower in title_map:
                file_info = title_map[title_lower]
                selected_files.append({
                    "title": file_info["title"],
                    "file_path": file_info["file_path"],
                    "file_uri": file_info["file_uri"],
                    "content_summary": file_info.get("content_summary", ""),
                    "topics": file_info.get("topics", [])
                })
            else:
                not_found.append(title)
        
        return {
            "selected_files": selected_files,
            "not_found": not_found,
            "total_selected": len(selected_files)
        }
    
    def get_all_file_titles(self) -> list[str]:
        """
        获取所有可用的文件标题列表
        
        Returns:
            文件标题列表
        """
        return [file_info["title"] for file_info in self.metadata.get("files", [])]
    
    def get_files_by_topic(self, topics: list[str]) -> dict:
        """
        根据主题选择文件
        
        Args:
            topics: 主题列表（例如：["astronomy", "physics"]）
        
        Returns:
            包含匹配文件信息的字典
        """
        matched_files = []
        
        for file_info in self.metadata.get("files", []):
            file_topics = file_info.get("topics", [])
            # 如果文件的主题与任一查询主题匹配
            if any(topic.lower() in [t.lower() for t in file_topics] for topic in topics):
                matched_files.append({
                    "title": file_info["title"],
                    "file_path": file_info["file_path"],
                    "file_uri": file_info["file_uri"],
                    "content_summary": file_info.get("content_summary", ""),
                    "topics": file_topics
                })
        
        return {
            "matched_files": matched_files,
            "total_matched": len(matched_files)
        }


# 测试代码
if __name__ == "__main__":
    tool = SelectFileTool()
    
    # 测试获取所有标题
    print("所有可用文件:")
    for title in tool.get_all_file_titles():
        print(f"  - {title}")
    
    # 测试按标题选择
    print("\n按标题选择文件:")
    result = tool.select_files_by_titles(["301F09.Ch16.Sun.Slides.pdf", "不存在的文件.pdf"])
    print(f"找到 {result['total_selected']} 个文件")
    for file in result["selected_files"]:
        print(f"  - {file['title']}")
        print(f"    路径: {file['file_path']}")
    if result["not_found"]:
        print(f"未找到: {result['not_found']}")
    
    # 测试按主题选择
    print("\n按主题选择文件:")
    result = tool.get_files_by_topic(["astronomy"])
    print(f"找到 {result['total_matched']} 个天文学相关文件")
    for file in result["matched_files"]:
        print(f"  - {file['title']}")
