"""
上下文构建器
为Concierge、Orchestrator和Action构建合适的上下文
"""

import re
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def build_concierge_context(user_msg: str, workspace, conversation) -> str:
    """
    构建Concierge的上下文
    
    包含:
    - chat_history（聊天历史，最新消息会标记）
    - orchestrator_timeline（Orchestrator统一时间线）
    - created_notes（所有生成的笔记）
    """
    parts = []
    
    # 1. chat_history - 类似orchestrator的用户消息队列
    parts.append("[chat_history]")
    chat_history = conversation.get_recent_chat_history(limit=100)  # 获取最近100条
    
    # 先检查当前消息是否是新的（还未记录）
    # 注意：在调用这个函数时，用户消息可能还未被add_user_message记录
    is_new_message = True
    if chat_history and chat_history[-1]["type"] == "user" and chat_history[-1]["content"] == user_msg:
        is_new_message = False
    
    # 构建聊天历史列表
    message_count = 0
    for entry in chat_history:
        message_count += 1
        if entry["type"] == "user":
            parts.append(f"#{message_count} **用户**: {entry['content']}")
        elif entry["type"] == "concierge":
            # 显示原始响应，不是清理后的版本
            original_response = entry.get('original_response', entry['content'])
            parts.append(f"#{message_count} Lumina（你）: {original_response}")
    
    # 如果当前消息是新的，添加到末尾并标记(新)
    if is_new_message:
        message_count += 1
        parts.append(f"#{message_count} **(新) 用户**: {user_msg}")
    
    parts.append("")
    
    # 2. 任务执行时间线 - 统一显示格式
    orchestrator_calls = conversation.get_recent_orchestrator_calls(limit=None)  # 获取所有调用
    
    parts.append("[Orchestrator任务执行时间线]")
    if not orchestrator_calls:
        # 如果没有任何orchestrator调用，说明未启动
        parts.append("「**系统状态: Orchestrator未启动，等待任务需求传递**」")
    else:
        # 按时间顺序显示所有orchestrator交互
        for msg_idx, msg in enumerate(orchestrator_calls):
            # 显示用户消息
            parts.append(f"# 用户消息{msg_idx + 1}: {msg['message']}")
            parts.append("")  # 空行
            
            # 显示属于这个用户消息的执行记录
            if 'execution_records' in msg and msg['execution_records']:
                for record in msg['execution_records']:
                    # 解析Round信息
                    round_match = re.match(r'Round(\d+):', record['step'])
                    if round_match:
                        round_num = round_match.group(1)
                        parts.append(f"## Round{round_num}:")
                        
                        # 显示observe（清理换行，Concierge用80字符预览）
                        if 'observe' in record and record['observe']:
                            observe_clean = record['observe'].replace('\n', ' ').replace('\r', ' ')
                            observe_clean = ' '.join(observe_clean.split())
                            observe_preview = observe_clean[:80] + "..." if len(observe_clean) > 80 else observe_clean
                            parts.append(f"🔍 观察: {observe_preview}")
                        
                        # 显示think（清理换行，Concierge用80字符预览）
                        if 'think' in record and record['think']:
                            think_clean = record['think'].replace('\n', ' ').replace('\r', ' ')
                            think_clean = ' '.join(think_clean.split())
                            think_preview = think_clean[:80] + "..." if len(think_clean) > 80 else think_clean
                            parts.append(f"💭 思考: {think_preview}")
                        
                        # 解析执行信息
                        step_content = record['step']
                        # 提取所有action和memo
                        all_actions = re.findall(r'"([^"]+)"', step_content)
                        # memo_match = re.search(r'memo: (.+)', step_content)
                        
                        if all_actions:
                            if len(all_actions) == 1:
                                parts.append(f"⚡ 执行: {all_actions[0]}")
                            else:
                                actions_str = ', '.join(all_actions)
                                parts.append(f"⚡ 执行: {actions_str}")
                        
                        # if memo_match:
                        #     memo = memo_match.group(1)
                        #     parts.append(f"📝 memo: {memo}")
                        
                        parts.append("")  # Round后的空行
            else:
                parts.append("（pending）")
                parts.append("")
            
            # 如果不是最后一个消息，添加分隔线
            if msg_idx < len(orchestrator_calls) - 1:
                parts.append("---")
                parts.append("")
        
        # 检查orchestrator运行状态
        if conversation.is_orchestrator_running():
            parts.append("「**系统状态: Orchestrator运行中，允许实时补充新需求**」")
        else:
            parts.append("「**系统状态: Orchestrator当前轮次执行完毕，等待传入新的需求**」")
    
        parts.append("")
    
    # 3. created_notes - Concierge只看前50字符摘要，按状态分类
    if workspace.notes:
        parts.append("[created_notes]")
        
        # 按状态分类
        star_notes = []
        archive_notes = []
        unreviewed_notes = []
        # trash notes对Concierge隐藏，不显示
        
        for note_id, note_data in workspace.notes.items():
            status = note_data.get("review_status")
            content_preview = note_data["content"][:50] + "..." if len(note_data["content"]) > 50 else note_data["content"]
            
            if status == "star":
                star_notes.append(f"⭐ @{note_id}: {content_preview}")
            elif status == "archive":
                archive_notes.append(f"📝 @{note_id}: {content_preview}")
            elif status != "trash":  # 排除trash，但包括未评审的
                unreviewed_notes.append(f"@{note_id}: {content_preview}")
        
        # 优先显示星标内容
        for note_line in star_notes:
            parts.append(note_line)
        for note_line in archive_notes:
            parts.append(note_line)
        for note_line in unreviewed_notes:
            parts.append(note_line)
            
        parts.append("")
    
    return "\n".join(parts)


