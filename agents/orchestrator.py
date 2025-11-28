"""
Orchestrator Agent
任务编排，负责理解需求并指挥执行
"""

import re
import logging
from typing import Dict, Any, Optional, List
from prompts.orchestrator_prompt import orchestrator_prompt # , reflection_prompt  # 注释掉reflection
from core.context_builder import build_orchestrator_context # , build_reflection_context  # 注释掉reflection
from model_base import call_llm

logger = logging.getLogger(__name__)


class Orchestrator:
    """任务编排Agent - 无状态版本"""
    
    def __init__(self, workspace, conversation, log_callback=None):
        self.workspace = workspace
        self.conversation = conversation
        self.system_prompt = orchestrator_prompt
        self.log_callback = log_callback
    
    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message, level)
    
    def process_task(self, task_message: str, execution_log: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        处理任务（单次调用）
        
        Args:
            task_message: 当前任务消息
            execution_log: 执行历史（用于构建step_done）
            
        Returns:
            包含本次处理结果的字典
        """
        # 构建上下文
        context = build_orchestrator_context(
            task_message,
            self.workspace,
            self.conversation,
            execution_log=execution_log or []
        )
        
        # 调用LLM
        # self._log("调用LLM处理任务...")
        response = call_llm(
            system_prompt=self.system_prompt,
            user_prompt=context,
            temperature=0.5,
            max_output_tokens=4000
        )
        
        # 记录响应
        self.conversation.add_orchestrator_response(response)
        
        # 解析响应
        result = {
            "response": response,
            # "tactics": None,
            "execute_commands": [],
            "completed": False
        }
        
        # 提取execute命令
        execute_commands = self._extract_execute_commands(response)
        result["execute_commands"] = execute_commands
        
        # 提取tactics（可能为空）
        # tactics = self._extract_tactics(response)
        # result["tactics"] = tactics
        
        # 提取observe和think内容
        observe = self._extract_observe(response)
        think = self._extract_think(response)
        
        # 记录所有会被执行的命令
        if len(execute_commands) > 1:
            actions = [cmd["action"] for cmd in execute_commands]
            self._log(f"✅ 检测到多个execute命令，将依次执行: {', '.join(actions)}")
        
        # 记录执行信息（不包含tactics）
        self._record_execution(execute_commands, observe, think)
        
        # 检查是否标记完成
        if '<ORCHESTRATOR_DECLARATION>' in response:
            result["completed"] = True
            self._log("检测到Orchestrator工作流程终止声明", "success")
        
        return result
    
    def _record_execution(self, execute_commands: List[Dict[str, str]], observe: Optional[str] = None, think: Optional[str] = None) -> None:
        """
        记录执行信息到ConversationManager（不包含tactics）
        """
        # 获取当前轮次
        current_round = self._get_current_round()
        
        # 构建本轮的执行记录
        round_entry = f"Round{current_round}: "
        
        # 添加执行的action信息
        if execute_commands:
            actions = [f'"{cmd["action"]}"' for cmd in execute_commands]
            if len(actions) == 1:
                round_entry += f"executed {actions[0]}."
            else:
                round_entry += f"executed {', '.join(actions)}."
        else:
            round_entry += "thinking."
        
        # 记录到ConversationManager
        self.conversation.add_execution_record(round_entry, observe=observe, think=think)
    
    def _get_current_round(self) -> int:
        """获取当前轮次号"""
        # 从ConversationManager获取当前轮次
        if hasattr(self.conversation, '_orchestrator_calls') and self.conversation._orchestrator_calls:
            current_call = self.conversation._orchestrator_calls[-1]
            if 'execution_records' in current_call:
                return len(current_call['execution_records']) + 1
        return 1
    
    # def _append_tactics(self, tactics: str, execute_commands: List[Dict[str, str]], observe: Optional[str] = None, think: Optional[str] = None) -> None:
    #     """
    #     累计保存tactics，格式：Round1: executed "action". memo: xxx
    #     """
    #     # 获取当前轮次
    #     current_round = self._get_current_round()
    #     
    #     # 构建本轮的tactics条目
    #     round_entry = f"Round{current_round}: "
    #     
    #     # 添加执行的action信息
    #     if execute_commands:
    #         actions = [f'"{cmd["action"]}"' for cmd in execute_commands]
    #         if len(actions) == 1:
    #             round_entry += f"executed {actions[0]}. "
    #         else:
    #             round_entry += f"executed {', '.join(actions)}. "
    #     else:
    #         round_entry += "thinking. "
    #     
    #     # 添加memo
    #     round_entry += f"memo: {tactics}"
    #     
    #     # 累计到workspace.tactics
    #     if hasattr(self.workspace, 'tactics') and self.workspace.tactics:
    #         self.workspace.tactics += f"\n{round_entry}"
    #     else:
    #         self.workspace.tactics = round_entry
    #     
    #     # 同时记录到ConversationManager，确保执行记录与orchestrator调用关联
    #     # 传递observe和think信息
    #     self.conversation.add_execution_record(round_entry, observe=observe, think=think)
    
    # def _get_current_round(self) -> int:
    #     """获取当前轮次号"""
    #     if not hasattr(self.workspace, 'tactics') or not self.workspace.tactics:
    #         return 1
    #     
    #     # 统计已有的Round条目
    #     import re
    #     rounds = re.findall(r'Round(\d+):', self.workspace.tactics)
    #     if rounds:
    #         return max(int(r) for r in rounds) + 1
    #     else:
    #         return 1
    
    # def _extract_tactics(self, response: str) -> Optional[str]:
    #     """提取tactics内容 - 增强版，支持不完整标签"""
    #     # 1. 尝试完整的标签匹配
    #     complete_pattern = r'<tactics>(.*?)</tactics>'
    #     match = re.search(complete_pattern, response, re.DOTALL)
    #     if match:
    #         return match.group(1).strip()
    #     
    #     # 2. 尝试不完整的标签匹配（只有开始标签）
    #     incomplete_pattern = r'<tactics>(.*?)(?=<\w+|$)'
    #     match = re.search(incomplete_pattern, response, re.DOTALL)
    #     if match:
    #         content = match.group(1).strip()
    #         if content:
    #             logger.warning("⚠️  检测到不完整的tactics标签，已自动修复")
    #             return content
    #     
    #     return None
    
    def _extract_observe(self, response: str) -> Optional[str]:
        """提取observe内容 - 增强版，支持不完整标签"""
        # 1. 尝试完整的标签匹配
        complete_pattern = r'<observe>(.*?)</observe>'
        match = re.search(complete_pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 2. 尝试不完整的标签匹配（只有开始标签）
        incomplete_pattern = r'<observe>(.*?)(?=<\w+|$)'
        match = re.search(incomplete_pattern, response, re.DOTALL)
        if match:
            content = match.group(1).strip()
            if content:
                logger.warning("⚠️  检测到不完整的observe标签，已自动修复")
                return content
        
        return None
    
    def _extract_think(self, response: str) -> Optional[str]:
        """提取think内容 - 增强版，支持不完整标签"""
        # 1. 尝试完整的标签匹配
        complete_pattern = r'<think>(.*?)</think>'
        match = re.search(complete_pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 2. 尝试不完整的标签匹配（只有开始标签）
        incomplete_pattern = r'<think>(.*?)(?=<\w+|$)'
        match = re.search(incomplete_pattern, response, re.DOTALL)
        if match:
            content = match.group(1).strip()
            if content:
                logger.warning("⚠️  检测到不完整的think标签，已自动修复")
                return content
        
        return None
    
    def _extract_execute_commands(self, response: str) -> List[Dict[str, str]]:
        """提取execute命令 - 支持多种格式"""
        commands = []
        
        # 尝试多种格式的正则表达式
        patterns = [
            # 标准格式：有双引号
            r'<execute\s+action="([^"]+)"\s+instruction="([^"]+)"\s*/?>',
            # 无双引号格式：修复版，使用正向先行断言正确匹配到结尾标签
            r'<execute\s+action=([^\s]+)\s+instruction=(.*?)(?=\s*/?>)',
            # 混合格式：一个有引号一个没有
            r'<execute\s+action="([^"]+)"\s+instruction=(.*?)(?=\s*/?>)',
            r'<execute\s+action=([^\s]+)\s+instruction="([^"]+)"\s*/?>',
        ]
        
        for i, pattern in enumerate(patterns):
            matches = list(re.finditer(pattern, response, re.DOTALL))
            if matches:
                logger.info(f"✅ 使用模式 {i+1} 成功提取到 {len(matches)} 个execute命令")
                for match in matches:
                    action = match.group(1).strip().strip('"')  # 去掉可能的双引号
                    instruction = match.group(2).strip().strip('"')  # 去掉可能的双引号
                    logger.info(f"📋 提取到命令: action={action}, instruction={instruction[:50]}...")
                    commands.append({
                        "action": action,
                        "instruction": instruction
                    })
                # 找到匹配就停止尝试其他格式
                break
        
        if not commands:
            logger.warning("⚠️  未能提取到任何execute命令")
            # 显示原始响应以便调试
            logger.debug(f"原始响应: {response}")
            
            # 尝试找到execute标签的存在
            if '<execute' in response:
                logger.warning("检测到execute标签存在，但无法正确解析")
                # 显示execute标签附近的内容
                execute_matches = re.finditer(r'<execute[^>]*>', response, re.DOTALL)
                for match in execute_matches:
                    start = max(0, match.start() - 50)
                    end = min(len(response), match.end() + 200)
                    logger.warning(f"发现execute标签: {response[start:end]}")
            else:
                logger.warning("响应中未找到execute标签")
        
        return commands

    # 注释掉reflection_step方法
    # def reflection_step(self, action_notes: List[str], action_type: str, user_task: str) -> Dict[str, Any]:
    #     """
    #     对单个Action产出的Notes进行反思评审
    #     
    #     Args:
    #         action_notes: 单个Action创建的note IDs列表
    #         action_type: Action类型
    #         user_task: 用户任务
    #         
    #     Returns:
    #         反思结果
    #     """
    #     if not action_notes:
    #         logger.info(f"Action [{action_type}] 无Notes产出，跳过reflection")
    #         return {"success": True, "reviewed_count": 0}
    #     
    #     logger.info(f"开始Action [{action_type}] 反思评审，共{len(action_notes)}条Notes")
    #     
    #     try:
    #         # 构建reflection上下文
    #         context = build_reflection_context(action_notes, user_task, self.workspace, self.conversation)
    #         
    #         # 调用LLM进行反思评审
    #         response = call_llm(
    #             system_prompt=reflection_prompt,
    #             user_prompt=context,
    #             temperature=0.3,  # 使用较低温度确保评审一致性
    #             max_output_tokens=2000
    #         )
    #         
    #         # 解析review_result
    #         review_results = self._parse_review_result(response)
    #         
    #         if not review_results:
    #             logger.warning("未能解析出有效的review_result")
    #             return {"success": False, "error": "解析失败"}
    #         
    #         # 更新notes状态
    #         updated_count = 0
    #         for note_id, status, comment in review_results:
    #             if self.workspace.update_note_review_status(note_id, status, comment):
    #                 updated_count += 1
    #                 logger.info(f"反思评审: @{note_id} -> {status} ({comment})")
    #         
    #         # 统计结果
    #         star_count = sum(1 for _, status, _ in review_results if status == "star")
    #         archive_count = sum(1 for _, status, _ in review_results if status == "archive") 
    #         trash_count = sum(1 for _, status, _ in review_results if status == "trash")
    #         
    #         logger.info(f"Action [{action_type}] 反思完成: ⭐{star_count} 📝{archive_count} 🗑️{trash_count}")
    #         
    #         return {
    #             "success": True,
    #             "reviewed_count": updated_count,
    #             "star_count": star_count,
    #             "archive_count": archive_count,
    #             "trash_count": trash_count,
    #             "raw_response": response
    #         }
    #         
    #     except Exception as e:
    #         logger.error(f"reflection执行失败: {str(e)}")
    #         return {"success": False, "error": str(e)}
    
    # 注释掉_parse_review_result方法
    # def _parse_review_result(self, response: str) -> List[tuple]:
    #     """
    #     解析reflection响应中的review_result
    #     
    #     支持的格式：
    #     @note1:star, comment: 内容...
    #     @note2:archive, comment:
    #     跨行内容...
    #     
    #     Returns:
    #         [(note_id, status, comment), ...]
    #     """
    #     review_results = []
    #     
    #     # 提取review_result标签内容
    #     review_pattern = r'<review_result>(.*?)</review_result>'
    #     match = re.search(review_pattern, response, re.DOTALL)
    #     
    #     if not match:
    #         logger.warning("未找到<review_result>标签")
    #         return []
    #     
    #     review_content = match.group(1).strip()
    #     
    #     # 按@符号分割各个评审条目
    #     entries = re.split(r'\n(?=@)', review_content)
    #     
    #     for entry in entries:
    #         entry = entry.strip()
    #         if not entry or not entry.startswith('@'):
    #             continue
    #         
    #         try:
    #             # 分割每个条目的第一行和剩余内容
    #             lines = entry.split('\n')
    #             first_line = lines[0].strip()
    #             
    #             # 解析第一行：@note_id:status, comment:
    #             # 使用简单的字符串操作
    #             if ':' not in first_line:
    #                 continue
    #                 
    #             # 提取note_id
    #             note_part = first_line.split(':', 1)[0]
    #             note_id = note_part.replace('@', '').strip()
    #             
    #             # 提取status和comment标识
    #             rest_part = first_line.split(':', 1)[1].strip()
    #             
    #             # 提取status（逗号之前的部分）
    #             if ',' in rest_part:
    #                 status = rest_part.split(',', 1)[0].strip()
    #             else:
    #                 status = rest_part.strip()
    #             
    #             # 清理status
    #             status = status.lower().strip().strip('"').strip("'")
    #             
    #             # 提取comment内容
    #             comment_lines = []
    #             
    #             # 检查第一行是否有comment内容
    #             if 'comment:' in first_line:
    #                 after_comment = first_line.split('comment:', 1)[1].strip()
    #                 if after_comment:
    #                     comment_lines.append(after_comment)
    #             
    #             # 添加后续行的内容
    #             if len(lines) > 1:
    #                 comment_lines.extend([line.strip() for line in lines[1:] if line.strip()])
    #             
    #             # 组合comment
    #             comment = '\n'.join(comment_lines).strip()
    #             if not comment:
    #                 comment = "无评论"
    #             
    #             # 验证status有效性
    #             if status in ["star", "archive", "trash"]:
    #                 review_results.append((note_id, status, comment))
    #                 logger.debug(f"✅ 解析成功: @{note_id} -> {status}")
    #             else:
    #                 logger.warning(f"❌ 无效状态: '{status}' (note_id: {note_id})")
    #                 
    #         except Exception as e:
    #             logger.error(f"❌ 解析条目失败: {str(e)}")
    #             logger.debug(f"问题条目: {entry[:200]}...")
    #             continue
    #     
    #     if review_results:
    #         logger.info(f"✅ 成功解析{len(review_results)}条评审结果")
    #         for note_id, status, comment in review_results:
    #             logger.info(f"   @{note_id} -> {status}")
    #     else:
    #         logger.warning("❌ 未解析出任何有效的评审结果")
    #         logger.debug(f"原始内容: {review_content[:500]}...")
    #     
    #     return review_results


def execute(action_type: str, instruction: str, workspace, conversation, orchestrator=None) -> Dict[str, Any]:
    """
    执行单个步骤的独立函数

    Args:
        action_type: Action类型
        instruction: 执行指令（可包含@引用）
        workspace: WorkSpace实例
        conversation: ConversationManager实例
        orchestrator: Orchestrator实例（可选，用于reflection）

    Returns:
        执行结果
    """
    from prompts.action_prompts import ACTION_PROMPTS
    from core.context_builder import build_action_context
    from core.notes_extractor import extract_and_create_notes
    from model_base import call_llm

    logger.info(f"执行步骤: [{action_type}] {instruction[:50]}...")

    try:
        # 检查action类型是否有效
        if action_type not in ACTION_PROMPTS:
            raise ValueError(f"未知的Action类型: {action_type}")

        # 获取系统提示词
        system_prompt = ACTION_PROMPTS[action_type]

        # 构建简单的步骤对象（仅用于build_action_context）
        step = {
            "action": action_type,
            "instruction": instruction
        }

        # 🔍 特殊处理：image_to_prompt action 需要支持图片输入
        if action_type == "image_to_prompt":
            from model_base import call_llm_with_image
            from kimi_provider import KimiProvider

            # 从instruction中提取图片路径
            # 格式: "分析这张图片: 1.jpg" 或 "1.jpg"
            image_path = instruction.strip()
            user_prompt = "请分析这张图片，反推出AI图像生成提示词"

            # 如果instruction包含冒号，尝试提取路径
            if ":" in instruction:
                parts = instruction.split(":", 1)
                if len(parts) > 1:
                    potential_path = parts[1].strip()
                    # 检查是否是有效的文件路径
                    import os
                    if os.path.exists(potential_path):
                        image_path = potential_path
                        user_prompt = parts[0].strip() if parts[0].strip() else user_prompt

            logger.info(f"🖼️  分析图片: {image_path}")

            kimi_provider = KimiProvider()
            output = kimi_provider.call_llm_with_image(
                system_prompt=system_prompt,
                image_path=image_path,
                user_prompt=user_prompt,
                max_output_tokens=8000
            )

            # 提取notes
            step_id = f"orch_{action_type}_{len(workspace.notes) + 1}"
            notes_created = extract_and_create_notes(output, step_id, workspace, expected_types=[action_type])

            logger.info(f"步骤执行成功，创建了 {len(notes_created)} 个notes")

            return {
                "success": True,
                "output": output,
                "notes_created": notes_created
            }

        # 构建上下文
        user_prompt = build_action_context(step, workspace, conversation)

        # 🔍 特殊处理：websearch action始终使用kimi的真实搜索
        if action_type == "websearch":
            from kimi_provider import KimiProvider
            kimi_provider = KimiProvider()
            output = kimi_provider.call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,  # 降低温度提高准确性
                max_output_tokens=None,  # 不设限制
                enable_websearch=True  # 启用真实搜索
            )
        else:
            # 根据action类型设置不同的参数
            if action_type == "knowledge":
                temperature = 0.3
                max_tokens = 8000
                thinking_budget = None  # knowledge类型不需要特殊的思考预算
            elif action_type in ["xhs_post", "wechat_article", "tiktok_script", "hitpoint"]:
                # 写作类和hitpoint类Action使用更高的思考预算
                temperature = 0.6
                max_tokens = 8000
                thinking_budget = 1200
            else:
                temperature = 0.4
                max_tokens = 8000
                thinking_budget = 500

            # 构建调用参数
            llm_kwargs = {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "temperature": temperature,
                "max_output_tokens": max_tokens
            }

            # 只有需要时才添加thinking_budget参数
            if thinking_budget is not None:
                llm_kwargs["thinking_budget"] = thinking_budget

            # 其他action使用当前选择的基座模型
            output = call_llm(**llm_kwargs)

        # 提取notes
        step_id = f"orch_{action_type}_{len(workspace.notes) + 1}"
        notes_created = extract_and_create_notes(output, step_id, workspace, expected_types=[action_type])

        logger.info(f"步骤执行成功，创建了 {len(notes_created)} 个notes")

        return {
            "success": True,
            "output": output,
            "notes_created": notes_created
        }

    except Exception as e:
        logger.error(f"执行步骤失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "notes_created": []
        }