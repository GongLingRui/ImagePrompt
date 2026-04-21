# ImagePrompt - AI图像提示词生成系统

基于多Agent架构的智能图像提示词生成系统，支持从文本描述或图片反向推导AI图像生成提示词。

## 功能特性

### 核心功能

<img width="545" height="775" alt="Pasted Graphic 2" src="https://github.com/user-attachments/assets/a787564c-f267-45a4-a429-ed5c2bae125f" />

<img width="527" height="748" alt="Pasted Graphic 3" src="https://github.com/user-attachments/assets/5033fe56-10b3-4a99-9cc0-d7f34350baee" />

<img width="518" height="773" alt="Pasted Graphic 4" src="https://github.com/user-attachments/assets/520c57a7-2a39-4e2f-a550-32657a11767b" />

<img width="533" height="780" alt="Pasted Graphic 5" src="https://github.com/user-attachments/assets/586f87e2-1fc8-4126-99dd-dc6b20b4d80e" />


<img width="528" height="689" alt="Pasted Graphic 6" src="https://github.com/user-attachments/assets/115d48dc-5fd6-4eb8-89d6-968577625647" />

<img width="543" height="786" alt="Pasted Graphic 7" src="https://github.com/user-attachments/assets/1e15c4b7-d0b9-4752-9ada-1c378e794af0" />


<img width="570" height="778" alt="Pasted Graphic 8" src="https://github.com/user-attachments/assets/20c301cd-7b13-45cd-89af-23b6832f960a" />

<img width="557" height="797" alt="Pasted Graphic 9" src="https://github.com/user-attachments/assets/5f855db5-0c46-4c2b-bba2-2919d341ce58" />


1. **文本转提示词 (Text-to-Prompt)**
   - 根据用户需求描述，自动生成适合不同平台的AI图像提示词
   - 支持风格分析、构图分析、情绪分析、视觉概念提取等

2. **图片转提示词 (Image-to-Prompt)**
   - 上传任意图片，系统自动分析并反推出AI图像生成提示词
   - 支持多模态大模型 Kimi K2.5 进行图片理解

3. **多平台提示词适配**
   - Midjourney 提示词
   - DALL-E 提示词
   - Stable Diffusion 提示词
   - 小红书帖子
   - 微信公众号文章
   - TikTok 脚本
   - Hitpoint 文案

4. **策略分析 (Tactician)**
   - 在生成提示词前进行深度策略分析
   - 分析用户意图、平台适配、视觉风格、执行计划
   - 生成策略笔记指导后续生成

5. **反思评审机制 (Reflection)**
   - 对生成的内容进行自动评审
   - 标记高价值内容 (⭐ star)、保留内容 (📝 archive)、质量问题 (🗑️ trash)

### 辅助功能

- **动态加载效果** - 启动时展示系统架构
- **批量测试模式** - 支持CSV文件批量测试
- **会话管理** - 支持多轮对话和任务续接
- **Token统计** - 实时显示API调用和费用统计

## 系统架构

### Agent架构

系统采用多Agent协作架构，包含三个核心Agent：

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户界面层                               │
│                    (ImagePromptCLI / BatchTest)                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Concierge Agent                             │
│                    (前台接待 / 意图识别)                          │
│  - 理解用户输入，判断是闲聊还是需要生成提示词                        │
│  - 路由任务到Orchestrator                                        │
│  - 维护会话历史                                                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestrator Agent                           │
│                   (任务编排 / ReAct循环)                          │
│  - 理解任务需求                                                   │
│  - 规划执行步骤（subject_analysis, style_analysis等）             │
│  - 指挥执行各Action                                               │
│  - 最多3轮执行循环                                                │
└─────────────────────────────────────────────────────────────────┘
                                │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Tactician     │  │     Actions     │  │   WorkSpace     │
│   (策略分析)     │  │    (执行动作)    │  │   (数据存储)    │
│                 │  │                 │  │                 │
│ - 任务预分析    │  │ - subject_      │  │ - Notes管理     │
│ - 策略笔记生成  │  │   analysis      │  │ - tactics存储   │
│ - 指导生成方向  │  │ - style_        │  │ - tactician_    │
│                 │  │   analysis      │  │   analysis      │
└─────────────────┘  │ - mood_         │  └─────────────────┘
                    │   analysis      │
                    │ - composition_   │
                    │   analysis      │
                    │ - visual_       │
                    │   concept       │
                    │ - midjourney_   │
                    │   prompt        │
                    │ - dalle_prompt  │
                    │ - sd_prompt     │
                    │ - xhs_post      │
                    │ - wechat_       │
                    │   article       │
                    │ - tiktok_script │
                    │ - hitpoint      │
                    │ - knowledge     │
                    │ - websearch     │
                    │ - image_to_     │
                    │   prompt        │
                    └─────────────────┘
