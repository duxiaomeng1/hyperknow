"""
Gradio 界面：展示 Director Agent 的完整决策过程
包含用户请求、函数调用路径和最终回复
"""
import os
import sys
import json
import gradio as gr
from google import genai
from google.genai import types
from tools.memory_tool import MemoryTool
from tools.select_file_tool import SelectFileTool
from tools.response_generator_tool import ResponseGeneratorTool


# 从 main.py 导入必要的函数定义
def load_metadata(metadata_path: str = "metadata.json") -> dict:
    """加载 metadata.json 文件"""
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"警告: 找不到文件 {metadata_path}，使用空数据")
        return {"files": []}
    except json.JSONDecodeError:
        print(f"警告: {metadata_path} 不是有效的 JSON 文件，使用空数据")
        return {"files": []}


def create_select_files_function(metadata_path: str = "metadata.json") -> dict:
    """动态创建文件选择函数声明"""
    metadata = load_metadata(metadata_path)
    files = metadata.get("files", [])
    
    file_titles = [file_info["title"] for file_info in files]
    
    # 生成文件描述列表（包含完整摘要以便更好地匹配）
    file_descriptions = []
    for file_info in files:
        title = file_info["title"]
        summary = file_info.get("content_summary", "无摘要")
        # 保留完整摘要，让模型能更准确地选择
        file_descriptions.append(f"- **{title}**\n  内容: {summary}")
    
    # 构建描述文本
    description = f"""根据用户的问题和需求，从可用的文档库中**精确选择**最相关的文件。

⚠️ **重要提示**：
- **仔细阅读**每个文件的内容摘要
- **只选择**与用户问题**直接相关**的文件
- **不要**选择所有文件，要根据问题内容**精确匹配**
- 如果问题只涉及某个特定主题（如太阳、望远镜、开普勒定律等），只选择包含该主题的文件

**选择策略**：
1. 仔细分析用户问题中的**关键词**（如：太阳、望远镜、轨道、光谱等）
2. 查看每个文件的**内容摘要**，判断是否包含相关主题
3. **只选择**内容摘要中明确提到相关主题的文件
4. 如果多个文件都相关，可以选择多个，但要确保每个都是必要的

**可用的文件及其详细内容（共 {len(files)} 个）**：

{chr(10).join(file_descriptions)}

**示例**：
- 问题："太阳的内部结构" → 只选择 ["301F09.Ch16.Sun.Slides.pdf"]（因为只有它介绍太阳）
- 问题："望远镜的工作原理" → 只选择 ["301F09.TelescopesCh5.9.16.09.pdf"]（因为只有它介绍望远镜）
- 问题："开普勒定律" → 选择 ["301F09.IntroOrbitsLight.I.pdf", "301F09Scalo.IntOrbLight.II.pdf"]（两个都涉及轨道和开普勒定律）
- 问题："光谱分析" → 只选择 ["301F09.LecturesCh3.5_4.pdf"]（因为它专门讲光谱）

请根据用户的问题内容，**精确选择**最相关的文件，避免选择不必要的文件。
"""
    
    return {
        "name": "select_relevant_files",
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {
                "file_titles": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": file_titles
                    },
                    "description": "需要查询的文件标题列表，从可用文件中选择最相关的一个或多个"
                },
            },
            "required": ["file_titles"],
        },
    }


# 定义函数声明
get_knowledge_level_function = {
    "name": "get_knowledge_level",
    "description": """获取用户在指定学科领域的知识水平信息（包括level和detailed_description）。
    
当用户提到以下任何情况时，必须调用此函数：
- 询问学习了什么内容、知识点、课程内容
- 询问知识水平、掌握程度、学习情况
- 提到具体学科名称（微积分、代数、天文学等）
- 需要根据用户水平提供建议或总结

可用的学科：
- calculus（微积分）：包括导数、积分、极限等
- algebra（代数）：包括方程、函数、表达式等
- astronomy（天文学）：包括天体、星系、轨道力学等
- general_science（通用科学）：物理、化学、生物等基础科学

示例触发场景：
- "请告诉我这学期学了哪些天文学知识" → 调用 get_knowledge_level(["astronomy"])
- "我在微积分方面的水平如何" → 调用 get_knowledge_level(["calculus"])
- "总结一下我的学习情况" → 调用 get_knowledge_level(["calculus", "algebra", "astronomy", "general_science"])
""",
    "parameters": {
        "type": "object",
        "properties": {
            "subjects": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["calculus", "algebra", "astronomy", "general_science"]
                },
                "description": "需要查询的学科列表。可选值：'calculus'（微积分）、'algebra'（代数）、'astronomy'（天文学）、'general_science'（通用科学）"
            },
        },
        "required": ["subjects"],
    },
}

