"""
Tactician Agent
图像创作策略分析师，负责在生成提示词前进行深度策略分析
"""

import logging
from typing import List, Optional
from prompts.tactician_prompt import tactician_prompt
from core.context_builder import build_tactician_context
from core.notes_extractor import extract_and_create_notes
from model_base import call_llm

logger = logging.getLogger(__name__)


class Tactician:
    """图像创作策略分析师Agent"""

    def __init__(self, workspace, conversation):
        self.workspace = workspace
        self.conversation = conversation
        self.system_prompt = tactician_prompt

    def analyze_task(self, user_message: str) -> bool:
        """
        分析用户创作需求，生成策略性笔记

        Args:
            user_message: 用户的图像创作需求

        Returns:
            bool: 是否成功完成分析
        """
        try:
            logger.info("开始Tactician策略分析...")

            # 构建上下文
            context = build_tactician_context(user_message, self.workspace, self.conversation)

            # 调用用户选择的LLM进行分析
            response = call_llm(
                system_prompt=self.system_prompt,
                user_prompt=context,
                temperature=0.3,
                max_output_tokens=4000
            )

            # 提取strategy并创建为Notes
            strategy_notes = extract_and_create_notes(
                response,
                "tactician_analysis",
                self.workspace,
                expected_types=['strategy']
            )

            if not strategy_notes:
                logger.warning("Tactician分析未产生有效策略")
                return False

            # 更新workspace analysis记录
            self.workspace.set_tactician_analysis({
                'strategy_notes': strategy_notes,
                'raw_response': response,
                'user_message': user_message
            })

            logger.info(f"Tactician分析完成: {len(strategy_notes)} 个策略Notes")
            return True

        except Exception as e:
            logger.error(f"Tactician分析失败: {e}")
            return False
    

    
 