```

### 数据流

```
用户输入
    │
    ▼
Concierge ──────► 意图识别
    │                    │
    │ 闲聊               │ 需要生成
    ▼                    ▼
返回回复           Orchestrator
                         │
                         ▼
              ┌────────────────────┐
              │   Tactician分析    │ (可选)
              │   (任务策略分析)    │
              └────────────────────┘
                         │
                         ▼
              ┌────────────────────┐
              │    ReAct循环       │
              │  (最多3轮)         │
              └────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    Action 1       Action 2       Action 3
    (subject_)     (style_)       (mood_)
         │               │               │
         └───────────────┼───────────────┘
                         ▼
              ┌────────────────────┐
              │   Notes提取        │
              │ (创建/更新/评审)    │
              └────────────────────┘
                         │
                         ▼
              ┌────────────────────┐
              │    结果展示        │
              │ (按状态分类显示)    │
              └────────────────────┘
```

## 核心模块

### 1. model_base.py - 模型抽象层

统一管理所有模型提供商，提供一致的LLM调用接口。

**主要组件：**
- `ModelProvider` - 模型提供商抽象基类
- `ModelManager` - 模型管理器，负责注册和切换模型
- `call_llm()` - 统一的LLM调用接口
- `create_llm_panel()` - 显示LLM调用面板
- `update_session_stats()` - 更新会话统计

**会话统计：**
```python
{
    "total_calls": 0,              # LLM调用次数
    "total_input_tokens": 0,       # 输入Token数
    "total_output_tokens": 0,      # 输出Token数
    "total_thinking_tokens": 0,   # 思考Token数
    "total_cost": 0.0              # 总费用
}
```

### 2. kimi_provider.py - Kimi模型提供商

Kimi K2.5 模型的实际实现，支持：
- 文本对话
- 图片理解（多模态）
- Web搜索

**配置：**
- 通过环境变量 `KIMI_API_KEY` 设置API密钥
- 默认模型：`kimi-k2.5`
- API地址：`https://api.moonshot.cn/v1`

### 3. WorkSpace - 工作空间

系统的数据中心，管理所有任务数据。

**核心功能：**
- `create_note()` - 创建新的笔记
- `get_note()` - 获取指定笔记
- `get_notes_by_type()` - 按类型获取笔记
- `get_notes_by_status()` - 按状态获取笔记
- `update_note_review_status()` - 更新笔记评审状态

**Note数据结构：**
```python
{
    "type": "midjourney_prompt",   # 笔记类型
    "content": "...",              # 笔记内容
    "source": "step_1",           # 来源
    "review_status": "star",       # 评审状态 (star/archive/trash)
    "review_comment": "..."        # 评审评论
}
```

### 4. ConversationManager - 会话管理

维护会话历史和执行记录。

**核心功能：**
- `add_orchestrator_call()` - 记录Orchestrator调用
- `add_orchestrator_response()` - 记录LLM响应
- `add_execution_record()` - 记录执行步骤
- `update_latest_execution_notes()` - 更新执行记录中的笔记
- `get_recent_orchestrator_calls()` - 获取最近的调用记录

### 5. context_builder.py - 上下文构建

为每个Agent和Action构建专属的上下文。

**主要函数：**
- `build_concierge_context()` - 构建Concierge上下文
- `build_orchestrator_context()` - 构建Orchestrator上下文
- `build_tactician_context()` - 构建Tactician上下文
- `build_action_context()` - 构建Action上下文

## Actions 详解

### subject_analysis - 主题分析

分析用户想要生成图片的主体内容，包括：
- 主体对象（人物、动物、物体等）
- 主体特征（外观、姿态、表情等）
- 主体数量和关系

### style_analysis - 风格分析

确定图片的整体艺术风格：
- 摄影风格（写实、纪实、创意摄影等）
- 绘画风格（水彩、油画、插画等）
- 数字风格（3D渲染、像素艺术等）
- 特定艺术家或流派风格

### mood_analysis - 情绪分析

分析图片应传达的情感和氛围：
- 情绪类型（欢快、悲伤、神秘等）
- 光线氛围（明亮、昏暗、戏剧性等）
- 色彩情绪（暖色调、冷色调等）

### composition_analysis - 构图分析