def build_orchestrator_context(task_message: str, workspace, conversation, execution_log: Optional[List[Dict]] = None) -> str:
    """
    构建Orchestrator的上下文
    
    包含:
    - 完整的用户消息队列和执行时间线
    - 每个Round的产出Notes（显示在对应Round执行记录后）
    注：Tactician分析结果暂时注释掉，统一created_notes显示已改为分散显示
    """
    parts = []
    
    # 1. 任务执行时间线（与用户消息关联的执行记录）
    parts.append("[任务执行时间线]")
    
    # 获取所有用户消息及其执行记录
    orchestrator_calls = conversation.get_recent_orchestrator_calls()
    all_messages = []
    
    # 构建完整的消息队列，包括历史消息和当前消息
    for call in orchestrator_calls:
        all_messages.append(call)
    
    # 如果当前消息不在历史记录中，添加为pending状态
    if task_message not in [msg['message'] for msg in all_messages]:
        all_messages.append({
            'message': task_message,
            'execution_records': [],
            'timestamp': 'current'
        })
    
    # 显示时间线
    if not all_messages:
        parts.append("（暂无用户消息）")
    else:
        # 按时间顺序显示每个用户消息及其执行记录
        for msg_idx, msg in enumerate(all_messages):
            # 显示用户消息
            parts.append(f"用户消息{msg_idx + 1}: {msg['message']}")
            
            # 显示该用户消息相关的material材料（用户上传的资料）
            message_materials = []
            for note_id, note_data in workspace.notes.items():
                if (note_id.startswith('material') and 
                    note_data.get('source') == 'concierge' and
                    note_data.get('review_status') != 'trash'):  # 排除垃圾material
                    message_materials.append((note_id, note_data))
            
            if message_materials:
                parts.append("")
                parts.append("📎 用户提供的材料：")
                for note_id, note_data in message_materials:
                    content_preview = note_data['content'][:100] + "..." if len(note_data['content']) > 100 else note_data['content']
                    parts.append(f"@{note_id}: {content_preview}")
                    parts.append("")  # 每个material后加空行
            
            parts.append("")  # 空行
            
            # 显示属于这个用户消息的执行记录
            if 'execution_records' in msg and msg['execution_records']:
                for record in msg['execution_records']:
                    # 解析Round信息
                    round_match = re.match(r'Round(\d+):', record['step'])
                    if round_match:
                        round_num = round_match.group(1)
                        parts.append(f"## Round{round_num}:")
                        
                        # 显示observe（清理换行）
                        if 'observe' in record and record['observe']:
                            observe_clean = record['observe'].replace('\n', ' ').replace('\r', ' ')
                            # 压缩多个空格为单个空格
                            observe_clean = ' '.join(observe_clean.split())
                            parts.append(f"🔍 观察: {observe_clean}")
                        
                        # 显示think（清理换行）
                        if 'think' in record and record['think']:
                            think_clean = record['think'].replace('\n', ' ').replace('\r', ' ')
                            # 压缩多个空格为单个空格
                            think_clean = ' '.join(think_clean.split())
                            parts.append(f"💭 思考: {think_clean}")
                        
                        # 解析执行信息
                        step_content = record['step']
                        # 提取所有action和memo
                        all_actions = re.findall(r'"([^"]+)"', step_content)
                        # memo_match = re.search(r'memo: (.+)', step_content)
                        
                        if all_actions:
                            if len(all_actions) == 1:
                                parts.append(f"⚡ 执行: {all_actions[0]}")
                            else:
                                actions_str = ', '.join(all_actions)
                                parts.append(f"⚡ 执行: {actions_str}")
                        
                        # 显示该Round产出的Notes
                        round_notes = record.get('notes_created', [])
                        if round_notes:
                            parts.append("")
                            parts.append("📝 本轮产出:")
                            # 按状态分类显示notes
                            for note_id in round_notes:
                                note = workspace.get_note(note_id)
                                if note:
                                    status = note.get("review_status", "")
                                    if status == "star":
                                        status_icon = "⭐"
                                    elif status == "archive":
                                        status_icon = "📝"
                                    elif status == "trash":
                                        status_icon = "🗑️"
                                    else:
                                        status_icon = "📄"
                                    
                                    # 显示note预览（前100字符）
                                    content_preview = note['content'][:100] + "..." if len(note['content']) > 100 else note['content']
                                    parts.append(f"{status_icon} @{note_id}: {content_preview}")
                        
                        # if memo_match:
                        #     memo = memo_match.group(1)
                        #     parts.append(f"📝 memo: {memo}")
                        
                        parts.append("")  # Round后的空行
            else:
                # 如果是当前新消息，显示pending状态
                if msg.get('timestamp') == 'current':
                    parts.append("（pending）")
                    parts.append("")
            
            # 如果不是最后一个消息，添加分隔线
            if msg_idx < len(all_messages) - 1:
                parts.append("---")
                parts.append("")

    # 2. Tactician分析结果
    if hasattr(workspace, 'tactician_analysis') and workspace.tactician_analysis:
        strategy_notes = workspace.tactician_analysis.get('strategy_notes', [])
        if strategy_notes:
            parts.append("[Tactician分析结果]")
            parts.append("以下是策略分析的产出，请参考其中的策略内容：")
            parts.append("")
            for strategy_id in strategy_notes:
                strategy_note = workspace.get_note(strategy_id)
                if strategy_note:
                    parts.append(f"@{strategy_id}:")
                    parts.append(strategy_note['content'])
                    parts.append("")
                else:
                    parts.append(f"@{strategy_id}: [note not found]")
                    parts.append("")

    # 3. created_notes - 已改为在每个Round后显示，注释掉统一显示
    #     
    #     if action_notes:
    #         parts.append("[created_notes]")
    #         parts.append("以下是目前Action产出的Notes，按照出现顺序展示：")
    #         
    #         # 按状态分类显示
    #         star_notes = []
    #         archive_notes = []
    #         trash_notes = []
    #         unreviewed_notes = []
    #         
    #         for note_id, note_data in action_notes.items():
    #             status = note_data.get("review_status")
    #             if status == "star":
    #                 star_notes.append((note_id, note_data))
    #             elif status == "archive":
    #                 archive_notes.append((note_id, note_data))
    #             elif status == "trash":
    #                 trash_notes.append((note_id, note_data))
    #             else:
    #                 unreviewed_notes.append((note_id, note_data))
    #         
    #         # 显示星标notes
    #         if star_notes:
    #             parts.append("")
    #             parts.append("⭐ 高价值内容：")
    #             for note_id, note_data in star_notes:
    #                 parts.append(f"@{note_id}:")
    #                 parts.append(note_data["content"])
    #                 parts.append("")
    #         
    #         # 显示归档notes
    #         if archive_notes:
    #             parts.append("📝 保留内容：")
    #             for note_id, note_data in archive_notes:
    #                 parts.append(f"@{note_id}:")
    #                 parts.append(note_data["content"])
    #                 parts.append("")
    #         
    #         # 显示其他notes
    #         if unreviewed_notes:
    #             if star_notes or archive_notes:
    #                 parts.append("📄 其他内容：")
    #             for note_id, note_data in unreviewed_notes:
    #                 parts.append(f"@{note_id}:")
    #                 parts.append(note_data["content"])
    #                 parts.append("")
    #         
    #         # 显示垃圾notes作为警示
    #         if trash_notes:
    #             parts.append("[trash_result] ⚠️ 质量问题警示")
    #             parts.append("以下内容存在质量问题，无法引用，请引以为戒：")
    #             for note_id, note_data in trash_notes:
    #                 comment = note_data.get("review_comment", "质量问题")
    #                 parts.append(f"🗑️ @{note_id}: {comment}")
    #             parts.append("")
    
    return "\n".join(parts)


