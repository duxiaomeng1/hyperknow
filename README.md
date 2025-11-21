# 智能学习助手系统 (AI Learning Assistant)

基于 Google Gemini API 的智能学习助手，能够根据用户的知识水平和相关文档提供个性化的学习辅导。系统采用 **Director Agent** 架构，通过函数调用 (Function Calling) 智能决策调用不同的工具来满足用户需求。

## 📋 项目简介

这是一个支持多轮对话的智能教学助手系统，主要功能包括：

- 🎯 **知识水平追踪**：记录并查询用户在不同学科的知识水平
- 📚 **智能文档选择**：根据问题自动选择相关的课程文档
- 💬 **个性化回答生成**：基于用户水平和文档内容生成定制化解答
- 🔄 **多轮对话支持**：支持上下文记忆，可以引用之前的对话内容
- 🖥️ **Web 界面**：提供友好的 Gradio 界面，可视化展示决策过程

### 支持的学科领域

- 📐 **微积分 (Calculus)**：导数、积分、极限等
- 🔢 **代数 (Algebra)**：方程、函数、表达式等
- 🌌 **天文学 (Astronomy)**：天体、星系、轨道力学等
- 🔬 **通用科学 (General Science)**：物理、化学、生物等基础科学

## 🏗️ 系统架构

系统采用 **Director Agent + Tool Calling** 架构：

```
用户提问
    ↓
Director Agent (决策中心)
    ↓
  分析并调用工具
    ├─→ Memory Tool (知识水平查询)
    ├─→ File Selection Tool (文档选择)
    └─→ Response Generator (回答生成)
    ↓
返回个性化回答
```

### 核心组件

1. **Director Agent** (`DirectorAgent` 类)
   - 负责分析用户请求
   - 决定调用哪些工具及调用顺序
   - 协调各个工具之间的数据流

2. **Memory Tool** (`tools/memory_tool.py`)
   - 管理用户的知识水平信息
   - 从 `memory.json` 读取/写入数据

3. **File Selection Tool** (`tools/select_file_tool.py`)
   - 根据问题智能选择相关文档
   - 从 `metadata.json` 读取文档元数据

4. **Response Generator Tool** (`tools/response_generator_tool.py`)
   - 整合知识水平和文档内容
   - 使用 Gemini API 生成详细回答

## 🚀 快速开始

### 1. 环境要求

- Python 3.9+
- Google Gemini API Key

### 2. 安装依赖

```bash
# 克隆或下载项目后，进入项目目录
cd homework

# 安装所需的 Python 包
pip install -r requirements.txt
```

### 3. 配置 API Key

创建 `.env` 文件（或设置环境变量）：

```bash
# 方法 1: 创建 .env 文件
echo "GEMINI_API_KEY=your_api_key_here" > .env

# 方法 2: 或者使用 GOOGLE_API_KEY
echo "GOOGLE_API_KEY=your_api_key_here" > .env

# 方法 3: 或者直接导出环境变量
export GEMINI_API_KEY=your_api_key_here
```