select_relevant_files_function = create_select_files_function()

generate_detailed_response_function = {
    "name": "generate_detailed_response",
    "description": """使用流式多轮对话模型，基于用户的知识水平和相关文档，生成详细、个性化的回答。

当用户提到以下任何情况时，应该调用此函数：
- 需要基于文档内容生成详细解释
- 需要根据用户知识水平定制回答
- 已经获取了知识水平和相关文件，需要整合信息回答
- 用户需要深入、全面的解答

此函数会：
- 结合用户的知识水平调整解释深度
- 基于选中的文档内容提供准确信息
- 以流式方式输出，提供更好的用户体验
- 支持多轮对话，可以追问和深入探讨

调用时机：
- 在获取了 get_knowledge_level 和/或 select_relevant_files 的结果后
- 作为最后一步，整合所有信息生成最终回答
""",
    "parameters": {
        "type": "object",
        "properties": {
            "user_query": {
                "type": "string",
                "description": "用户的原始问题"
            },
            "use_knowledge_level": {
                "type": "boolean",
                "description": "是否使用知识水平信息（如果之前调用了 get_knowledge_level）"
            },
            "use_selected_files": {
                "type": "boolean",
                "description": "是否使用选中的文件信息（如果之前调用了 select_relevant_files）"
            }
        },
        "required": ["user_query"],
    },
}