def build_action_context(step: Dict, workspace, conversation) -> str:
    """
    构建Action的上下文
    
    包含:
    - 用户需求（部分Action需要，如写作类）
    - Orchestrator提供的instruction
    - instruction中@引用的完整内容
    """
    parts = []
    
    # 定义写作类Action列表（用于自动material引用）
    writing_actions = ["midjourney_prompt", "dalle_prompt", "sd_prompt", "visual_concept"]

    # 定义不需要用户需求的Action类型
    no_user_need_actions = ["websearch", "knowledge", "style_analysis", "mood_analysis", "composition_analysis"]
    
    # 1. 根据Action类型决定是否添加用户需求背景
    if step["action"] not in no_user_need_actions:
        parts.append("[用户需求]")
        # 获取所有Concierge传递给Orchestrator的任务消息
        orchestrator_calls = conversation.get_recent_orchestrator_calls()
        if orchestrator_calls:
            # 将所有任务消息按时间顺序展示
            for i, call in enumerate(orchestrator_calls):
                if i == 0:
                    # 第一条是主要需求
                    parts.append(call['message'])
                else:
                    # 后续的是补充和反馈
                    parts.append(f"补充: {call['message']}")
        else:
            parts.append("无特定用户需求")
        parts.append("")
    
    # 2. 当前任务指令
    parts.append("[任务指令]")
    parts.append(step["instruction"])
    parts.append("")
    
    # 3. 解析并展开@引用（包括自动material引用）
    import re
    refs = []
    
    # 查找instruction中的@引用
    if '@' in step["instruction"]:
        refs = re.findall(r'@([a-zA-Z_]+\d+)', step["instruction"])
        refs = list(set(refs))  # 去重
    
    # 为hitpoint和创作类Action自动添加@material引用
    if step["action"] in writing_actions:
        # 查找所有material类型的notes
        referenceable_notes = workspace.get_referenceable_notes()  # 排除trash状态
        material_notes = [note_id for note_id in referenceable_notes.keys() if note_id.startswith('material')]
        # 添加到引用列表，但避免重复
        for material_id in material_notes:
            if material_id not in refs:
                refs.append(material_id)
    
    # 4. 展开所有@引用内容
    if refs:
        parts.append("[引用内容]")
        referenceable_notes = workspace.get_referenceable_notes()  # 排除trash状态
        for ref in refs:
            note_data = referenceable_notes.get(ref)
            if note_data:
                parts.append(f"@{ref}:")
                parts.append(note_data["content"])
                parts.append("")
            else:
                parts.append(f"@{ref}: [未找到或不可引用]")
                parts.append("")
    
    return "\n".join(parts)


