"""
对话历史管理器
分层存储用户对话、Orchestrator调用和执行记录
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConversationManager:
    """管理对话历史，包括用户消息、Concierge响应、Orchestrator调用等"""
    
    def __init__(self):
        # 完整的对话历史
        self.history: List[Dict[str, Any]] = []
        
        # Orchestrator调用历史（用于快速访问）
        self._orchestrator_calls: List[Dict[str, Any]] = []
        
        # 当前活跃的orchestrator调用索引
        self._active_orchestrator_index: Optional[int] = None
        
        # Orchestrator运行状态
        self._orchestrator_running: bool = False
        
        # logger.info("ConversationManager初始化完成")
    
    def add_user_message(self, content: str, notes_created: Optional[List[str]] = None):
        """添加用户消息"""
        entry = {
            "type": "user",
            "content": content,
            "notes_created": notes_created or []
        }
        self.history.append(entry)
        # logger.info(f"添加用户消息: {content[:50]}...")
    
    def add_concierge_response(self, content: str, orchestrator_call: Optional[str] = None, original_response: Optional[str] = None):
        """添加Concierge响应"""
        entry = {
            "type": "concierge",
            "content": content
        }
        
        # 如果提供了原始响应，也存储起来
        if original_response:
            entry["original_response"] = original_response
        
        if orchestrator_call:
            entry["orchestrator_call"] = orchestrator_call
            # 同时记录到orchestrator调用历史
            self._orchestrator_calls.append({
                "message": orchestrator_call,
                "history_index": len(self.history),
                "execution_records": []  # 新增：存储属于这个调用的执行记录
            })
            # 更新活跃的orchestrator调用索引
            self._active_orchestrator_index = len(self._orchestrator_calls) - 1
        
        self.history.append(entry)
        # logger.info(f"添加Concierge响应: {content[:50]}...")
    
    def add_orchestrator_response(self, content: str):
        """添加Orchestrator响应"""
        entry = {
            "type": "orchestrator",
            "content": content
        }
        self.history.append(entry)
        
        # 更新最近的orchestrator调用记录
        if self._orchestrator_calls:
            self._orchestrator_calls[-1]["response_index"] = len(self.history) - 1
        
        # logger.info(f"添加Orchestrator响应: {content[:50]}...")
    
    def add_execution_record(self, step: str, notes_created: Optional[List[str]] = None, observe: Optional[str] = None, think: Optional[str] = None):
        """添加执行记录"""
        entry = {
            "type": "execution",
            "step": step,
            "notes_created": notes_created or []
        }
        
        # 添加observe和think信息（如果存在）
        if observe:
            entry["observe"] = observe
        if think:
            entry["think"] = think
        
        self.history.append(entry)
        
        # 将执行记录关联到当前活跃的orchestrator调用
        if self._active_orchestrator_index is not None and self._active_orchestrator_index < len(self._orchestrator_calls):
            execution_record = {
                "step": step,
                "notes_created": notes_created or []
            }
            
            # 添加observe和think信息（如果存在）
            if observe:
                execution_record["observe"] = observe
            if think:
                execution_record["think"] = think
            
            self._orchestrator_calls[self._active_orchestrator_index]["execution_records"].append(execution_record)
        
        logger.info(f"添加执行记录: {step}")
    
    def update_latest_execution_notes(self, notes_created: List[str]):
        """更新最新execution_record的notes信息"""
        if self._active_orchestrator_index is not None and self._active_orchestrator_index < len(self._orchestrator_calls):
            current_call = self._orchestrator_calls[self._active_orchestrator_index]
            if current_call["execution_records"]:
                # 更新最新的execution_record
                latest_record = current_call["execution_records"][-1]
                latest_record["notes_created"] = notes_created
                logger.info(f"更新执行记录notes: {len(notes_created)}个notes")
    
    def get_recent_chat_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的用户对话历史（仅user和concierge类型）"""
        chat_history = []
        for entry in reversed(self.history):
            if entry["type"] in ["user", "concierge"]:
                chat_history.append(entry)
                if len(chat_history) >= limit * 2:  # user和concierge成对
                    break
        
        return list(reversed(chat_history))
    
    def get_recent_orchestrator_calls(self, limit: Optional[int] = 10) -> List[Dict[str, str]]:
        """获取最近的Orchestrator调用历史"""
        recent_calls = []
        
        # 如果limit为None，获取所有历史；否则获取最近的limit条
        calls_to_process = self._orchestrator_calls if limit is None else self._orchestrator_calls[-limit:]
        
        for call in reversed(calls_to_process):
            result = {
                "message": call["message"]
            }
            
            # 如果有响应，也包含进去
            if "response_index" in call:
                response = self.history[call["response_index"]]
                result["response"] = response["content"]
            
            # 包含执行记录（新增）
            if "execution_records" in call:
                result["execution_records"] = call["execution_records"]
            
            recent_calls.append(result)
        
        return list(reversed(recent_calls))
    
    def set_active_orchestrator_call(self, index: int):
        """设置当前活跃的orchestrator调用索引"""
        if 0 <= index < len(self._orchestrator_calls):
            self._active_orchestrator_index = index
        else:
            logger.warning(f"无效的orchestrator调用索引: {index}")
    
    def set_orchestrator_running(self, running: bool):
        """设置orchestrator运行状态"""
        self._orchestrator_running = running
    
    def is_orchestrator_running(self) -> bool:
        """获取orchestrator运行状态"""
        return self._orchestrator_running 