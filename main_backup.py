"""
使用 Google Gemini 的 Function Calling 来智能调用记忆工具
"""
import os
import sys
import json
from google import genai
from google.genai import types
from tools.memory_tool import MemoryTool
from tools.select_file_tool import SelectFileTool


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


# 定义文件选择函数的声明
select_relevant_files_function = {
    "name": "select_relevant_files",
    "description": """根据用户的问题和需求，从可用的文档库中选择相关的文件。
    
当用户提到以下任何情况时，应该调用此函数：
- 询问具体的知识点、概念、理论（需要查阅文档）
- 要求详细解释某个主题
- 需要参考课程资料或文档
- 询问关于天文学、物理学等学科的具体内容

可用的文件及其内容：
- 301F09.Ch16.Sun.Slides.pdf: 太阳的物理性质、内部结构、大气层、太阳活动、核聚变、太阳中微子观测
- 301F09.IntroOrbitsLight.I.pdf: 科学记数法、测量单位（距离和角度）、开普勒行星运动定律、从地心说到日心说模型
- 301F09.LecturesCh3.5_4.pdf: 多普勒效应、原子和辐射、光谱线形成、分子、光谱线分析（化学成分、温度、径向速度）
- 301F09Scalo.IntOrbLight.II.pdf: 牛顿运动定律和引力定律、光的性质、光谱学基础
- 301F09.TelescopesCh5.9.16.09.pdf: 望远镜原理、聚光能力、分辨率极限、不同类型望远镜（光学、红外、X射线、伽马射线）、自适应光学、干涉测量

主题分类：
- astronomy（天文学）：所有文件都涵盖
- physics（物理学）：所有文件都涵盖
- history（历史）：301F09.IntroOrbitsLight.I.pdf

示例触发场景：
- "太阳的内部结构是什么？" → 选择 ["301F09.Ch16.Sun.Slides.pdf"]
- "开普勒定律是什么？" → 选择 ["301F09.IntroOrbitsLight.I.pdf"]
- "多普勒效应在天文学中的应用" → 选择 ["301F09.LecturesCh3.5_4.pdf"]
- "望远镜的工作原理" → 选择 ["301F09.TelescopesCh5.9.16.09.pdf"]
- "牛顿定律和引力" → 选择 ["301F09Scalo.IntOrbLight.II.pdf"]
""",
    "parameters": {
        "type": "object",
        "properties": {
            "file_titles": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "301F09.Ch16.Sun.Slides.pdf",
                        "301F09.IntroOrbitsLight.I.pdf",
                        "301F09.LecturesCh3.5_4.pdf",
                        "301F09Scalo.IntOrbLight.II.pdf",
                        "301F09.TelescopesCh5.9.16.09.pdf"
                    ]
                },
                "description": "需要查询的文件标题列表，从可用文件中选择最相关的一个或多个"
            },
        },
        "required": ["file_titles"],
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


def process_user_query(user_query: str):
    """
    处理用户查询，使用 Function Calling 智能调用记忆工具和文件选择工具
    
    Args:
        user_query: 用户的问题或请求
    """
    print(f"\n{'='*60}")
    print(f"用户查询: {user_query}")
    print(f"{'='*60}\n")
    
    # 初始化客户端和工具
    client = initialize_client()
    memory_tool = MemoryTool()
    select_file_tool = SelectFileTool()
    
    # 配置工具（同时支持两个函数）
    tools = types.Tool(function_declarations=[
        get_knowledge_level_function,
        select_relevant_files_function
    ])
    config = types.GenerateContentConfig(
        tools=[tools],
        system_instruction="""你是一个智能学习助手。你可以调用以下函数来帮助用户：

1. get_knowledge_level: 当用户询问学习内容、知识水平、掌握程度时调用
2. select_relevant_files: 当用户需要详细了解某个具体知识点或主题时调用

调用规则：
- 如果用户询问"学了什么"、"知识水平"，调用 get_knowledge_level
- 如果用户询问具体概念、理论、要求详细解释，调用 select_relevant_files
- 可以同时调用多个函数（例如：先获取知识水平，再选择相关文件）
- 根据返回的数据给出准确、详细的回答

学科映射：
- 微积分 → calculus
- 代数 → algebra  
- 天文/天文学 → astronomy
- 科学/通用科学 → general_science
"""
    )
    
    # 第一次请求：让模型决定是否需要调用函数
    print("🤖 正在分析您的请求...")
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=user_query,
        config=config,
    )
    
    # 检查是否有函数调用
    function_calls_list = []
    
    if response.candidates and len(response.candidates) > 0:
        parts = response.candidates[0].content.parts
        if parts and len(parts) > 0:
            # 检查每个part，找到所有function_call
            for part in parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls_list.append(part.function_call)
    
    if function_calls_list:

重要规则：
1. 如果用户提到任何学科（微积分、代数、天文学、科学），必须调用函数获取知识水平
2. 如果用户询问"学了什么"、"知识水平"、"掌握程度"，必须调用函数
3. 不要猜测或假设用户的知识水平，必须通过函数获取真实数据
4. 调用函数后，基于返回的 level 和 detailed_description 给出针对性的回答

学科映射：
- 微积分 → calculus
- 代数 → algebra  
- 天文/天文学 → astronomy
- 科学/通用科学 → general_science
"""
    )
    
    # 第一次请求：让模型决定是否需要调用函数
    print("🤖 正在分析您的请求...")
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=user_query,
        config=config,
    )
    
    # 检查是否有函数调用
    has_function_call = False
    function_call = None
    
    if response.candidates and len(response.candidates) > 0:
        parts = response.candidates[0].content.parts
        if parts and len(parts) > 0:
            # 检查每个part，找到function_call
            for part in parts:
                if hasattr(part, 'function_call') and part.function_call:
                    has_function_call = True
                    function_call = part.function_call
                    break
    
    if has_function_call and function_call:
        
        print(f"\n📞 模型决定调用函数: {function_call.name}")
        print(f"📋 参数: {dict(function_call.args)}")
        
        # 实际调用我们的记忆工具
        if function_call.name == "get_knowledge_level":
            subjects = list(function_call.args.get("subjects", []))
            print(f"\n🔍 正在查询学科: {', '.join(subjects)}")
            
            # 调用实际的工具函数
            memory_result = memory_tool.get_knowledge_level(subjects)
            
            print(f"\n📚 获取到的知识水平信息:")
            print(f"{'-'*60}")
            for subject, info in memory_result["subjects_info"].items():
                print(f"\n学科: {subject}")
                print(f"  级别: {info['level']}")
                print(f"  详细描述: {info['detailed_description']}")
            print(f"{'-'*60}")
            
            # 第二次请求：将函数调用结果返回给模型，生成最终回复
            print(f"\n🤖 正在生成最终回复...\n")
            
            # 构建包含函数响应的对话历史
            function_response = types.Part.from_function_response(
                name=function_call.name,
                response=memory_result
            )
            
            # 发送第二次请求
            final_response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=user_query)]
                    ),
                    types.Content(
                        role="model",
                        parts=[response.candidates[0].content.parts[0]]
                    ),
                    types.Content(
                        role="user",
                        parts=[function_response]
                    )
                ],
                config=config,
            )
            
            print(f"{'='*60}")
            print("💬 AI 助手的回复:")
            print(f"{'='*60}")
            print(final_response.text)
            print(f"{'='*60}\n")
            
    else:
        # 如果不需要调用函数，直接返回文本回复
        print(f"\n💬 AI 助手的回复:")
        print(f"{'='*60}")
        print(response.text)
        print(f"{'='*60}\n")


def main():
    """主程序入口"""
    # 尝试从 .env 文件加载环境变量
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # 检查命令行参数
    if len(sys.argv) < 2:
        print("使用示例:")
        print('  python main.py "请告诉我用户在微积分和天文学方面的知识水平"')
        print('  python main.py "给我总结这学期天文课上的所有内容"')
        print('  python main.py "用户对代数的掌握程度如何？"')
        sys.exit(1)
    
    # 获取用户查询
    user_query = sys.argv[1]
    
    # 处理查询
    process_user_query(user_query)


if __name__ == "__main__":
    main()