def build_tactician_context(user_message: str, workspace, conversation) -> str:
    """
    构建Tactician的上下文

    包含:
    - 用户创作需求
    - 现有资料（用户上传的参考图等）
    - 支持的目标平台信息
    """
    parts = []

    # 1. 用户创作需求
    parts.append("[用户图像创作需求]")
    parts.append(user_message)
    parts.append("")

    # 2. 用户上传的参考资料
    material_notes = []
    for note_id, note_data in workspace.notes.items():
        if note_id.startswith('material') and note_data.get('review_status') != 'trash':
            material_notes.append((note_id, note_data))

    if material_notes:
        parts.append("[用户上传的参考资料]")
        for note_id, note_data in material_notes:
            parts.append(f"@{note_id}:")
            parts.append(note_data["content"][:500] + "..." if len(note_data["content"]) > 500 else note_data["content"])
            parts.append("")

    # 3. 支持的目标平台
    parts.append("[目标平台]")
    parts.append("支持以下AI图像生成平台：Midjourney、DALL-E、Stable Diffusion、Flux")
    parts.append("每个平台有不同的提示词语法和风格偏好")
    parts.append("")

    return "\n".join(parts)


def build_reflection_context(action_notes: List[str], user_task: str, workspace, conversation) -> str:
    """
    构建Reflection的上下文
    
    包含:
    - 用户任务需求（初次需求和反馈补充）
    - 本次Action产出的Notes完整内容
    """
    parts = []
    
    # 1. 用户任务需求
    parts.append("[用户任务需求]")
    # 获取所有Orchestrator调用的用户消息
    orchestrator_calls = conversation.get_recent_orchestrator_calls()
    if orchestrator_calls:
        for i, call in enumerate(orchestrator_calls):
            if i == 0:
                parts.append(f"初次需求: {call['message']}")
            else:
                parts.append(f"反馈补充: {call['message']}")
    else:
        parts.append(user_task)
    parts.append("")
    
    # 2. 本次Action产出的Notes
    if action_notes:
        parts.append("[本次Action产出Notes]")
        parts.append("以下是本次Action执行产出的内容，需要逐一评审，只有一条能被star：")
        parts.append("")
        
        for note_id in action_notes:
            note = workspace.get_note(note_id)
            if note:
                parts.append(f"@{note_id}:")
                parts.append(note["content"])
                parts.append("")
    
    return "\n".join(parts)