class GradioDirectorAgent:
    """
    Gradio 界面的 Director Agent
    负责分析用户请求，记录函数调用路径，并生成最终回复
    """
    
    def __init__(self):
        """初始化 Director Agent"""
        # 从环境变量获取 API Key
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("请设置 GOOGLE_API_KEY 或 GEMINI_API_KEY 环境变量")
        
        self.client = genai.Client(api_key=api_key)
        self.memory_tool = MemoryTool()
        self.select_file_tool = SelectFileTool()
        self.response_generator = ResponseGeneratorTool()
        
        # 决策模型的系统指令（已同步 main.py 的多轮对话优化）
        self.system_instruction = """你是一个智能决策助手 (Director Agent)。你的职责是分析用户的请求，并决定需要调用哪些工具来满足用户需求。

**🔵 重要提示：多轮对话能力**
- 你正在参与一个多轮对话会话，**你可以访问完整的对话历史**
- 当用户提及"上次"、"刚才"、"之前"等词时，你应该查看对话历史来回答
- 对于简单的上下文引用问题（如"我刚才问了什么"），你应该**直接回答**，不需要调用任何工具
- 只有当用户需要查询知识水平、文档内容或生成详细解释时，才调用相应的工具

你可以调用以下三个工具：

1. **get_knowledge_level** - 获取用户知识水平
   - 当用户的请求中可以识别出所属的学科，就要先调用此函数，来了解用户在该学科的知识水平
   - 当需要根据用户水平定制回答时调用
   - 可查询学科: calculus(微积分), algebra(代数), astronomy(天文学), general_science(通用科学)

2. **select_relevant_files** - 选择相关文档
   - 当用户需要详细了解天文学时
   - 当需要查阅课程资料或文档时调用
   - 从文档库中选择最相关的文件
   - ⚠️ **重要**: 文档库中包含用户的课程课件，这是最权威的学习资料

3. **generate_detailed_response** - 生成详细回答
   - 在获取了知识水平和/或相关文件后调用
   - 整合所有信息生成个性化的详细回答
   - **必须**作为最后一步调用

**🔴 核心决策流程（必须严格遵守）**：

**规则0：优先处理上下文查询**
- ✅ 如果用户只是询问对话历史（如"我刚才问了什么"、"上个问题是什么"），**直接查看对话历史并回答**
- ✅ 不要为简单的上下文查询调用任何工具
- 示例：
  - "我上次问了什么？" → 查看对话历史，直接回答（不调用工具）
  - "刚才你说了什么？" → 查看对话历史，直接回答（不调用工具）

**规则1：识别学科类型**
- 分析用户问题，识别涉及的学科（calculus、algebra、astronomy、general_science）
- 只要问题涉及任何学科知识，都必须执行规则2

**规则2：必须先获取知识水平**
- ✅ 只要用户请求包含学科相关的知识，**第一步必须调用 get_knowledge_level**
- ✅ 先了解用户的知识等级，才能提供个性化回答

**规则3：天文学必须查阅文档**
- ✅ 如果问题涉及天文学（astronomy），**必须**在获取知识水平后调用 select_relevant_files
- ✅ 选择所有与问题相关的天文学课件文件

**规则4：最后生成回复**
- ✅ **必须**最后调用 generate_detailed_response
- ✅ 整合知识水平和文档信息生成个性化回答

**🎯 具体示例（必须遵循）**：

示例 1: "我刚才问了什么？"
   - 识别：这是上下文查询
   - 执行流程：直接查看对话历史并回答（不调用任何工具）

示例 2: "解释太阳的内部结构"
   - 识别：涉及天文学
   - 执行流程：
     ① get_knowledge_level(["astronomy"])
     ② select_relevant_files(["301F09.Ch16.Sun.Slides.pdf"])
     ③ generate_detailed_response(use_knowledge=True, use_files=True)

示例 3: "我上次问的那个问题能详细解释一下吗？"
   - 识别：引用了上下文 + 需要详细解释
   - 执行流程：
     ① 查看对话历史，确定"上次问的问题"是什么
     ② 根据那个问题，调用相应的工具
     ③ 调用 generate_detailed_response 生成详细解释

**⚠️ 重要提醒**：
- 每次调用函数时，只调用一个函数，等待结果后再决定下一步
- 不要一次性调用多个函数
- 严格按照流程顺序执行
- 天文学问题必须执行完整的流程（三个步骤）
"""
        
        # 配置工具
        self.tools = types.Tool(function_declarations=[
            get_knowledge_level_function,
            select_relevant_files_function,
            generate_detailed_response_function
        ])
        
        self.config = types.GenerateContentConfig(
            tools=[self.tools],
            system_instruction=self.system_instruction
        )
    
    def execute_function(self, function_call, user_query: str, 
                        knowledge_level_result: dict = None, 
                        selected_files_result: dict = None):
        """执行函数调用并返回结果"""
        if function_call.name == "get_knowledge_level":
            subjects = list(function_call.args.get("subjects", []))
            result = self.memory_tool.get_knowledge_level(subjects)
            return result
            
        elif function_call.name == "select_relevant_files":
            file_titles = list(function_call.args.get("file_titles", []))
            result = self.select_file_tool.select_files_by_titles(file_titles)
            return result
            
        elif function_call.name == "generate_detailed_response":
            query = function_call.args.get("user_query", user_query)
            use_knowledge = function_call.args.get("use_knowledge_level", False)
            use_files = function_call.args.get("use_selected_files", False)
            
            knowledge_info = knowledge_level_result if use_knowledge else None
            files_info = selected_files_result.get("selected_files", []) if use_files and selected_files_result else None
            
            # 不再需要 file_uris，直接使用 files_info 中的 file_path
            detailed_response = self.response_generator.generate_response_stream(
                user_query=query,
                knowledge_level_info=knowledge_info,
                selected_files=files_info
            )
            
            result = {
                "response": detailed_response,
                "used_knowledge_level": use_knowledge,
                "used_files": use_files,
                "response_length": len(detailed_response)
            }
            
            return result
        
        return None
    
    def process_query_with_chat(self, user_query: str, chat=None):
        """
        使用聊天会话处理用户查询（支持多轮对话）
        
        Args:
            user_query: 用户的问题
            chat: 聊天会话对象（可选）
            
        Returns:
            str: AI 的回复文本
        """
        if not user_query or not user_query.strip():
            return "⚠️ 请输入有效的问题"
        
        # 用于存储函数调用结果
        knowledge_level_result = None
        selected_files_result = None
        
        try:
            # 如果使用聊天会话，直接发送消息
            if chat:
                response = chat.send_message(user_query)
            else:
                # 否则使用传统方式
                conversation_history = [
                    types.Content(
                        role="user",
                        parts=[types.Part(text=user_query)]
                    )
                ]
                
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=conversation_history,
                    config=self.config,
                )
            
            # 循环处理函数调用
            max_iterations = 10
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                
                # 提取函数调用
                function_calls_list = []
                if response.candidates and len(response.candidates) > 0:
                    parts = response.candidates[0].content.parts
                    if parts and len(parts) > 0:
                        for part in parts:
                            if hasattr(part, 'function_call') and part.function_call:
                                function_calls_list.append(part.function_call)
                
                if not function_calls_list:
                    # 没有函数调用，返回最终回复
                    return response.text if response.text else "抱歉，我无法生成回复。"
                
                # 处理所有函数调用
                function_responses = []
                
                for function_call in function_calls_list:
                    # 执行函数调用
                    result = self.execute_function(
                        function_call, 
                        user_query, 
                        knowledge_level_result, 
                        selected_files_result
                    )
                    
                    # 保存结果
                    if function_call.name == "get_knowledge_level":
                        knowledge_level_result = result
                    elif function_call.name == "select_relevant_files":
                        selected_files_result = result
                    elif function_call.name == "generate_detailed_response":
                        # 如果调用了 generate_detailed_response，任务完成
                        return result["response"]
                    
                    # 创建函数响应
                    function_response = types.Part.from_function_response(
                        name=function_call.name,
                        response=result
                    )
                    function_responses.append(function_response)
                
                # 发送函数响应并获取新的回复
                if chat:
                    response = chat.send_message(function_responses)
                else:
                    conversation_history.append(response.candidates[0].content)
                    conversation_history.append(
                        types.Content(
                            role="user",
                            parts=function_responses
                        )
                    )
                    response = self.client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=conversation_history,
                        config=self.config,
                    )
            
            return "⚠️ 达到最大迭代次数限制"
            
        except Exception as e:
            return f"❌ 处理过程中出现错误: {str(e)}"
    
    def process_query_for_gradio(self, user_query: str):
        """
        处理用户查询并返回格式化的结果
        
        Returns:
            tuple: (函数调用路径, 最终回复)
        """
        if not user_query or not user_query.strip():
            return "⚠️ 请输入有效的问题", ""
        
        # 用于记录函数调用路径
        function_call_log = []
        function_call_log.append(f"### 📝 用户问题\n\n{user_query}\n")
        function_call_log.append("\n### 🧠 Director Agent 分析路径\n")
        
        # 用于存储函数调用结果
        knowledge_level_result = None
        selected_files_result = None
        final_response = ""
        
        # 构建对话历史
        conversation_history = [
            types.Content(
                role="user",
                parts=[types.Part(text=user_query)]
            )
        ]
        
        # 循环处理
        max_iterations = 10
        iteration = 0
        step_number = 1
        
        try:
            while iteration < max_iterations:
                iteration += 1
                
                # 调用模型
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=conversation_history,
                    config=self.config,
                )
                
                # 提取函数调用
                function_calls_list = []
                if response.candidates and len(response.candidates) > 0:
                    parts = response.candidates[0].content.parts
                    if parts and len(parts) > 0:
                        for part in parts:
                            if hasattr(part, 'function_call') and part.function_call:
                                function_calls_list.append(part.function_call)
                
                if not function_calls_list:
                    # 没有函数调用，得到最终回复
                    if response.text:
                        final_response = response.text
                    break
                
                # 将模型的响应添加到对话历史
                conversation_history.append(response.candidates[0].content)
                
                # 处理所有函数调用
                function_responses = []
                
                for function_call in function_calls_list:
                    # 记录函数调用
                    function_call_log.append(f"\n#### 步骤 {step_number}: 调用函数 `{function_call.name}`\n")
                    
                    # 格式化参数
                    args_dict = dict(function_call.args)
                    function_call_log.append(f"**参数:**\n```json\n{json.dumps(args_dict, ensure_ascii=False, indent=2)}\n```\n")
                    
                    # 执行函数调用
                    result = self.execute_function(
                        function_call, 
                        user_query, 
                        knowledge_level_result, 
                        selected_files_result
                    )
                    
                    # 记录结果
                    if function_call.name == "get_knowledge_level":
                        knowledge_level_result = result
                        function_call_log.append("**结果:**\n")
                        for subject, info in result["subjects_info"].items():
                            function_call_log.append(f"- **{subject}**: {info['level']} - {info['detailed_description']}\n")
                    
                    elif function_call.name == "select_relevant_files":
                        selected_files_result = result
                        function_call_log.append("**结果:**\n")
                        function_call_log.append(f"- 选中文件数: {len(result['selected_files'])}\n")
                        for file_info in result["selected_files"]:
                            function_call_log.append(f"  - 📄 {file_info['title']}\n")
                    
                    elif function_call.name == "generate_detailed_response":
                        final_response = result["response"]
                        function_call_log.append("**结果:**\n")
                        function_call_log.append(f"- ✅ 生成了详细回复（{result['response_length']} 字符）\n")
                        function_call_log.append(f"- 使用知识水平: {'是' if result['used_knowledge_level'] else '否'}\n")
                        function_call_log.append(f"- 使用文档: {'是' if result['used_files'] else '否'}\n")
                    
                    step_number += 1
                    
                    # 创建函数响应
                    function_response = types.Part.from_function_response(
                        name=function_call.name,
                        response=result
                    )
                    function_responses.append(function_response)
                
                # 如果调用了 generate_detailed_response，任务完成
                if any(fc.name == "generate_detailed_response" for fc in function_calls_list):
                    break
                
                # 将函数响应添加到对话历史
                conversation_history.append(
                    types.Content(
                        role="user",
                        parts=function_responses
                    )
                )
            
            # 返回结果
            path_text = "\n".join(function_call_log)
            return path_text, final_response
            
        except Exception as e:
            error_msg = f"❌ 处理过程中出现错误: {str(e)}"
            return error_msg, ""


