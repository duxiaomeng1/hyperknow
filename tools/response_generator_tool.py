"""
响应生成工具：使用流式多轮对话模型生成详细回答
基于用户请求、知识水平和相关文档生成个性化回答
"""
from google import genai
from google.genai import types
import os
import sys


class ResponseGeneratorTool:
    """响应生成工具类 - 支持流式输出和多轮对话"""
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
        """
        初始化响应生成工具
        
        Args:
            model_name: 使用的模型名称
        """
        self.model_name = model_name
        self.client = self._initialize_client()
        self.chat = None
        self.conversation_history = []
    
    def _initialize_client(self) -> genai.Client:
        """初始化 Gemini 客户端"""
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("请设置 GOOGLE_API_KEY 或 GEMINI_API_KEY 环境变量")
        return genai.Client(api_key=api_key)
    
    def create_chat_session(self):
        """创建新的聊天会话"""
        self.chat = self.client.chats.create(model=self.model_name)
        self.conversation_history = []
        return self.chat
    
    def generate_response_stream(
        self,
        user_query: str,
        knowledge_level_info: dict = None,
        selected_files: list = None,
        file_uris: list = None
    ) -> str:
        """
        生成流式响应
        
        Args:
            user_query: 用户的原始查询
            knowledge_level_info: 用户的知识水平信息
            selected_files: 选中的文件信息列表
            file_uris: 文件的 URI 列表（已弃用，改用本地文件上传）
        
        Returns:
            完整的响应文本
        """
        # 构建上下文信息
        context_parts = []
        
        # 添加用户知识水平信息
        if knowledge_level_info:
            context = self._format_knowledge_level_context(knowledge_level_info)
            context_parts.append(context)
        
        # 构建完整的提示
        prompt = self._build_prompt(user_query, context_parts)
        
        # 发送消息并获取流式响应
        print("\n" + "="*60)
        print("💬 AI 助手的详细回答:")
        print("="*60 + "\n")
        
        full_response = ""
        try:
            # 检查是否有本地文件需要上传
            if selected_files and len(selected_files) > 0:
                # 使用本地文件上传
                content_parts = []
                
                # 上传并添加所有文件
                for file_info in selected_files:
                    file_path = file_info.get("file_path")
                    if file_path and os.path.exists(file_path):
                        print(f"📤 正在上传文件: {file_info.get('title', file_path)}")
                        try:
                            # 上传文件并获取 file 对象
                            # 根据官方文档: client.files.upload(file="path/to/file")
                            uploaded_file = self.client.files.upload(file=file_path)
                            print(f"✓ 文件上传成功: {uploaded_file.name}")
                            
                            # 添加文件到 content_parts
                            content_parts.append(types.Part.from_uri(
                                file_uri=uploaded_file.uri,
                                mime_type="application/pdf"
                            ))
                        except Exception as e:
                            print(f"⚠️ 文件上传失败 ({file_info.get('title', file_path)}): {e}")
                            # 如果上传失败，使用文件摘要作为备选
                            context = self._format_single_file_context(file_info)
                            prompt = context + "\n" + prompt
                    else:
                        # 文件路径无效，使用摘要
                        print(f"⚠️ 文件路径无效，使用摘要: {file_info.get('title', 'unknown')}")
                        context = self._format_single_file_context(file_info)
                        prompt = context + "\n" + prompt
                
                # 添加文本提示
                content_parts.append(types.Part(text=prompt))
                
                # 使用流式生成（如果有成功上传的文件）
                if len(content_parts) > 1:  # 至少有一个文件 + 文本
                    response_stream = self.client.models.generate_content_stream(
                        model=self.model_name,
                        contents=content_parts
                    )
                    
                    for chunk in response_stream:
                        if chunk.text:
                            print(chunk.text, end="", flush=True)
                            full_response += chunk.text
                    print("\n")
                else:
                    # 没有成功上传的文件，使用聊天会话
                    if self.chat is None:
                        self.create_chat_session()
                    
                    response_stream = self.chat.send_message_stream(prompt)
                    for chunk in response_stream:
                        if chunk.text:
                            print(chunk.text, end="", flush=True)
                            full_response += chunk.text
                    print("\n")
            else:
                # 没有文件，使用聊天会话
                if self.chat is None:
                    self.create_chat_session()
                
                response_stream = self.chat.send_message_stream(prompt)
                for chunk in response_stream:
                    if chunk.text:
                        print(chunk.text, end="", flush=True)
                        full_response += chunk.text
                print("\n")
                
        except Exception as e:
            print(f"\n错误: 生成响应时出现问题: {e}")
            full_response = f"抱歉，生成响应时出现错误: {e}"
        
        # 保存到历史记录
        self.conversation_history.append({
            "role": "user",
            "content": prompt
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": full_response
        })
        
        return full_response
    
    def _format_knowledge_level_context(self, knowledge_level_info: dict) -> str:
        """格式化知识水平信息为上下文"""
        context = "\n【用户知识水平背景】\n"
        
        subjects_info = knowledge_level_info.get("subjects_info", {})
        for subject, info in subjects_info.items():
            level = info.get("level", "unknown")
            description = info.get("detailed_description", "")
            context += f"- {subject}: {level} 水平\n"
            if description:
                context += f"  详情: {description}\n"
        
        context += "\n请根据用户的知识水平，用合适的方式解释概念。\n"
        return context
    
    def _format_files_context(self, selected_files: list) -> str:
        """格式化文件信息为上下文"""
        context = "\n【相关参考文档】\n"
        
        for file_info in selected_files:
            title = file_info.get("title", "未知文件")
            summary = file_info.get("content_summary", "")
            topics = file_info.get("topics", [])
            
            context += f"\n文档: {title}\n"
            if topics:
                context += f"主题: {', '.join(topics)}\n"
            if summary:
                context += f"内容摘要: {summary}\n"
        
        context += "\n请基于上述参考文档的内容来回答用户的问题。\n"
        return context
    
    def _format_single_file_context(self, file_info: dict) -> str:
        """格式化单个文件信息为上下文"""
        title = file_info.get("title", "未知文件")
        summary = file_info.get("content_summary", "")
        topics = file_info.get("topics", [])
        
        context = f"\n【参考文档: {title}】\n"
        if topics:
            context += f"主题: {', '.join(topics)}\n"
        if summary:
            context += f"内容摘要: {summary}\n"
        context += "\n"
        return context
    
    def _build_prompt(self, user_query: str, context_parts: list) -> str:
        """构建完整的提示"""
        prompt = ""
        
        # 添加上下文信息
        if context_parts:
            prompt += "".join(context_parts)
            prompt += "\n" + "-"*60 + "\n\n"
        
        # 添加用户查询
        prompt += f"用户问题: {user_query}\n\n"
        prompt += "请提供详细、准确、易懂的回答。"
        
        return prompt
    
    def get_history(self) -> list:
        """获取对话历史"""
        if self.chat:
            try:
                return list(self.chat.get_history())
            except:
                return self.conversation_history
        return self.conversation_history
    
    def print_history(self):
        """打印对话历史"""
        print("\n" + "="*60)
        print("📜 对话历史:")
        print("="*60 + "\n")
        
        history = self.get_history()
        for i, message in enumerate(history, 1):
            role = message.role if hasattr(message, 'role') else message.get('role', 'unknown')
            print(f"[{i}] {role.upper()}:")
            
            if hasattr(message, 'parts'):
                for part in message.parts:
                    if hasattr(part, 'text'):
                        print(f"  {part.text[:200]}...")
            elif 'content' in message:
                print(f"  {message['content'][:200]}...")
            print()
    
    def continue_conversation(self, follow_up_query: str) -> str:
        """
        继续多轮对话
        
        Args:
            follow_up_query: 后续问题
            
        Returns:
            响应文本
        """
        if self.chat is None:
            raise ValueError("没有活动的聊天会话，请先调用 generate_response_stream")
        
        print("\n" + "="*60)
        print("💬 AI 助手的回答:")
        print("="*60 + "\n")
        
        full_response = ""
        try:
            response_stream = self.chat.send_message_stream(follow_up_query)
            for chunk in response_stream:
                if chunk.text:
                    print(chunk.text, end="", flush=True)
                    full_response += chunk.text
            print("\n")
        except Exception as e:
            print(f"\n错误: 生成响应时出现问题: {e}")
            full_response = f"抱歉，生成响应时出现错误: {e}"
        
        return full_response


# 测试代码
if __name__ == "__main__":
    print("测试 ResponseGeneratorTool\n")
    
    try:
        # 创建工具实例
        tool = ResponseGeneratorTool()
        
        # 模拟知识水平信息
        knowledge_level = {
            "subjects_info": {
                "astronomy": {
                    "level": "beginner",
                    "detailed_description": "刚开始学习天文学，了解基本概念"
                }
            }
        }
        
        # 模拟文件信息
        selected_files = [
            {
                "title": "太阳基础知识.pdf",
                "content_summary": "介绍太阳的基本结构、温度和能量来源",
                "topics": ["astronomy", "physics"]
            }
        ]
        
        # 生成响应
        response = tool.generate_response_stream(
            user_query="太阳的内部结构是什么？",
            knowledge_level_info=knowledge_level,
            selected_files=selected_files
        )
        
        print("\n✓ 测试完成！")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
