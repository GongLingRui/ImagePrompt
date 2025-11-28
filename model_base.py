#!/usr/bin/env python3
"""
统一模型调用接口
作为ImagePrompt系统的模型抽象层

支持多种模型提供商：
- Gemini 2.5 Pro
- Doubao-Seed-1.6-thinking
- 未来可扩展更多模型
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# 导入所有prompts
from prompts.concierge_prompt import concierge_prompt
from prompts.orchestrator_prompt import orchestrator_prompt
from prompts.action_prompts import ACTION_PROMPTS

# 配置日志
logger = logging.getLogger(__name__)

# Rich console
console = Console()

# 全局会话统计
_session_stats = {
    "total_calls": 0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_thinking_tokens": 0,
    "total_cost": 0.0
}

def get_session_stats():
    """获取当前会话的token使用统计"""
    return _session_stats.copy()

def reset_session_stats():
    """重置会话统计"""
    global _session_stats
    _session_stats = {
        "total_calls": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_thinking_tokens": 0,
        "total_cost": 0.0
    }

def remove_chinese_quotes(text: str) -> str:
    """
    去掉中文双引号，例如将"生育惩罚"变成生育惩罚
    
    Args:
        text: 需要处理的文本
        
    Returns:
        处理后的文本
    """
    # 使用正则表达式去掉中文双引号
    # 匹配中文双引号及其内容，只保留内容
    text = re.sub(r'"([^"]*)"', r'\1', text)
    return text

def identify_prompt_type(system_prompt: str) -> str:
    """识别prompt类型"""
    if system_prompt == concierge_prompt:
        return "Concierge"
    elif system_prompt == orchestrator_prompt:
        return "Orchestrator"
    else:
        # 检查是否是action prompt
        for action_name, action_prompt in ACTION_PROMPTS.items():
            if system_prompt == action_prompt:
                return f"Action: {action_name}"
        return "Unknown"

def create_llm_panel(
    prompt_type: str,
    user_prompt: str,
    response: str,
    input_tokens: int,
    output_tokens: int,
    thinking_tokens: int,
    call_cost: float,
    total_cost: float
) -> None:
    """创建并显示LLM调用面板"""
    # 创建面板内容
    panel_content = Text()
    panel_content.append(f"🤖 {prompt_type}\n", style="bold cyan")
    panel_content.append("─" * 80 + "\n", style="dim")
    panel_content.append("📥 User Prompt:\n", style="bold yellow")
    panel_content.append(user_prompt + "\n", style="white")
    panel_content.append("─" * 80 + "\n", style="dim")
    
    # 如果有thinking tokens，显示thinking提示
    if thinking_tokens > 0:
        panel_content.append("🧠 Model Thinking:\n", style="bold magenta")
        panel_content.append(f"模型进行了深度思考（{thinking_tokens:,} thinking tokens）\n", style="dim cyan")
        panel_content.append("💡 虽然API不再返回thinking内容，但模型已充分思考问题\n", style="dim")
        panel_content.append("─" * 80 + "\n", style="dim")
    
    panel_content.append("📤 LLM Response:\n", style="bold green")
    panel_content.append(response, style="bright_green")
    
    # 添加统计信息
    user_prompt_lines = user_prompt.split('\n')
    response_lines = response.split('\n')
    char_stats = f"Input: {len(user_prompt)} chars, {len(user_prompt_lines)} lines | Output: {len(response)} chars, {len(response_lines)} lines"
    
    # 构建token统计信息
    total_tokens = input_tokens + output_tokens + thinking_tokens
    if thinking_tokens > 0:
        token_stats = f"Tokens: {input_tokens:,} in + {output_tokens:,} out + {thinking_tokens:,} thinking = {total_tokens:,} total"
    else:
        token_stats = f"Tokens: {input_tokens:,} in + {output_tokens:,} out = {total_tokens:,} total"
    
    cost_stats = f"Cost: ${call_cost:.4f} (${total_cost:.4f} session)"
    
    # 在面板内容末尾添加费用信息
    panel_content.append("\n" + "─" * 80 + "\n", style="dim")
    panel_content.append("💰 ", style="yellow")
    panel_content.append(f"{token_stats} | {cost_stats}", style="dim")
    
    # 显示详细的面板
    console.print("\n")  # 添加空行
    console.print(Panel(
        panel_content,
        title=f"[bold]LLM Call[/bold] - [dim]{char_stats}[/dim]",
        border_style="bright_cyan",
        padding=(1, 2),
        expand=True
    ))
    console.print("\n")  # 添加空行

def update_session_stats(input_tokens: int, output_tokens: int, thinking_tokens: int, cost: float):
    """更新会话统计"""
    global _session_stats
    _session_stats["total_calls"] += 1
    _session_stats["total_input_tokens"] += input_tokens
    _session_stats["total_output_tokens"] += output_tokens
    _session_stats["total_thinking_tokens"] += thinking_tokens
    _session_stats["total_cost"] += cost


class ModelProvider(ABC):
    """模型提供商抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """模型名称"""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """显示名称"""
        pass
    
    @abstractmethod
    def calculate_cost(self, input_tokens: int, output_tokens: int, thinking_tokens: int = 0, **kwargs) -> float:
        """计算API调用费用"""
        pass
    
    @abstractmethod
    def call_llm(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """调用LLM生成内容"""
        pass
    
    def process_text(self, text: str) -> str:
        """处理文本（默认去掉中文双引号）"""
        return remove_chinese_quotes(text)


class ModelManager:
    """模型管理器"""
    
    def __init__(self):
        self._providers: Dict[str, ModelProvider] = {}
        self._current_provider: Optional[ModelProvider] = None
    
    def register_provider(self, provider: ModelProvider):
        """注册模型提供商"""
        self._providers[provider.name] = provider
        # logger.info(f"✅ 注册模型提供商: {provider.display_name}")
    
    def set_current_provider(self, name: str):
        """设置当前使用的模型"""
        if name not in self._providers:
            raise ValueError(f"未找到模型提供商: {name}")
        self._current_provider = self._providers[name]
        logger.info(f"🔄 切换到模型: {self._current_provider.display_name}")
    
    def get_current_provider(self) -> Optional[ModelProvider]:
        """获取当前模型提供商"""
        return self._current_provider
    
    def list_providers(self) -> List[str]:
        """列出所有可用的模型提供商"""
        return list(self._providers.keys())
    
    def get_provider_display_names(self) -> Dict[str, str]:
        """获取所有提供商的显示名称映射"""
        return {name: provider.display_name for name, provider in self._providers.items()}
    
    def call_current_model(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """使用当前模型调用LLM"""
        if not self._current_provider:
            raise ValueError("未设置当前模型提供商")
        
        return self._current_provider.call_llm(system_prompt, user_prompt, **kwargs)


# 全局模型管理器实例
model_manager = ModelManager()

def call_llm(system_prompt: str, user_prompt: str, **kwargs) -> str:
    """
    统一的LLM调用接口
    
    Args:
        system_prompt: 系统提示词
        user_prompt: 用户输入
        **kwargs: 其他生成参数
        
    Returns:
        生成的文本内容
        
    Raises:
        ValueError: 未设置模型提供商时抛出
        Exception: 调用失败时抛出异常
    """
    return model_manager.call_current_model(system_prompt, user_prompt, **kwargs)

def get_available_models() -> Dict[str, str]:
    """获取所有可用模型的显示名称"""
    return model_manager.get_provider_display_names()

def set_current_model(model_name: str):
    """设置当前使用的模型"""
    model_manager.set_current_provider(model_name)

def get_current_model_name() -> Optional[str]:
    """获取当前模型名称"""
    provider = model_manager.get_current_provider()
    return provider.display_name if provider else None

def call_llm_with_image(system_prompt: str, image_path: str, user_prompt: str = "", **kwargs) -> str:
    """
    统一的图片输入LLM调用接口

    Args:
        system_prompt: 系统提示词
        image_path: 图片路径
        user_prompt: 附加的文本输入（可选）
        **kwargs: 其他生成参数

    Returns:
        生成的文本内容

    Raises:
        ValueError: 未设置模型提供商时抛出
        Exception: 调用失败时抛出异常
    """
    provider = model_manager.get_current_provider()
    if not provider:
        raise ValueError("未设置当前模型提供商")

    if not hasattr(provider, 'call_llm_with_image'):
        raise ValueError(f"当前模型 {provider.display_name} 不支持图片输入")

    return provider.call_llm_with_image(system_prompt, image_path, user_prompt, **kwargs)