def create_gradio_interface():
    """创建 Gradio 聊天界面（支持多轮对话）"""
    # 尝试加载环境变量
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # 初始化 Director Agent
    try:
        agent = GradioDirectorAgent()
    except ValueError as e:
        print(f"错误: {e}")
        print("请设置 GOOGLE_API_KEY 或 GEMINI_API_KEY 环境变量")
        sys.exit(1)
    
    # 创建 Gradio 聊天界面
    with gr.Blocks(title="Director Agent 聊天系统", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 💬 Director Agent 智能对话系统
        
        支持**真正的多轮对话**！系统会记住对话历史，可以理解上下文。
        
        **系统能力:**
        - 🧠 智能分析用户请求，调用合适的工具
        - 📚 获取用户知识水平（微积分、代数、天文学、通用科学）
        - 📄 选择相关文档（天文学课件）
        - 🤖 生成个性化的详细回复
        - 💬 支持多轮对话，理解上下文引用
        """)
        
        # 使用 gr.State 保存聊天会话
        chat_session = gr.State(None)
        
        # 聊天界面
        chatbot = gr.Chatbot(
            label="对话历史",
            height=500,
            show_label=True,
            bubble_full_width=False
        )
        
        with gr.Row():
            msg = gr.Textbox(
                label="输入消息",
                placeholder="输入您的问题，例如：我在天文学方面学了什么？",
                scale=4,
                show_label=False
            )
            submit_btn = gr.Button("发送 📤", variant="primary", scale=1)
        
        with gr.Row():
            clear_btn = gr.Button("🗑️ 清除历史", variant="secondary")
            retry_btn = gr.Button("🔄 重试上一条", variant="secondary")
        
        gr.Markdown("""
        ### 💡 示例对话:
        
        **连续提问示例：**
        1. "我在天文学方面学了什么？"
        2. "详细解释一下太阳的内部结构"
        3. "我刚才问了什么？" ← AI 会记住并回答
        4. "能再简单点解释吗？" ← AI 理解是指太阳的内部结构
        
        **其他示例问题：**
        - 给我总结一下开普勒定律
        - 望远镜的工作原理是什么？
        - 我这学期学了哪些天文学知识？
        """)
        
        # 初始化或获取聊天会话
        def get_or_create_chat(chat):
            if chat is None:
                chat = agent.client.chats.create(
                    model="gemini-2.0-flash",
                    config=agent.config
                )
            return chat
        
        # 处理用户消息
        def respond(message, history, chat):
            if not message or not message.strip():
                return history, "", chat
            
            # 获取或创建聊天会话
            chat = get_or_create_chat(chat)
            
            # 调用 DirectorAgent 处理
            response = agent.process_query_with_chat(message, chat)
            
            # 更新历史
            history = history or []
            history.append((message, response))
            
            return history, "", chat
        
        # 清除历史
        def clear_history():
            return [], None
        
        # 重试上一条
        def retry_last(history, chat):
            if not history or len(history) == 0:
                return history, "", chat
            
            # 获取最后一条用户消息
            last_message = history[-1][0]
            
            # 删除最后一条对话
            history = history[:-1]
            
            # 重新发送
            return respond(last_message, history, chat)
        
        # 绑定事件
        submit_btn.click(
            fn=respond,
            inputs=[msg, chatbot, chat_session],
            outputs=[chatbot, msg, chat_session]
        )
        
        msg.submit(
            fn=respond,
            inputs=[msg, chatbot, chat_session],
            outputs=[chatbot, msg, chat_session]
        )
        
        clear_btn.click(
            fn=clear_history,
            outputs=[chatbot, chat_session]
        )
        
        retry_btn.click(
            fn=retry_last,
            inputs=[chatbot, chat_session],
            outputs=[chatbot, msg, chat_session]
        )
    
    return demo


def main():
    """主程序入口"""
    demo = create_gradio_interface()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )


if __name__ == "__main__":
    main()
