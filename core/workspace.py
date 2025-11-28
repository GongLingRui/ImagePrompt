"""
WorkSpace - ImagePrompt系统的数据中心
管理Notes和tactics
"""

from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class WorkSpace:
    """工作空间，存储和管理所有任务数据"""
    
    def __init__(self):
        # Notes存储 - 使用类型+编号作为key
        self.notes: Dict[str, Dict[str, str]] = {}
        
        # 编号计数器 - 用于自动编号
        self._note_counters: Dict[str, int] = {}
        
        # tactics - Orchestrator的工作备忘
        self.tactics: Optional[str] = None
        

        self.tactician_analysis: Dict[str, Any] = {}  # Tactician的完整分析结果
        
        # 保留plan属性以兼容旧代码（如concierge中的取消操作）
        self.plan = None
        
        # logger.info("WorkSpace初始化完成")
    
    def create_note(self, note_type: str, content: str, source: str, review_status: Optional[str] = None) -> str:
        """
        创建新的note
        
        Args:
            note_type: note类型（如xhs_post, resonant, text_study等）
            content: note内容
            source: 来源（user, step_1, step_2等）
            review_status: 反思评审状态 ("star", "archive", "trash", None)
            
        Returns:
            创建的note的key（如resonant1）
        """
        # 获取下一个编号
        if note_type not in self._note_counters:
            self._note_counters[note_type] = 0
        
        self._note_counters[note_type] += 1
        note_id = f"{note_type}{self._note_counters[note_type]}"
        
        # 存储note
        self.notes[note_id] = {
            "type": note_type,
            "content": content,
            "source": source
        }
        
        # 添加反思状态
        if review_status:
            self.notes[note_id]["review_status"] = review_status
        
        # logger.info(f"创建note: {note_id} (来源: {source})")
        return note_id
    
    def get_note(self, note_id: str) -> Optional[Dict[str, str]]:
        """获取指定的note"""
        return self.notes.get(note_id)
    
    def get_notes_by_type(self, note_type: str) -> Dict[str, Dict[str, str]]:
        """获取指定类型的所有notes"""
        return {
            note_id: note_data 
            for note_id, note_data in self.notes.items() 
            if note_id.startswith(note_type)
        }
    
    def get_notes_by_status(self, status: str) -> Dict[str, Dict[str, str]]:
        """获取指定反思状态的所有notes"""
        return {
            note_id: note_data 
            for note_id, note_data in self.notes.items() 
            if note_data.get("review_status") == status
        }
    
    def update_note_review_status(self, note_id: str, status: str, comment: Optional[str] = None) -> bool:
        """
        更新note的反思评审状态
        
        Args:
            note_id: note ID
            status: 状态 ("star", "archive", "trash")
            comment: 反思评论
            
        Returns:
            是否成功更新
        """
        if note_id in self.notes:
            self.notes[note_id]["review_status"] = status
            if comment:
                self.notes[note_id]["review_comment"] = comment
            logger.info(f"更新note反思状态: {note_id} -> {status}")
            return True
        return False
    
    def get_referenceable_notes(self) -> Dict[str, Dict[str, str]]:
        """获取可引用的notes（排除trash状态）"""
        return {
            note_id: note_data 
            for note_id, note_data in self.notes.items() 
            if note_data.get("review_status") != "trash"
        }
    
    def set_tactician_analysis(self, tactician_analysis: Dict[str, Any]):
        """设置Tactician分析结果"""
        self.tactician_analysis = tactician_analysis or {}
        strategy_count = len(tactician_analysis.get('strategy_notes', []))
        logger.info(f"设置Tactician分析结果: {strategy_count} 个strategy notes")
    
