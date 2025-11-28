# ImagePrompt - AI图像提示词生成系统

基于多Agent架构的智能图像提示词生成系统，支持从文本描述或图片反向推导AI图像生成提示词。

## 功能特性

### 核心功能

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
