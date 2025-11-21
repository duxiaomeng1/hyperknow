"""
使用 Google Gemini 的 Function Calling 来智能调用记忆工具和文件选择工具
"""
import os
import sys
import json
from google import genai
from google.genai import types
from tools.memory_tool import MemoryTool
from tools.select_file_tool import SelectFileTool
from tools.response_generator_tool import ResponseGeneratorTool


# 定义记忆获取函数的声明
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
    """
    动态创建文件选择函数声明，从 metadata.json 读取文件信息
    
    Args:
        metadata_path: metadata.json 文件路径
        
    Returns:
        函数声明字典
    """
    metadata = load_metadata(metadata_path)
    files = metadata.get("files", [])
    
    # 提取文件标题列表
    file_titles = [file_info["title"] for file_info in files]
    
    # 生成文件描述列表（包含完整摘要以便更好地匹配）
    file_descriptions = []
    for file_info in files:
        title = file_info["title"]
        summary = file_info.get("content_summary", "无摘要")
        # 保留完整摘要，让模型能更准确地选择
        file_descriptions.append(f"- **{title}**\n  内容: {summary}")
    
    # 收集所有主题
    all_topics = set()
    topic_files = {}  # 主题 -> 文件列表的映射
    for file_info in files:
        topics = file_info.get("topics", [])
        for topic in topics:
            all_topics.add(topic)
            if topic not in topic_files:
                topic_files[topic] = []
            topic_files[topic].append(file_info["title"])
    
    # 生成主题分类描述
    topic_descriptions = []
    for topic in sorted(all_topics):
        files_with_topic = topic_files.get(topic, [])
        if len(files_with_topic) == len(file_titles):
            topic_descriptions.append(f"- {topic}: 所有文件都涵盖")
        else:
            topic_descriptions.append(f"- {topic}: {', '.join(files_with_topic)}")
    
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


# 动态生成文件选择函数的声明
select_relevant_files_function = create_select_files_function()


# 定义响应生成函数的声明
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


def initialize_client():
    """初始化 Google Gemini 客户端"""
    # 从环境变量获取 API Key (支持 GOOGLE_API_KEY 或 GEMINI_API_KEY)
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("错误: 请设置 GOOGLE_API_KEY 或 GEMINI_API_KEY 环境变量")
        print("可以在项目根目录创建 .env 文件，添加:")
        print("GEMINI_API_KEY=your_api_key_here")
        print("或")
        print("GOOGLE_API_KEY=your_api_key_here")
        sys.exit(1)
    
    return genai.Client(api_key=api_key)


class DirectorAgent:
    """
    主决策模型 (Director Agent)
    负责分析用户请求，决定调用哪些工具以及调用顺序
    """
    
    def __init__(self, client):
        """
        初始化 Director Agent
        
        Args:
            client: Google Gemini 客户端实例
        """
        self.client = client
        self.memory_tool = MemoryTool()
        self.select_file_tool = SelectFileTool()
        self.response_generator = ResponseGeneratorTool()
        
        # 决策模型的系统指令
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
- 示例：
  - "解释太阳结构" → 涉及天文学 → 先调用 get_knowledge_level(["astronomy"])
  - "开普勒定律是什么" → 涉及天文学 → 先调用 get_knowledge_level(["astronomy"])
  - "导数的概念" → 涉及微积分 → 先调用 get_knowledge_level(["calculus"])

**规则3：天文学必须查阅文档**
- ✅ 如果问题涉及天文学（astronomy），**必须**在获取知识水平后调用 select_relevant_files
- ✅ 选择所有与问题相关的天文学课件文件
- 原因：文档库存储的是用户的天文学课程课件，是最权威的学习资料

**规则4：最后生成回复**
- ✅ **必须**最后调用 generate_detailed_response
- ✅ 整合知识水平和文档信息生成个性化回答

**📋 标准工作流程**：

**流程A：天文学相关问题**（最常见）
```
第1步: get_knowledge_level(["astronomy"]) 
       → 获取用户天文学水平（如：beginner）
       
第2步: select_relevant_files([相关天文课件])
       → 选择所有与问题主题相关的课件
       
第3步: generate_detailed_response(use_knowledge_level=True, use_selected_files=True)
       → 基于用户水平和课件内容生成回答
```

**流程B：其他学科问题**
```
第1步: get_knowledge_level([学科名称])
       → 获取用户该学科水平
       
第2步: generate_detailed_response(use_knowledge_level=True, use_selected_files=False)
       → 基于用户水平生成回答
```

**流程C：仅询问知识水平**
```
第1步: get_knowledge_level([学科名称])
       → 获取知识水平
       
第2步: 直接返回知识水平信息（不需要调用 generate_detailed_response）
```

**🎯 具体示例（必须遵循）**：

