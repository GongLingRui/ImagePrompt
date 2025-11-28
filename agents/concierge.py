"""
Concierge Agent
前台接待，负责与用户直接对话，理解需求并路由任务
"""

import re
import logging
from typing import Optional, Dict, Any, List, Tuple
from prompts.concierge_prompt import concierge_prompt
from core.context_builder import build_concierge_context
from model_base import call_llm

logger = logging.getLogger(__name__)


class Concierge:
    """前台接待Agent - 简化版"""
    
    def __init__(self, workspace, conversation):
        self.workspace = workspace
        self.conversation = conversation
        self.system_prompt = concierge_prompt
    
    def process_user_input(self, user_input: str) -> str:
        """
        处理用户输入，返回Concierge的响应
        
        简化版：所有输入都统一处理，让LLM智能理解意图
        """
        # 记录用户消息
        notes_created = []
        
        # 记录到对话历史
        self.conversation.add_user_message(user_input, notes_created)
        
        # 2. 构建上下文并调用LLM
        context = build_concierge_context(user_input, self.workspace, self.conversation)
        
        try:
            # 使用用户选择的LLM模型（与Orchestrator保持一致）
            response = call_llm(
                system_prompt=self.system_prompt,
                user_prompt=context,
                temperature=0.4,
                max_output_tokens=4000
            )
            
            # 3. 解析响应
            orchestrator_call = self._extract_orchestrator_call(response)
            save_material_commands = self._extract_save_material(response)
            
            # 4. 执行save_material命令
            if save_material_commands:
                for user_id, content in save_material_commands:
                    # 创建material类型的note，忽略用户提供的ID
                    note_id = self.workspace.create_note("material", content, "concierge")
                    notes_created.append(note_id)
                    # 在响应中替换占位符，显示实际创建的ID
                    # 使用正则表达式替换，因为格式可能有变化
                    pattern = rf'<save_material>\s*<id>{re.escape(user_id)}</id>\s*<content>{re.escape(content)}</content>\s*</save_material>'
                    response = re.sub(pattern, f"[已保存为 @{note_id}]", response, flags=re.DOTALL)
            
            # 5. 清理响应文本
            clean_response = self._clean_response(response)
            
            # 6. 记录响应和可能的orchestrator调用
            self.conversation.add_concierge_response(clean_response, orchestrator_call, original_response=response)
            
            # 7. 处理orchestrator调用
            if orchestrator_call:
                logger.info("检测到需要调用Orchestrator")
                # 调用已经被记录到conversation中
                # CLI层会根据orchestrator状态决定如何处理
            
            return clean_response
            
        except Exception as e:
            logger.error(f"Concierge处理失败: {str(e)}")
            return f"抱歉，处理您的请求时出现错误：{str(e)}"
    
    def _extract_orchestrator_call(self, response: str) -> Optional[str]:
        """提取orchestrator调用 - 增强版，可处理不完整的XML标签"""
        # 首先尝试匹配完整的XML标签对
        complete_pattern = r'<call_orchestrator>(.*?)</call_orchestrator>'
        match = re.search(complete_pattern, response, re.DOTALL)
        if match:
            content = match.group(1).strip()
            return content if content else None
        
        # 如果没有找到完整的标签对，尝试匹配只有开始标签的情况
        incomplete_pattern = r'<call_orchestrator>(.*?)(?=<\w+|\n\n[^<]|$)'
        match = re.search(incomplete_pattern, response, re.DOTALL)
        if match:
            content = match.group(1).strip()
            # 确保内容不为空且不是其他XML标签
            if content and not content.startswith('<'):
                # 进一步清理：移除可能的AI回复语句
                content = re.sub(r'\n\n.*?(?:我会|开始|执行).*$', '', content, flags=re.DOTALL)
                content = content.strip()
                if content:
                    logger.warning("检测到不完整的call_orchestrator标签，已自动修复")
                    return content
        
        return None
    
    def _extract_save_material(self, response: str) -> List[Tuple[str, str]]:
        """提取save_material命令"""
        materials = []
        pattern = r'<save_material>\s*<id>(\d+)</id>\s*<content>(.*?)</content>\s*</save_material>'
        for match in re.finditer(pattern, response, re.DOTALL):
            user_id = match.group(1)
            content = match.group(2).strip()
            materials.append((user_id, content))
        return materials
    
    def _clean_response(self, response: str) -> str:
        """清理响应文本，移除XML标签"""
        # 移除各种命令标签
        patterns = [
            r'<call_orchestrator>.*?</call_orchestrator>',
            r'<save_material>.*?</save_material>'
        ]
        
        clean = response
        for pattern in patterns:
            clean = re.sub(pattern, '', clean, flags=re.DOTALL)
        
        # 清理多余的空行
        clean = re.sub(r'\n{3,}', '\n\n', clean)
        
        return clean.strip() 
    