**获取 API Key**：访问 [Google AI Studio](https://aistudio.google.com/app/apikey) 获取免费的 API Key。

### 4. 运行程序

#### 命令行版本 (`main.py`)

```bash
# 单次查询模式
python main.py "你的问题"

# 示例
python main.py "解释一下太阳的内部结构"
python main.py "我在天文学方面学了什么"
python main.py "开普勒第三定律是什么"
```

#### Web 界面版本 (`app.py`)

```bash
# 启动 Gradio Web 界面
python app.py
```

启动后，浏览器会自动打开 `http://127.0.0.1:7860`，你可以：
- 在界面中输入问题
- 查看完整的决策过程
- 支持多轮对话

## 📖 使用示例

### 示例 1：查询知识水平

```bash
python main.py "我在天文学方面的知识水平如何？"
```

**系统流程**：
1. Director Agent 识别到需要查询知识水平
2. 调用 `get_knowledge_level(["astronomy"])`
3. 返回用户的天文学知识水平信息

### 示例 2：学习天文学知识

```bash
python main.py "解释一下太阳的内部结构"
```

**系统流程**：
1. 调用 `get_knowledge_level(["astronomy"])` 了解用户水平
2. 调用 `select_relevant_files(["301F09.Ch16.Sun.Slides.pdf"])` 选择相关课件
3. 调用 `generate_detailed_response()` 生成个性化回答

### 示例 3：多轮对话

```bash
# 第一轮
python main.py "开普勒定律是什么"

# 第二轮（引用上下文）
python main.py "我上次问了什么"
```

**系统特点**：
- 自动识别上下文查询
- 无需调用工具，直接从对话历史中获取答案

## 📁 项目结构

```
homework/
├── main.py                 # 命令行版本主程序
├── app.py                  # Web 界面版本 (Gradio)
├── requirements.txt        # 依赖列表
├── memory.json            # 用户知识水平数据
├── metadata.json          # 文档元数据
├── .env                   # API Key 配置（需自行创建）
├── tools/                 # 工具模块目录
│   ├── memory_tool.py            # 知识水平管理工具
│   ├── select_file_tool.py       # 文件选择工具
│   └── response_generator_tool.py # 回答生成工具
└── document/              # 课程文档目录
    ├── 301F09.Ch16.Sun.Slides.pdf          # 太阳相关课件
    ├── 301F09.IntroOrbitsLight.I.pdf       # 轨道与光学 I
    ├── 301F09.LecturesCh3.5_4.pdf          # 光谱分析课件
    ├── 301F09.TelescopesCh5.9.16.09.pdf    # 望远镜课件
    └── 301F09Scalo.IntOrbLight.II.pdf      # 轨道与光学 II
```

## 🔧 配置文件说明

### `memory.json` - 知识水平数据

存储用户在各学科的知识水平信息：

```json
{
  "knowledge_levels": {
    "astronomy": {
      "level": "intermediate",
      "detailed_description": "已学习太阳系、恒星演化、开普勒定律等基础天文知识"
    },
    "calculus": {
      "level": "beginner",
      "detailed_description": "了解导数和积分的基本概念"
    }
  }
}
```

### `metadata.json` - 文档元数据

存储课程文档的元信息：

```json
{
  "files": [
    {
      "title": "301F09.Ch16.Sun.Slides.pdf",
      "file_path": "document/301F09.Ch16.Sun.Slides.pdf",
      "content_summary": "介绍太阳的结构、核反应、太阳活动等内容",
      "topics": ["太阳", "恒星", "核聚变"],
      "difficulty": "intermediate"
    }
  ]
}
```

## 🎯 核心功能详解

### 1. Director Agent 决策流程

Director Agent 会根据用户问题自动决定调用顺序：

**流程 A：天文学相关问题**
```
用户: "解释太阳的内部结构"
  ↓
步骤 1: get_knowledge_level(["astronomy"]) 
        → 了解用户天文学水平
  ↓
步骤 2: select_relevant_files(["301F09.Ch16.Sun.Slides.pdf"])
        → 选择太阳相关课件
  ↓
步骤 3: generate_detailed_response(use_knowledge=True, use_files=True)
        → 基于用户水平和课件生成回答
```

**流程 B：上下文查询**
```
用户: "我刚才问了什么？"
  ↓
直接查看对话历史并回答（不调用任何工具）
```

### 2. 多轮对话支持

系统使用 Gemini 的聊天会话功能，自动维护对话上下文：

```python
# Web 界面版本 (app.py) 会自动管理会话
# 命令行版本需要手动启用会话模式
```

### 3. 智能文档选择

系统会根据问题关键词精确选择相关文档：

| 关键词 | 选择的文档 |
|--------|-----------|
| 太阳、恒星结构 | `301F09.Ch16.Sun.Slides.pdf` |
| 望远镜、光学系统 | `301F09.TelescopesCh5.9.16.09.pdf` |
| 开普勒定律、轨道 | `301F09.IntroOrbitsLight.I.pdf`, `301F09Scalo.IntOrbLight.II.pdf` |
| 光谱、吸收线 | `301F09.LecturesCh3.5_4.pdf` |

## 🛠️ 高级用法

### 添加新文档

1. 将 PDF 文件放入 `document/` 目录
2. 在 `metadata.json` 中添加文档信息：

```json
{
  "title": "新文档.pdf",
  "file_path": "document/新文档.pdf",
  "content_summary": "这个文档的内容摘要",
  "topics": ["主题1", "主题2"],
  "difficulty": "beginner"
}
```

### 更新知识水平

直接编辑 `memory.json` 文件：

```json
{
  "knowledge_levels": {
    "new_subject": {
      "level": "advanced",
      "detailed_description": "详细的知识水平描述"
    }
  }
}
```

### 自定义 Director Agent 行为

编辑 `main.py` 或 `app.py` 中的 `system_instruction` 字段，可以调整 Director Agent 的决策逻辑。

## 🐛 常见问题

### Q1: 提示 "请设置 GOOGLE_API_KEY 或 GEMINI_API_KEY 环境变量"

**解决方法**：
```bash
# 创建 .env 文件
echo "GEMINI_API_KEY=your_api_key_here" > .env

# 或者直接导出
export GEMINI_API_KEY=your_api_key_here
```

### Q2: 无法读取 PDF 文件

**原因**：系统使用 Gemini 的文件上传功能读取 PDF，需要确保：
- PDF 文件路径正确
- API Key 有权限上传文件
- 文件大小不超过限制（20MB）

### Q3: Web 界面无法启动

**解决方法**：
```bash
# 检查是否安装了 gradio
pip install gradio>=4.0.0

# 如果端口被占用，可以指定其他端口
python app.py  # 会自动分配可用端口
```

### Q4: Director Agent 没有调用预期的工具

**原因**：Director Agent 的决策取决于系统指令。可以：
1. 检查 `system_instruction` 是否正确
2. 确保问题中包含明确的关键词
3. 查看终端输出的决策日志

## 📊 性能优化建议

1. **减少 API 调用**：对于简单问题，可以跳过某些工具调用
2. **缓存文档内容**：避免重复上传相同的 PDF 文件
3. **调整模型参数**：可以修改 `temperature`、`max_tokens` 等参数

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目仅供学习和研究使用。

## 🔗 相关链接

- [Google Gemini API 文档](https://ai.google.dev/gemini-api/docs)
- [Gradio 文档](https://www.gradio.app/docs/)
- [Google AI Studio](https://aistudio.google.com/)

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 GitHub Issue
- 发送邮件至项目维护者

---

**祝你学习愉快！🎓**
