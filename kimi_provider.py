#!/usr/bin/env python3
"""
Kimi K2.5 模型提供商
支持kimi-k2.5系列模型，兼容OpenAI格式API，支持多模态（图片输入）
"""

import os
import json
import base64
import logging
from typing import Optional, Dict, Any
from openai import OpenAI

from model_base import ModelProvider, identify_prompt_type, create_llm_panel, update_session_stats

# 配置日志
logger = logging.getLogger(__name__)

# 配置常量
BASE_URL = "https://api.moonshot.cn/v1"
API_KEY = os.environ.get("KIMI_API_KEY", "")
MODEL_NAME = "kimi-k2.5"

if not API_KEY:
    raise ValueError("请设置环境变量 KIMI_API_KEY")

# 费用计算常量 (人民币价格，需要转换为美元)
COST_INPUT_PER_1M_RMB = 4.0    # 4元/1M tokens
COST_OUTPUT_PER_1M_RMB = 16.0  # 16元/1M tokens
WEBSEARCH_COST_RMB = 0.03      # 0.03元/次
RMB_TO_USD_RATE = 7.0          # 假设汇率


class KimiProvider(ModelProvider):
    """Kimi K2.5 模型提供商"""

    def __init__(self):
        self._client = None

    @property
    def name(self) -> str:
        return "kimi-k2.5"

    @property
    def display_name(self) -> str:
        return "Kimi-K2.5"

    def calculate_cost(self, input_tokens: int, output_tokens: int, thinking_tokens: int = 0, websearch_calls: int = 0) -> float:
        """计算API调用费用（转换为美元）"""
        input_cost_rmb = (input_tokens / 1_000_000) * COST_INPUT_PER_1M_RMB
        output_cost_rmb = ((output_tokens + thinking_tokens) / 1_000_000) * COST_OUTPUT_PER_1M_RMB
        websearch_cost_rmb = websearch_calls * WEBSEARCH_COST_RMB

        total_cost_rmb = input_cost_rmb + output_cost_rmb + websearch_cost_rmb

        return total_cost_rmb / RMB_TO_USD_RATE

    def _initialize_client(self):
        """初始化OpenAI客户端"""
        if self._client is None:
            try:
                self._client = OpenAI(
                    base_url=BASE_URL,
                    api_key=API_KEY
                )
            except Exception as e:
                logger.error(f"❌ Kimi客户端初始化失败: {e}")
                raise
        return self._client

    def _encode_image(self, image_path: str) -> str:
        """将图片编码为base64字符串"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _get_image_media_type(self, image_path: str) -> str:
        """根据文件扩展名获取图片媒体类型"""
        ext = os.path.splitext(image_path)[1].lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        return media_types.get(ext, "image/jpeg")

    def call_llm(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        调用Kimi生成内容

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            **kwargs: 其他生成参数
                - max_output_tokens: 最大输出token数 (默认: 8000)
                - temperature: 温度参数 (默认: 0.8)
                - enable_websearch: 是否启用web搜索 (默认: False)

        Returns:
            生成的文本内容
        """
        try:
            prompt_type = identify_prompt_type(system_prompt)
            client = self._initialize_client()
            processed_user_prompt = self.process_text(user_prompt)

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": processed_user_prompt}
            ]

            generation_config = {
                "model": MODEL_NAME,
                "messages": messages,
                "max_tokens": kwargs.get("max_output_tokens", 8000),
                "temperature": 1.0,
                "top_p": kwargs.get("top_p", 0.95),
            }

            enable_websearch = kwargs.get("enable_websearch", False)
            websearch_calls = 0

            if enable_websearch:
                generation_config["tools"] = [
                    {
                        "type": "builtin_function",
                        "function": {
                            "name": "$web_search",
                        },
                    }
                ]

            finish_reason = None
            while finish_reason is None or finish_reason == "tool_calls":
                completion = client.chat.completions.create(**generation_config)
                choice = completion.choices[0]
                finish_reason = choice.finish_reason

                if finish_reason == "tool_calls":
                    messages.append(choice.message)

                    for tool_call in choice.message.tool_calls:
                        tool_call_name = tool_call.function.name
                        tool_call_arguments = json.loads(tool_call.function.arguments)

                        if tool_call_name == "$web_search":
                            websearch_calls += 1
                            tool_result = tool_call_arguments
                            logger.info(f"🔍 执行web搜索，消耗tokens: {tool_call_arguments.get('usage', {}).get('total_tokens', 0)}")
                        else:
                            tool_result = f"Error: unable to find tool by name '{tool_call_name}'"

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_call_name,
                            "content": json.dumps(tool_result),
                        })

                    generation_config["messages"] = messages
                else:
                    result_text = choice.message.content
                    break

            result_text = self.process_text(result_text)

            usage = completion.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            thinking_tokens = 0

            call_cost = self.calculate_cost(input_tokens, output_tokens, thinking_tokens, websearch_calls)

            update_session_stats(input_tokens, output_tokens, thinking_tokens, call_cost)

            from model_base import get_session_stats
            session_stats = get_session_stats()

            create_llm_panel(
                prompt_type,
                processed_user_prompt,
                result_text,
                input_tokens,
                output_tokens,
                thinking_tokens,
                call_cost,
                session_stats["total_cost"]
            )

            return result_text

        except Exception as e:
            logger.error(f"❌ Kimi调用失败: {e}")
            raise

    def call_llm_with_image(self, system_prompt: str, image_path: str, user_prompt: str = "", **kwargs) -> str:
        """
        调用Kimi生成内容（支持图片输入）

        Args:
            system_prompt: 系统提示词
            image_path: 图片路径
            user_prompt: 附加的文本输入（可选）
            **kwargs: 其他生成参数
                - max_output_tokens: 最大输出token数 (默认: 8000)

        Returns:
            生成的文本内容
        """
        try:
            prompt_type = identify_prompt_type(system_prompt)
            client = self._initialize_client()

            # 编码图片
            image_base64 = self._encode_image(image_path)
            media_type = self._get_image_media_type(image_path)

            # 构建多模态消息
            content = [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{image_base64}"
                    }
                }
            ]

            # 如果有文本输入，添加文本部分
            if user_prompt:
                processed_text = self.process_text(user_prompt)
                content.append({
                    "type": "text",
                    "text": processed_text
                })

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ]

            generation_config = {
                "model": MODEL_NAME,
                "messages": messages,
                "max_tokens": kwargs.get("max_output_tokens", 8000),
                "temperature": 1.0,
                "top_p": kwargs.get("top_p", 0.95),
            }

            completion = client.chat.completions.create(**generation_config)
            choice = completion.choices[0]
            result_text = choice.message.content

            result_text = self.process_text(result_text)

            usage = completion.usage
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            thinking_tokens = 0

            call_cost = self.calculate_cost(input_tokens, output_tokens, thinking_tokens, 0)

            update_session_stats(input_tokens, output_tokens, thinking_tokens, call_cost)

            from model_base import get_session_stats
            session_stats = get_session_stats()

            create_llm_panel(
                prompt_type,
                f"[图片: {os.path.basename(image_path)}] {user_prompt}",
                result_text,
                input_tokens,
                output_tokens,
                thinking_tokens,
                call_cost,
                session_stats["total_cost"]
            )

            return result_text

        except Exception as e:
            logger.error(f"❌ Kimi图片分析失败: {e}")
            raise


def test_kimi_provider():
    """测试Kimi提供商"""
    print("🧪 测试Kimi Provider")
    print("=" * 40)
    
    provider = KimiProvider()
    system_prompt = "你是一个专业的AI助手，请用简洁明了的方式回答问题。"
    user_prompt = "披萨是什么？"
    
    try:
        result = provider.call_llm(system_prompt, user_prompt)
        print(f"✅ 调用成功!")
        print(f"模型名称: {provider.display_name}")
        print(f"系统提示词: {system_prompt}")
        print(f"用户输入: {user_prompt}")
        print(f"回答: {result}")
        
        # 测试websearch功能
        print("\n" + "=" * 40)
        print("🔍 测试websearch功能")
        
        websearch_result = provider.call_llm(
            system_prompt,
            "请搜索最新的人工智能发展动态",
            enable_websearch=True
        )
        print(f"✅ websearch调用成功!")
        print(f"搜索结果: {websearch_result}")
        
    except Exception as e:
        print(f"❌ 调用失败: {e}")


if __name__ == "__main__":
    test_kimi_provider() 