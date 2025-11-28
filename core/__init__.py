"""
Core模块
包含WorkSpace、ConversationManager等核心组件
"""

from .workspace import WorkSpace
from .conversation import ConversationManager
from .context_builder import (
    build_concierge_context,
    build_orchestrator_context,
    build_action_context,
    build_tactician_context,
    build_reflection_context
)
from .notes_extractor import extract_notes

__all__ = [
    'WorkSpace',
    'ConversationManager',
    'build_concierge_context',
    'build_orchestrator_context',
    'build_action_context',
    'build_tactician_context',
    'build_reflection_context',
    'extract_notes'
] 