规划图片的构图方式：
- 视角（平视、俯视、仰视等）
- 构图法则（三分法、对角线、对称等）
- 前景/背景处理

### visual_concept - 视觉概念

定义画面的核心视觉元素：
- 场景设置
- 光线方向和强度
- 色彩方案
- 纹理和材质

### midjourney_prompt / dalle_prompt / sd_prompt

生成特定平台的提示词，自动适配各平台的语法规则。

### xhs_post / wechat_article / tiktok_script / hitpoint

生成适合不同平台的文案内容。

### knowledge - 知识查询

查询相关领域的知识，为提示词生成提供参考。

### websearch - 网络搜索

实时搜索相关信息，获取最新参考素材。

### image_to_prompt - 图片反推

输入图片，输出AI图像生成提示词。

## 业务流程

### 完整执行流程

```
1. 用户输入需求
   ↓
2. Concierge 接收并分析
   - 如果是闲聊，直接回复
   - 如果是任务，创建 Orchestrator 调用记录
   ↓
3. 启动 Orchestrator
   ↓
4. Tactician 策略分析（首次执行时）
   - 分析用户意图
   - 确定平台适配
   - 规划视觉风格
   - 制定执行计划
   ↓
5. ReAct 循环（最多3轮）
   5.1 Orchestrator 调用 LLM 规划下一步
   5.2 如果完成，退出循环
   5.3 执行 Action(s)
   5.4 提取 Notes
   5.5 继续下一轮
   ↓
6. 结果展示
   - 按状态分类显示（star/archive/trash）
   - 显示统计信息
   ↓
7. 用户可继续输入新需求或查看已有内容
```

### Tactician 何时运行

- 仅在 `workspace.tactician_analysis` 为空时运行
- 当用户切换到完全不同任务时（通过关键词重叠度检测 < 50%），自动清除旧分析并重新分析

### 并发控制

- 使用 `Queue` 队列管理多个任务
- 使用 `Lock` 保证线程安全
- 守护线程改为普通线程，确保完整执行
- 退出时等待线程结束

## 文件结构

```
loomi2-1/
├── ImagePrompt.py           # 主程序入口
├── batch_test.py            # 批量测试模块
├── dynamic_loading.py        # 动态加载效果
├── model_base.py            # 模型抽象层
├── kimi_provider.py         # Kimi模型实现
│
├── agents/                  # Agent模块
│   ├── __init__.py
│   ├── concierge.py        # 前台接待Agent
│   ├── orchestrator.py     # 任务编排Agent
│   └── tactician.py        # 策略分析Agent
│
├── core/                    # 核心模块
│   ├── __init__.py
│   ├── workspace.py         # 工作空间
│   ├── conversation.py      # 会话管理
│   ├── context_builder.py   # 上下文构建
│   └── notes_extractor.py   # 笔记提取
│
├── prompts/                 # 提示词模板
│   ├── concierge_prompt.py
│   ├── orchestrator_prompt.py
│   ├── tactician_prompt.py
│   └── action_prompts.py
│
├── .env.example             # 环境变量模板
└── .gitignore              # Git忽略配置
```

## 安装与使用

### 环境要求

- Python 3.10+
- OpenAI SDK
- Rich (终端美化库)

### 安装依赖

```bash
pip install openai rich
```

### 配置API密钥

```bash
# 创建 .env 文件
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
vim .env
```

### 运行程序

```bash
# 交互模式
python ImagePrompt.py

# 批量测试模式
python ImagePrompt.py --batch test.csv
```

### 命令行参数

- `--batch <csv_path>` 或 `-b <csv_path>` - 批量测试模式

### 交互命令

- `exit/quit/bye/退出` - 退出程序
- `help/帮助` - 显示帮助
- `status/状态` - 显示系统状态
- `batch/批量测试` - 启动批量测试

## 批量测试

### CSV格式

```csv
query
生成一个可爱的猫咪图片
生成一个赛博朋克风格的城市夜景
...
```

### 输出结果

自动生成带时间戳的CSV文件，包含：
- 原始查询
- LLM调用记录
- Token使用统计
- 总费用

## 提示词系统

### Prompt类型识别

系统会自动识别正在使用的Prompt类型：
- Concierge
- Orchestrator
- Action: {action_name}

### Action Prompt模板

每个Action都有专属的Prompt模板，定义在 `prompts/action_prompts.py` 中，包含：
- 系统角色定义
- 输入格式说明
- 输出格式要求
- 示例

## 注意事项