示例 1: "我刚才问了什么？"
   - 识别：这是上下文查询
   - 执行流程：直接查看对话历史并回答（不调用任何工具）

示例 2: "解释太阳的内部结构"
   - 识别：涉及天文学
   - 执行流程A：
     ① get_knowledge_level(["astronomy"])
     ② select_relevant_files(["301F09.Ch16.Sun.Slides.pdf"])
     ③ generate_detailed_response(use_knowledge=True, use_files=True)

示例 3: "我上次问的那个问题能详细解释一下吗？"
   - 识别：引用了上下文 + 需要详细解释
   - 执行流程：
     ① 查看对话历史，确定"上次问的问题"是什么
     ② 根据那个问题，调用相应的工具（如 get_knowledge_level、select_relevant_files）
     ③ 调用 generate_detailed_response 生成详细解释
     
**学科识别关键词**：
- **astronomy（天文学）**: 太阳、月亮、星球、行星、恒星、星系、轨道、开普勒、牛顿引力、光学、望远镜、天体、宇宙
- **calculus（微积分）**: 导数、积分、极限、微分、函数、连续性
- **algebra（代数）**: 方程、变量、多项式、因式分解、二次方程
- **general_science（通用科学）**: 物理、化学、生物、能量、运动

**⚠️ 重要提醒**：
- 每次调用函数时，只调用一个函数，等待结果后再决定下一步
- 不要一次性调用多个函数
- 严格按照流程顺序执行
- 天文学问题必须执行完整的流程A（三个步骤）
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
        """
        执行函数调用
        
        Args:
            function_call: 函数调用对象
            user_query: 用户查询
            knowledge_level_result: 知识水平查询结果
            selected_files_result: 文件选择结果
            
        Returns:
            函数执行结果
        """
        print(f"\n📞 Director Agent 调用函数: {function_call.name}")
        print(f"📋 参数: {dict(function_call.args)}")
        
        if function_call.name == "get_knowledge_level":
            subjects = list(function_call.args.get("subjects", []))
            print(f"\n🔍 正在查询学科: {', '.join(subjects)}")
            
            result = self.memory_tool.get_knowledge_level(subjects)
            
            print(f"\n📚 获取到的知识水平信息:")
            print(f"{'-'*60}")
            for subject, info in result["subjects_info"].items():
                print(f"\n学科: {subject}")
                print(f"  级别: {info['level']}")
                print(f"  详细描述: {info['detailed_description']}")
            print(f"{'-'*60}")
            
            return result
            
        elif function_call.name == "select_relevant_files":
            file_titles = list(function_call.args.get("file_titles", []))
            print(f"\n📁 正在选择文件: {', '.join(file_titles)}")
            
            result = self.select_file_tool.select_files_by_titles(file_titles)
            
            print(f"\n📄 选中的文件:")
            print(f"{'-'*60}")
            for file_info in result["selected_files"]:
                print(f"\n文件: {file_info['title']}")
                print(f"  路径: {file_info['file_path']}")
                print(f"  URI: {file_info.get('file_uri', 'N/A')}")
                print(f"  摘要: {file_info['content_summary'][:100]}...")
                print(f"  主题: {', '.join(file_info['topics'])}")
            if result["not_found"]:
                print(f"\n未找到的文件: {', '.join(result['not_found'])}")
            print(f"{'-'*60}")
            
            return result
            
        elif function_call.name == "generate_detailed_response":
            query = function_call.args.get("user_query", user_query)
            use_knowledge = function_call.args.get("use_knowledge_level", False)
            use_files = function_call.args.get("use_selected_files", False)
            
            print(f"\n🤖 Director Agent 生成详细回答...")
            print(f"  使用知识水平: {'是' if use_knowledge else '否'}")
            print(f"  使用文档信息: {'是' if use_files else '否'}")
            
            # 准备参数
            knowledge_info = knowledge_level_result if use_knowledge else None
            files_info = selected_files_result.get("selected_files", []) if use_files and selected_files_result else None
            
            # 生成流式响应（不再需要 file_uris，直接使用 files_info 中的 file_path）
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
    
    def process_query(self, user_query: str, chat=None):
        """
        处理用户查询的主流程，支持使用聊天会话对象
        
        Args:
            user_query: 用户的问题或请求
            chat: 可选的聊天会话对象，用于多轮对话
        """
        print(f"\n{'='*60}")
        print(f"用户查询: {user_query}")
        print(f"{'='*60}\n")
        
        # 用于存储函数调用结果
        knowledge_level_result = None
        selected_files_result = None
        
        print("🧠 Director Agent 正在分析您的请求...")
        
        # 如果使用聊天会话，直接发送消息
        if chat:
            response = chat.send_message(user_query)
        else:
            # 否则使用传统方式（构建对话历史）
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
        
        # 循环处理，直到不再有函数调用
        max_iterations = 10  # 防止无限循环
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
                # 没有函数调用，说明得到最终回复
                print(f"\n💬 Director Agent 的回复:")
                print(f"{'='*60}")
                print(response.text)
                print(f"{'='*60}\n")
                return
            
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
                    print(f"\n{'='*60}")
                    print("✅ Director Agent 完成任务")
                    print(f"{'='*60}\n")
                    return
                
                # 创建函数响应
                function_response = types.Part.from_function_response(
                    name=function_call.name,
                    response=result
                )
                function_responses.append(function_response)
            
            # 发送函数响应并获取新的回复
            if chat:
                # 使用聊天会话发送函数响应
                response = chat.send_message(function_responses)
            else:
                # 使用传统方式
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
        
        print("\n⚠️ 警告: 达到最大迭代次数限制")
        print(f"{'='*60}\n")


def process_user_query(user_query: str):
    """
    处理用户查询，使用 Director Agent 智能调用记忆工具、文件选择工具和响应生成工具
    
    Args:
        user_query: 用户的问题或请求
    """
    # 初始化客户端
    client = initialize_client()
    
    # 创建 Director Agent
    director = DirectorAgent(client)
    
    # 使用 Director Agent 处理查询
    director.process_query(user_query)


def main():
    """主程序入口 - 支持交互式多轮对话"""
    # 尝试从 .env 文件加载环境变量
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # 初始化客户端
    client = initialize_client()
    
    # 创建 Director Agent
    director = DirectorAgent(client)
    
    # 如果有命令行参数，使用单次查询模式（向后兼容）
    if len(sys.argv) >= 2:
        user_query = sys.argv[1]
        director.process_query(user_query)
        return
    
    # 交互式多轮对话模式
    print("\n" + "="*60)
    print("🌟 欢迎使用 AI 学习助手 - 交互式多轮对话模式")
    print("="*60)
    print("\n📚 功能说明:")
    print("  • 可以连续提问，系统会记住对话历史")
    print("  • 支持询问知识水平、查询文档、获取详细解释")
    print("  • 输入 'quit'、'exit' 或 'q' 退出程序")
    print("  • 输入 'help' 查看帮助信息")
    print("  • 输入 'clear' 清除对话历史，开始新对话")
    print("\n" + "="*60 + "\n")
    
    # 创建聊天会话
    chat = client.chats.create(
        model="gemini-2.0-flash",
        config=director.config
    )
    
    print("✅ 聊天会话已创建，您可以开始提问了！\n")
    
    # 主对话循环
    while True:
        try:
            # 获取用户输入
            user_input = input("👤 您: ").strip()
            
            # 检查是否为空
            if not user_input:
                continue
            
            # 处理特殊命令
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 感谢使用 AI 学习助手，再见！\n")
                break
            
            if user_input.lower() == 'help':
                print("\n📖 帮助信息:")
                print("  • 直接输入问题，例如:")
                print("    - '我在天文学方面学了什么？'")
                print("    - '解释太阳的内部结构'")
                print("    - '开普勒三定律是什么？'")
                print("  • 命令:")
                print("    - 'quit', 'exit', 'q': 退出程序")
                print("    - 'help': 显示此帮助信息")
                print("    - 'clear': 清除对话历史")
                print("    - 'history': 查看对话历史")
                print()
                continue
            
            if user_input.lower() == 'clear':
                print("\n🔄 正在清除对话历史...\n")
                # 重新创建聊天会话
                chat = client.chats.create(
                    model="gemini-2.0-flash",
                    config=director.config
                )
                print("✅ 对话历史已清除，您可以开始新的对话了！\n")
                continue
            
            if user_input.lower() == 'history':
                print("\n📜 对话历史:")
                print("="*60)
                history = chat.get_history()
                for i, message in enumerate(history, 1):
                    role = "用户" if message.role == "user" else "助手"
                    print(f"\n[{i}] {role}:")
                    if message.parts:
                        for part in message.parts:
                            if hasattr(part, 'text') and part.text:
                                print(f"  {part.text}")
                            elif hasattr(part, 'function_call') and part.function_call:
                                print(f"  [调用函数: {part.function_call.name}]")
                            elif hasattr(part, 'function_response') and part.function_response:
                                print(f"  [函数响应: {part.function_response.name}]")
                print("="*60 + "\n")
                continue
            
            # 处理用户查询
            director.process_query(user_input, chat=chat)
            
        except KeyboardInterrupt:
            print("\n\n👋 检测到 Ctrl+C，正在退出...\n")
            break
        except EOFError:
            print("\n\n👋 检测到 EOF，正在退出...\n")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {str(e)}\n")
            import traceback
            traceback.print_exc()
            print("\n💡 您可以继续提问，或输入 'quit' 退出。\n")


if __name__ == "__main__":
    main()