1. **API费用** - 使用Kimi API会产生费用，请关注用量统计
2. **并发限制** - 建议单次只运行一个任务，避免资源竞争
3. **敏感信息** - API密钥存储在环境变量中，不要提交到代码仓库
4. **图片支持** - 图片反推功能需要多模态模型支持

## License

MIT License



## 目录

1. [系统概述](#系统概述)
2. [核心设计模式](#核心设计模式)
3. [Agent通信机制](#agent通信机制)
4. [数据流与状态管理](#数据流与状态管理)
5. [ReAct执行循环](#react执行循环)
6. [Context构建机制](#context构建机制)
7. [Notes系统设计](#notes系统设计)
8. [代码实现详解](#代码实现详解)
9. [如何开发新的Agent](#如何开发新的agent)
10. [如何开发新的Action](#如何开发新的action)

---

## 系统概述

ImagePrompt是一个基于**多Agent协作**的AI图像提示词生成系统。其核心理念是模拟一个专业内容创作团队的工作方式：

```
用户输入
    │
    ▼
┌─────────────────┐
│   Concierge     │ ← 前台接待：理解需求、路由任务
└────────┬────────┘
         │ <call_orchestrator> 标签触发
         ▼
┌─────────────────┐
│   Tactician     │ ← 策略分析：深度分析任务、制定执行计划
└────────┬────────┘
         │ strategy_notes
         ▼
┌─────────────────┐
│   Orchestrator  │ ← 任务编排：ReAct循环、指挥Action执行
└────────┬────────┘
         │ <execute action="xxx"> 标签触发
         ▼
┌─────────────────┐
│    Actions      │ ← 执行单元：各类专业分析/生成动作
└────────┬────────┘
         │ notes_created
         ▼
┌─────────────────┐
│    WorkSpace    │ ← 数据中心：存储所有Notes和状态
└─────────────────┘
```

---

## 核心设计模式

### 1. Prompt-Driven Architecture（提示词驱动架构）

每个Agent的核心是其**System Prompt**，定义了Agent的角色、能力边界、输出格式。

```python
# concierge.py
class Concierge:
    def __init__(self, workspace, conversation):
        self.system_prompt = concierge_prompt  # 预定义的提示词模板
```

**设计要点：**
- System Prompt定义Agent的"人格"和"职责"
- Prompt中嵌入输出格式规范（XML标签）
- Agent通过LLM的function calling能力输出结构化指令

### 2. 上下文注入模式

每个Agent的`process_task()`方法都会调用`build_xxx_context()`构建专属上下文：

```python
# orchestrator.py
def process_task(self, task_message: str, execution_log: list):
    context = build_orchestrator_context(
        task_message, self.workspace, self.conversation, execution_log
    )
    response = call_llm(
        system_prompt=self.system_prompt,
        user_prompt=context,
        ...
    )
```

**上下文包含：**
- 当前任务消息
- 历史执行记录（Round N: observe/think/执行了哪些Action）
- 已创建的Notes（可被@引用）
- Tactician分析结果

### 3. XML指令标签模式

Agent通过XML标签向系统传递指令：

```xml
<!-- Concierge → 系统 -->
<call_orchestrator>
用户希望生成赛博朋克城市雨夜图像...
</call_orchestrator>

<!-- Orchestrator → 系统 -->
<execute action="midjourney_prompt" instruction="基于@visual_concept1生成MJ提示词"/>

<!-- 系统 → LLM -->
<think>这里是我的思考过程...</think>
<observe>这是我观察到的结果...</observe>
```

**解析机制：**
```python
# orchestrator.py
def _extract_execute_commands(self, response: str) -> List[Dict[str, str]]:
    """从LLM响应中提取execute命令"""
    patterns = [
        r'<execute\s+action="([^"]+)"\s+instruction="([^"]+)"\s*/?>',
        # ... 多种格式兼容
    ]
    # 正则匹配，提取action和instruction
```

---

## Agent通信机制

### Agent间的通信流程

```
┌──────────────────────────────────────────────────────────────────┐
│                         Concierge                                 │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 1. 接收用户输入                                              │ │
│  │ 2. 调用LLM，理解意图                                        │ │
│  │ 3. 如果需要生成提示词，输出 <call_orchestrator>              │ │
│  │ 4. 解析响应，检测是否包含 <call_orchestrator>                │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                                │
                                │ conversation.add_concierge_response()
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                      ConversationManager                           │
│  - history: 完整对话历史                                          │
│  - _orchestrator_calls: Orchestrator调用记录                      │
│  - _active_orchestrator_index: 当前活跃调用索引                    │
└──────────────────────────────────────────────────────────────────┘
                                │
                                │ CLI层检查 orchestrator_call
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                      ImagePromptCLI                               │
│  run_orchestrator_async(task_message)                            │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                         Tactician                                 │
│  - analyze_task() → strategy_notes → workspace.tactician_analysis │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Orchestrator                               │
│  process_task() → ReAct循环 → <execute action="xxx">            │
└──────────────────────────────────────────────────────────────────┘
                                │
                                │ execute()
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                     execute() 函数                                 │
│  - 根据action_type从ACTION_PROMPTS获取prompt                      │
│  - 调用call_llm()                                                │
│  - 提取notes → workspace.create_note()                           │
└──────────────────────────────────────────────────────────────────┘
```

### XML标签的流转

1. **Concierge输出标签**：
```python
# concierge.py 第81-104行
def _extract_orchestrator_call(self, response: str) -> Optional[str]:
    # 匹配 <call_orchestrator>...</call_orchestrator>
    match = re.search(r'<call_orchestrator>(.*?)</call_orchestrator>', response, re.DOTALL)
    if match:
        return match.group(1).strip()
```

2. **CLI捕获标签**：
```python
# ImagePrompt.py 第381-412行
def handle_user_input(self, user_input: str):
    response = self.concierge.process_user_input(user_input)
    if after_count > before_count:  # 检测到orchestrator_call
        self.run_orchestrator_async(task_message)
```

3. **Orchestrator输出标签**：
```python
# orchestrator.py 第232-279行
def _extract_execute_commands(self, response: str) -> List[Dict[str, str]]:
    # 匹配 <execute action="xxx" instruction="yyy"/>
    commands = []
    for match in re.finditer(pattern, response, re.DOTALL):
        commands.append({
            "action": match.group(1),
            "instruction": match.group(2)
        })
    return commands
```

---

## 数据流与状态管理

### 三大核心对象

#### 1. WorkSpace（数据中心）

```python
class WorkSpace:
    def __init__(self):
        self.notes: Dict[str, Dict[str, str]] = {}      # 所有Notes
        self._note_counters: Dict[str, int] = {}         # 编号计数器
        self.tactics: Optional[str] = None                # Orchestrator工作备忘
        self.tactician_analysis: Dict[str, Any] = {}     # Tactician分析结果
```

**Note数据结构：**
```python
{
    "type": "midjourney_prompt",    # Note类型
    "content": "cyberpunk city...", # 内容
    "source": "step_1",            # 来源
    "review_status": "star",        # 评审状态
    "review_comment": "高质量"       # 评审意见
}
```

#### 2. ConversationManager（会话历史）

```python
class ConversationManager:
    def __init__(self):
        self.history: List[Dict] = []                    # 完整历史
        self._orchestrator_calls: List[Dict] = []        # Orchestrator调用
        self._active_orchestrator_index: Optional[int] = None
        self._orchestrator_running: bool = False
```

**history条目类型：**
- `user`: 用户消息
- `concierge`: Concierge响应
- `orchestrator`: Orchestrator响应
- `execution`: 执行记录

#### 3. execution_log（执行日志）

由Orchestrator维护，传给`process_task()`：

```python
execution_log = []  # 初始化
for iteration in range(max_iterations):
    result = self.orchestrator.process_task(task_message, execution_log)
    execution_log.append({
        "iteration": iteration + 1,
        "command_index": cmd_idx,
        "action": cmd['action'],
        "instruction": cmd['instruction'],
        "result": step_result
    })
```

---

## ReAct执行循环

ReAct（Reasoning + Acting）是Orchestrator的核心执行模式：

### 执行流程

```python
# orchestrator.py 第41-72行
def process_task(self, task_message: str, execution_log: list):
    for iteration in range(max_iterations):  # 最多3轮
        # 1. 调用LLM进行推理
        response = call_llm(
            system_prompt=self.system_prompt,
            user_prompt=context,
            ...
        )

        # 2. 提取思考结果（可选）
        think_content = self._extract_think_content(response)

        # 3. 提取执行命令
        commands = self._extract_execute_commands(response)

        # 4. 提取观察结果（可选）
        observe_content = self._extract_observe_content(response)

        # 5. 记录执行日志
        execution_log.append({
            "iteration": iteration,
            "think": think_content,
            "observe": observe_content,
            "commands": commands
        })

        # 6. 解析complete状态
        if self._is_completed(response):
            return {"completed": True, "execute_commands": []}

        # 7. 执行所有命令
        for cmd in commands:
            execute(cmd['action'], cmd['instruction'], ...)
```

### Orchestrator的System Prompt

```python
# orchestrator_prompt.py
"""
## Action执行

<execute action="action_type" instruction="具体指令"/>
- action: subject_analysis / style_analysis / midjourney_prompt 等
- instruction: 给Action的具体任务描述

## 工作流程
Round1: subject + style + mood + composition（并行）
Round2: visual_concept（整合）
Round3: midjourney_prompt / dalle_prompt / sd_prompt（生成）
"""
```

### 三轮执行示例

```
Round 1:
  Orchestrator → LLM: "为'赛博朋克城市雨夜'生成提示词"
  LLM响应:
    <think>需要分析主体、风格、氛围...</think>
    <execute action="subject_analysis" instruction="分析赛博朋克城市雨夜"/>
    <execute action="style_analysis" instruction="分析赛博朋克风格"/>
  执行: subject_analysis + style_analysis → workspace.notes

Round 2:
  Orchestrator → LLM: "基于之前的分析，整合视觉概念"
  LLM响应:
    <execute action="visual_concept" instruction="整合@subject_analysis1和@style_analysis1"/>
  执行: visual_concept → workspace.notes

Round 3:
  Orchestrator → LLM: "基于视觉概念生成最终提示词"
  LLM响应:
    <execute action="midjourney_prompt" instruction="基于@visual_concept1生成MJ提示词"/>
    <complete/>
  执行: midjourney_prompt → workspace.notes
  完成!
```

---

## Context构建机制

### build_orchestrator_context()

为Orchestrator构建上下文，包含：

```python
# context_builder.py 第158-365行
def build_orchestrator_context(task_message, workspace, conversation, execution_log):
    parts = []

    # 1. 任务执行时间线
    parts.append("[任务执行时间线]")
    for msg_idx, msg in enumerate(all_messages):
        parts.append(f"用户消息{msg_idx + 1}: {msg['message']}")

        # 显示material材料
        for note_id in workspace.notes:
            if note_id.startswith('material'):
                parts.append(f"@{note_id}: {note_data['content']}")

        # 显示该消息的执行记录
        for record in msg['execution_records']:
            parts.append(f"## Round{round_num}:")
            parts.append(f"🔍 观察: {record['observe']}")
            parts.append(f"💭 思考: {record['think']}")
            parts.append(f"⚡ 执行: {actions}")

            # 显示该Round产出的Notes
            for note_id in record['notes_created']:
                parts.append(f"📝 @{note_id}: {note_preview}")

    # 2. Tactician分析结果
    if workspace.tactician_analysis:
        parts.append("[Tactician分析结果]")
        for strategy_id in strategy_notes:
            parts.append(f"@{strategy_id}: {content}")

    return "\n".join(parts)
```

### build_action_context()

为具体Action构建上下文：

```python
# context_builder.py 第368-441行
def build_action_context(step, workspace, conversation):
    parts = []

    # 1. 用户需求（部分Action需要）
    if step["action"] not in no_user_need_actions:
        parts.append("[用户需求]")
        parts.append(orchestrator_calls[0]['message'])

    # 2. 任务指令
    parts.append("[任务指令]")
    parts.append(step["instruction"])

    # 3. 展开@引用
    # 例如 @visual_concept1 → 实际内容
    refs = re.findall(r'@([a-zA-Z_]+\d+)', step["instruction"])
    for ref in refs:
        note_data = workspace.get_note(ref)
        if note_data:
            parts.append(f"@{ref}:")
            parts.append(note_data["content"])

    return "\n".join(parts)
```

### @引用替换机制

```python
# 在instruction中使用@引用
instruction = "基于@visual_concept1生成MJ提示词"

# 系统自动展开
# @visual_concept1 → [引用内容]
# Cyberpunk neon city at night, rain-slicked streets, ...
```

---

## Notes系统设计

### Note类型

| 类型 | 来源 | 说明 |
|------|------|------|
| `material` | Concierge | 用户上传的参考材料 |
| `subject_analysis` | Action | 主体分析结果 |
| `style_analysis` | Action | 风格分析结果 |
| `mood_analysis` | Action | 情绪分析结果 |
| `visual_concept` | Action | 视觉概念 |
| `midjourney_prompt` | Action | MJ提示词 |
| `strategy` | Tactician | 策略笔记 |

### Note生命周期

```python
# 1. 创建
note_id = workspace.create_note(
    note_type="midjourney_prompt",
    content="cyberpunk city, neon lights, rain...",
    source="step_1"
)

# 2. 更新评审状态
workspace.update_note_review_status(
    note_id="midjourney_prompt1",
    status="star",
    comment="高质量，可直接使用"
)

# 3. 查询
workspace.get_notes_by_type("midjourney_prompt")  # 按类型
workspace.get_notes_by_status("star")             # 按状态
workspace.get_referenceable_notes()               # 可引用的（排除trash）
```

### Note自动编号

```python
# workspace.py 第46-51行
def create_note(self, note_type, content, source):
    if note_type not in self._note_counters:
        self._note_counters[note_type] = 0

    self._note_counters[note_type] += 1
    note_id = f"{note_type}{self._note_counters[note_type]}"
    # 例如: midjourney_prompt1, midjourney_prompt2, ...
```

---

## 代码实现详解

### 完整的用户请求流程

```
1. 用户输入："帮我生成赛博朋克城市夜景的MJ提示词"

2. ImagePromptCLI.handle_user_input()
   ↓
3. Concierge.process_user_input()
   - conversation.add_user_message()
   - build_concierge_context()
   - call_llm(system_prompt=concierge_prompt, ...)
   - 检查响应是否包含 <call_orchestrator>
   - conversation.add_concierge_response()
   - 返回清理后的文本给用户

4. CLI检测到 orchestrator_call
   ↓
5. run_orchestrator_async()
   - 清空旧tactician_analysis（如果任务变化）
   - 启动后台线程

6. Tactician.analyze_task()  [首次执行]
   - build_tactician_context()
   - call_llm(system_prompt=tactician_prompt, ...)
   - 提取strategy_notes → workspace.tactician_analysis

7. Orchestrator.process_task()  [ReAct循环，最多3轮]
   - build_orchestrator_context()
   - call_llm(system_prompt=orchestrator_prompt, ...)
   - 提取 <execute action="xxx"> 命令
   - 执行每个命令 → execute()

8. execute(action_type, instruction)
   - 获取 ACTION_PROMPTS[action_type]
   - build_action_context()
   - call_llm(system_prompt, user_prompt)
   - extract_and_create_notes()
   - workspace.create_note()

9. 返回结果给用户
```

### 关键代码片段

#### Concierge的XML标签检测

```python
# concierge.py 第81-104行
def _extract_orchestrator_call(self, response: str) -> Optional[str]:
    # 1. 尝试完整标签对
    complete_pattern = r'<call_orchestrator>(.*?)</call_orchestrator>'
    match = re.search(complete_pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 2. 尝试不完整的标签（只有开始标签）
    incomplete_pattern = r'<call_orchestrator>(.*?)(?=<\w+|\n\n[^<]|$)'
    match = re.search(incomplete_pattern, response, re.DOTALL)
    if match:
        content = match.group(1).strip()
        if content and not content.startswith('<'):
            return content
    return None
```

#### Orchestrator的并行命令提取

```python
# orchestrator.py 第232-279行
def _extract_execute_commands(self, response: str) -> List[Dict[str, str]]:
    commands = []
    patterns = [
        # 标准格式
        r'<execute\s+action="([^"]+)"\s+instruction="([^"]+)"\s*/?>',
        # 无引号格式
        r'<execute\s+action=([^\s]+)\s+instruction=(.*?)(?=\s*/?>)',
        # 混合格式
        r'<execute\s+action="([^"]+)"\s+instruction=(.*?)(?=\s*/?>)',
    ]

    for i, pattern in enumerate(patterns):
        matches = list(re.finditer(pattern, response, re.DOTALL))
        if matches:
            for match in matches:
                commands.append({
                    "action": match.group(1).strip().strip('"'),
                    "instruction": match.group(2).strip().strip('"')
                })
            break
    return commands
```

#### execute()函数

```python
# orchestrator.py 第446-587行
def execute(action_type: str, instruction: str, workspace, conversation) -> Dict:
    # 1. 获取Action的Prompt模板
    system_prompt = ACTION_PROMPTS[action_type]

    # 2. 构建Action上下文
    step = {"action": action_type, "instruction": instruction}
    user_prompt = build_action_context(step, workspace, conversation)

    # 3. 特殊处理
    if action_type == "image_to_prompt":
        # 图片输入处理
        output = kimi_provider.call_llm_with_image(...)
    elif action_type == "websearch":
        # 启用web搜索
        output = kimi_provider.call_llm(..., enable_websearch=True)
    else:
        # 普通调用
        output = call_llm(system_prompt, user_prompt, temperature, ...)

    # 4. 提取Notes
    notes_created = extract_and_create_notes(output, step_id, workspace)

    return {
        "success": True,
        "output": output,
        "notes_created": notes_created
    }
```

---

## 如何开发新的Agent

### 步骤1：定义Agent的System Prompt

在`prompts/`目录下创建新的prompt文件：

```python
# prompts/my_agent_prompt.py
my_agent_prompt = """
你是MyAgent，一个负责[具体职责]的Agent。

# 你的能力
- 你可以执行XXX操作
- 你可以分析XXX内容

# 输出格式
当需要执行操作时，使用以下标签：
<my_action param1="value1" param2="value2">
这是操作说明
</my_action>

当任务完成时，使用：
<my_complete>
任务已完成，结论：...
</my_complete>
"""
```

### 步骤2：创建Agent类

```python
# agents/my_agent.py
from model_base import call_llm

class MyAgent:
    def __init__(self, workspace, conversation):
        self.workspace = workspace
        self.conversation = conversation
        self.system_prompt = my_agent_prompt

    def process_task(self, task_message: str) -> Dict:
        # 1. 构建上下文
        context = build_my_agent_context(task_message, self.workspace)

        # 2. 调用LLM
        response = call_llm(
            system_prompt=self.system_prompt,
            user_prompt=context,
            temperature=0.3
        )

        # 3. 解析响应
        actions = self._extract_actions(response)

        # 4. 执行动作
        results = []
        for action in actions:
            result = self._execute_action(action)
            results.append(result)

        # 5. 返回结果
        return {
            "completed": self._is_completed(response),
            "actions": actions,
            "results": results
        }

    def _extract_actions(self, response: str) -> List[Dict]:
        # 解析 <my_action> 标签
        ...

    def _execute_action(self, action: Dict) -> Any:
        # 执行具体动作
        ...
```

### 步骤3：注册到CLI

```python
# ImagePrompt.py
from agents.my_agent import MyAgent

class ImagePromptCLI:
    def __init__(self):
        # ...
        self.my_agent = MyAgent(self.workspace, self.conversation)
```

---

## 如何开发新的Action

### 步骤1：添加Action Prompt

在`prompts/action_prompts.py`中定义：

```python
ACTION_PROMPTS = {
    # ... 现有actions

    # 新Action
    "my_new_action": """
你是MyNewAction，一个负责[具体职责]的Action。

## 输入
你会收到一个[任务指令]，需要按照要求执行。

## 输出要求
请生成[具体内容]，包含：
1. [要素1]
2. [要素2]
3. [要素3]

## 格式
输出必须包含<result>标签：
<result>
这是你的输出内容...
</result>
""",
}
```

### 步骤2：在notes_extractor.py中添加提取规则

```python
# core/notes_extractor.py
def extract_and_create_notes(output: str, step_id: str, workspace, expected_types=None):
    notes_created = []

    # 新Action的提取规则
    if expected_types and "my_new_action" in expected_types:
        result_match = re.search(r'<result>(.*?)</result>', output, re.DOTALL)
        if result_match:
            note_id = workspace.create_note(
                note_type="my_new_action",
                content=result_match.group(1).strip(),
                source=step_id
            )
            notes_created.append(note_id)

    return notes_created
```

### 步骤3：在execute()中添加特殊处理（可选）

```python
# orchestrator.py execute()函数
if action_type == "my_new_action":
    # 特殊处理逻辑
    output = my_special_processing(instruction, workspace)
    # ...
```

---

## 架构设计总结

### 核心理念

1. **LLM作为Agent的核心大脑**：每个Agent通过System Prompt定义其行为模式
2. **结构化输出**：通过XML标签实现Agent与系统、Agent与Agent之间的通信
3. **上下文注入**：每个请求都携带完整的上下文，包括历史、状态、参考资料
4. **Notes作为共享知识**：所有Agent通过Notes系统共享中间结果
5. **ReAct循环**：Orchestrator通过推理-行动循环完成复杂任务

### 设计模式

| 模式 | 应用场景 |
|------|----------|
| Prompt-Driven | 所有Agent的System Prompt定义 |
| Context Injection | build_xxx_context() 构建上下文 |
| XML Tag Protocol | Agent间通信指令 |
| ReAct Loop | Orchestrator执行循环 |
| Shared Knowledge Base | WorkSpace.notes |
| State Machine | ConversationManager状态管理 |

### 扩展点

1. **新Agent**：创建Agent类 + 定义Prompt + 注册到CLI
2. **新Action**：添加Prompt + 添加提取规则
3. **新数据存储**：扩展WorkSpace或ConversationManager
4. **新通信协议**：定义新的XML标签格式

---

## 参考资料

- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)

