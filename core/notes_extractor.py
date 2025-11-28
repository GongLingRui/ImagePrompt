"""
Notes提取器 - 鲁棒版本
从Action输出中提取XML标签格式的notes，支持各种corner case处理
"""

import re
from typing import Dict, List, Tuple, Set, Optional
import logging
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class RobustNotesExtractor:
    """鲁棒的Notes提取器，能够处理各种格式错误和边界情况"""
    
    def __init__(self):
        self.known_types = [
            'subject_analysis', 'style_analysis', 'mood_analysis', 'composition_analysis',
            'reference_analysis', 'visual_concept',
            'midjourney_prompt', 'dalle_prompt', 'sd_prompt',
            'material', 'websearch', 'knowledge', 'question', 'strategy'
        ]
        
        # 统计信息
        self.extraction_stats = {
            'perfect_matches': 0,
            'repaired_matches': 0,
            'fuzzy_matches': 0,
            'failed_extractions': 0
        }
    
    def extract_notes(self, response: str) -> Dict[str, List[Tuple[str, str]]]:
        """
        从响应文本中提取所有XML格式的notes
        使用多级解析策略，从严格到宽松
        
        Args:
            response: Action的输出文本
            
        Returns:
            字典，key为note类型，value为(编号, 内容)的列表
        """
        if not response or not response.strip():
            return {}
            
        notes_by_type = {}
        
        # 重置统计信息
        self.extraction_stats = {key: 0 for key in self.extraction_stats}
        
        # 对每种已知类型进行多级提取
        for tag_type in self.known_types:
            extracted_notes = self._extract_notes_for_type(response, tag_type)
            if extracted_notes:
                notes_by_type[tag_type] = extracted_notes
        
        # 🔧 临时关闭未知类型检测，避免测试干扰
        # # 尝试发现未知类型的标签
        # unknown_notes = self._extract_unknown_types(response)
        # if unknown_notes:
        #     notes_by_type.update(unknown_notes)
        
        # 记录统计信息
        total_notes = sum(len(notes) for notes in notes_by_type.values())
        logger.info(f"提取完成 - 总计{total_notes}条notes")
        logger.info(f"统计: 完美匹配{self.extraction_stats['perfect_matches']}, "
                   f"修复匹配{self.extraction_stats['repaired_matches']}, "
                   f"模糊匹配{self.extraction_stats['fuzzy_matches']}, "
                   f"失败{self.extraction_stats['failed_extractions']}")
        
        return notes_by_type
    
    def _extract_notes_for_type(self, response: str, tag_type: str) -> List[Tuple[str, str]]:
        """
        为特定类型提取notes，使用多级策略
        
        Args:
            response: 响应文本
            tag_type: 标签类型
            
        Returns:
            (编号, 内容)的列表
        """
        notes = []
        
        # 第一级：完美匹配
        perfect_notes = self._extract_perfect_matches(response, tag_type)
        if perfect_notes:
            notes.extend(perfect_notes)
            self.extraction_stats['perfect_matches'] += len(perfect_notes)
            logger.debug(f"完美匹配 {tag_type}: {len(perfect_notes)} 条")
        else:
            # 第二级：修复匹配（只有在完美匹配失败时才尝试）
            repaired_notes = self._extract_with_repair(response, tag_type)
            if repaired_notes:
                notes.extend(repaired_notes)
                self.extraction_stats['repaired_matches'] += len(repaired_notes)
                logger.debug(f"修复匹配 {tag_type}: {len(repaired_notes)} 条")
        
        # 第三级：模糊匹配（只有在前两级都没有结果时才尝试）
        if not notes:
            fuzzy_notes = self._extract_fuzzy_matches(response, tag_type)
            if fuzzy_notes:
                notes.extend(fuzzy_notes)
                self.extraction_stats['fuzzy_matches'] += len(fuzzy_notes)
                logger.debug(f"模糊匹配 {tag_type}: {len(fuzzy_notes)} 条")
        
        return self._clean_duplicate_notes(notes, tag_type)
    
    def _extract_perfect_matches(self, response: str, tag_type: str) -> List[Tuple[str, str]]:
        """第一级：完美匹配标准格式"""
        notes = []
        
        # 1. 带星号的完美格式：<**type1**>...</</**type1**>
        starred_pattern = f'<\\*\\*{tag_type}(\\d+)\\*\\*>(.*?)</\\*\\*{tag_type}\\1\\*\\*>'
        for match in re.finditer(starred_pattern, response, re.DOTALL):
            number = match.group(1)
            content = match.group(2).strip()
            if content:  # 只添加非空内容
                notes.append((number, content))
        
        # 2. 标准带编号的完美格式：<type1>...</type1>
        if not notes:
            numbered_pattern = f'<{tag_type}(\\d+)>(.*?)</{tag_type}\\1>'
            for match in re.finditer(numbered_pattern, response, re.DOTALL):
                number = match.group(1)
                content = match.group(2).strip()
                if content:
                    notes.append((number, content))
        
        # 3. 无编号的完美格式
        if not notes:
            # 带星号的无编号格式
            starred_simple_pattern = f'<\\*\\*{tag_type}\\*\\*>(.*?)</\\*\\*{tag_type}\\*\\*>'
            starred_matches = list(re.finditer(starred_simple_pattern, response, re.DOTALL))
            
            if starred_matches:
                for i, match in enumerate(starred_matches, 1):
                    content = match.group(1).strip()
                    if content:
                        notes.append((str(i), content))
            else:
                # 标准无编号格式
                simple_pattern = f'<{tag_type}>(.*?)</{tag_type}>'
                simple_matches = list(re.finditer(simple_pattern, response, re.DOTALL))
                
                if simple_matches:
                    for i, match in enumerate(simple_matches, 1):
                        content = match.group(1).strip()
                        if content:
                            notes.append((str(i), content))
        
        return notes
    
    def _extract_with_repair(self, response: str, tag_type: str) -> List[Tuple[str, str]]:
        """第二级：修复匹配，处理格式错误"""
        notes = []
        
        # 1. 修复缺少闭合标签的情况
        notes.extend(self._repair_unclosed_tags(response, tag_type))
        
        # 2. 修复标签符号缺失的情况
        notes.extend(self._repair_missing_symbols(response, tag_type))
        
        # 3. 修复数字不匹配的情况
        notes.extend(self._repair_mismatched_numbers(response, tag_type))
        
        return notes
    
    def _repair_unclosed_tags(self, response: str, tag_type: str) -> List[Tuple[str, str]]:
        """修复不完整的闭合标签"""
        notes = []
        
        # 寻找开标签但闭合标签不完整的情况
        patterns = [
            # 带星号的开标签，但闭合标签可能不完整
            (f'<\\*\\*{tag_type}(\\d+)\\*\\*>(.*?)(?:</\\*\\*{tag_type}\\d*\\*\\*>|</\\*\\*{tag_type}\\*\\*>|</\\*\\*|</|$)', 'starred'),
            # 标准开标签，但闭合标签可能不完整 - 增强版，支持各种不完整结尾
            (f'<{tag_type}(\\d+)>(.*?)(?:</{tag_type}\\d*>|</{tag_type}>|</\\w*|</|<$|$)', 'numbered'),
            # 无编号的开标签 - 增强版
            (f'<\\*\\*{tag_type}\\*\\*>(.*?)(?:</\\*\\*{tag_type}\\*\\*>|</\\*\\*|</|$)', 'starred_simple'),
            (f'<{tag_type}>(.*?)(?:</{tag_type}>|</\\w*|</|<$|$)', 'simple')
        ]
        
        for pattern, pattern_type in patterns:
            matches = list(re.finditer(pattern, response, re.DOTALL))
            if matches:
                for i, match in enumerate(matches, 1):
                    if pattern_type in ['starred', 'numbered']:
                        number = match.group(1)
                        content = match.group(2).strip()
                    else:
                        number = str(i)
                        content = match.group(1).strip()
                    
                    if content and len(content) > 0:
                        # 清理内容，移除可能的不完整闭合标签和无效内容
                        content = self._clean_content(content, tag_type)
                        
                        # 特殊处理：对于question类型，额外清理可能的干扰文本
                        if tag_type == "question":
                            # 移除可能混入的说明性文字（如"接下来，是受众。谁会关注..."这样的段落）
                            # 通常question内容应该以问号结尾，我们可以利用这个特征
                            lines = content.split('\n')
                            cleaned_lines = []
                            question_started = False
                            
                            for line in lines:
                                line = line.strip()
                                if not line:
                                    continue
                                
                                # 如果包含问号，认为是问题内容
                                if '？' in line or '?' in line:
                                    question_started = True
                                    cleaned_lines.append(line)
                                elif question_started:
                                    # 问题开始后，继续收集内容直到遇到明显的分段
                                    if not line.startswith('接下来') and not line.startswith('然后') and not line.startswith('我们'):
                                        cleaned_lines.append(line)
                                    else:
                                        break
                                elif line.endswith('？') or line.endswith('?'):
                                    # 单独一行以问号结尾的内容
                                    cleaned_lines.append(line)
                                    question_started = True
                            
                            if cleaned_lines:
                                content = '\n'.join(cleaned_lines)
                        
                        if content:
                            notes.append((number, content))
                            logger.debug(f"修复不完整标签 {tag_type}{number}")
                break  # 找到一种模式就停止
        
        return notes
    
    def _repair_missing_symbols(self, response: str, tag_type: str) -> List[Tuple[str, str]]:
        """修复缺少<、>、/等符号的情况"""
        notes = []
        
        # 寻找可能缺少符号的模式
        patterns = [
            # 缺少<的情况：**type1**>content</type1>
            (f'\\*\\*{tag_type}(\\d+)\\*\\*>(.*?)</\\*\\*{tag_type}\\1\\*\\*>', 'missing_open_bracket'),
            # 缺少>的情况：<**type1**content</type1>
            (f'<\\*\\*{tag_type}(\\d+)\\*\\*(.*?)</\\*\\*{tag_type}\\1\\*\\*>', 'missing_close_bracket'),
            # 缺少/的情况：<type1>content<type1>
            (f'<{tag_type}(\\d+)>(.*?)<{tag_type}\\1>', 'missing_slash'),
        ]
        
        for pattern, repair_type in patterns:
            matches = list(re.finditer(pattern, response, re.DOTALL))
            if matches:
                for match in matches:
                    number = match.group(1)
                    content = match.group(2).strip()
                    if content:
                        notes.append((number, content))
                        logger.debug(f"修复缺少符号 {tag_type}{number} ({repair_type})")
        
        return notes
    
    def _repair_mismatched_numbers(self, response: str, tag_type: str) -> List[Tuple[str, str]]:
        """修复开闭标签数字不匹配的情况"""
        notes = []
        
        # 寻找数字不匹配的情况
        patterns = [
            # 带星号的数字不匹配：<**type1**>content</type2>
            f'<\\*\\*{tag_type}(\\d+)\\*\\*>(.*?)</\\*\\*{tag_type}\\d+\\*\\*>',
            # 标准格式数字不匹配：<type1>content</type2>
            f'<{tag_type}(\\d+)>(.*?)</{tag_type}\\d+>'
        ]
        
        for pattern in patterns:
            matches = list(re.finditer(pattern, response, re.DOTALL))
            if matches:
                for match in matches:
                    number = match.group(1)
                    content = match.group(2).strip()
                    if content:
                        notes.append((number, content))
                        logger.debug(f"修复数字不匹配 {tag_type}{number}")
        
        return notes
    
    def _extract_fuzzy_matches(self, response: str, tag_type: str) -> List[Tuple[str, str]]:
        """第三级：模糊匹配，最后的手段"""
        notes = []
        
        # 1. 寻找任何包含类型名的可能标签
        fuzzy_pattern = f'(?i).*{tag_type}.*?[:：]\\s*(.*?)(?=\\n|$|<|>)'
        matches = list(re.finditer(fuzzy_pattern, response, re.DOTALL))
        
        if matches:
            for i, match in enumerate(matches, 1):
                content = match.group(1).strip()
                if content and len(content) > 10:  # 模糊匹配要求内容足够长
                    notes.append((str(i), content))
                    logger.debug(f"模糊匹配 {tag_type}{i}")
        
        # 🔧 移除基于关键词的识别，这个逻辑过于激进容易误匹配
        
        return notes
    
    def _clean_duplicate_notes(self, notes: List[Tuple[str, str]], tag_type: str) -> List[Tuple[str, str]]:
        """清理重复的数字和内容"""
        if not notes:
            return []
        
        # 处理数字重复
        number_count = Counter(num for num, _ in notes)
        duplicate_numbers = [num for num, count in number_count.items() if count > 1]
        
        if duplicate_numbers:
            logger.warning(f"{tag_type} 发现重复编号: {duplicate_numbers}")
            # 重新编号
            renumbered_notes = []
            for i, (_, content) in enumerate(notes, 1):
                renumbered_notes.append((str(i), content))
            notes = renumbered_notes
        
        # 处理内容重复
        seen_content = set()
        unique_notes = []
        
        for number, content in notes:
            content_normalized = content.lower().strip()
            if content_normalized not in seen_content:
                seen_content.add(content_normalized)
                unique_notes.append((number, content))
            else:
                logger.debug(f"跳过重复内容 {tag_type}{number}")
        
        return unique_notes
    
    def _clean_content(self, content: str, tag_type: str) -> str:
        """清理内容中的不完整标签和多余符号"""
        if not content:
            return ""
        
        # 移除可能的不完整闭合标签 - 增强版
        content = re.sub(f'</\\*\\*{tag_type}\\d*\\*\\*>?$', '', content)
        content = re.sub(f'</{tag_type}\\d*>?$', '', content)
        content = re.sub(f'</\\*\\*{tag_type}\\*\\*>?$', '', content)
        content = re.sub(f'</{tag_type}>?$', '', content)
        
        # 移除各种不完整的结束标签
        content = re.sub(r'</\w*$', '', content)  # 移除 </word 这样的不完整标签
        content = re.sub(r'</$', '', content)     # 移除 </ 这样的不完整标签
        content = re.sub(r'<$', '', content)      # 移除单独的 < 符号
        
        # 移除多余的符号
        content = re.sub(r'[<>/*]+$', '', content)
        
        # 特殊清理：移除一些常见的无效标签
        # 清理可能出现的错误标签
        invalid_tags = [
            r'</gross-out-of-the-box-questions>',
            r'<gross-out-of-the-box-questions>',
            r'</question-end>',
            r'<question-end>',
            r'</end-question>',
            r'<end-question>'
        ]
        
        for invalid_tag in invalid_tags:
            content = re.sub(invalid_tag, '', content, flags=re.IGNORECASE)
        
        # 清理多余的换行和空格
        content = re.sub(r'\n{3,}', '\n\n', content)  # 多个换行压缩为两个
        content = re.sub(r'^\s+', '', content, flags=re.MULTILINE)  # 移除行首空格
        
        return content.strip()
    
    def _extract_unknown_types(self, response: str) -> Dict[str, List[Tuple[str, str]]]:
        """提取未知类型的标签"""
        unknown_notes = {}
        
        # 寻找所有可能的标签格式
        patterns = [
            r'<\*\*(\w+)(\d+)\*\*>(.*?)</\*\*\1\2\*\*>',  # 带星号带编号
            r'<(\w+)(\d+)>(.*?)</\1\2>',  # 标准带编号
            r'<\*\*(\w+)\*\*>(.*?)</\*\*\1\*\*>',  # 带星号无编号
            r'<(\w+)>(.*?)</\1>'  # 标准无编号
        ]
        
        for pattern in patterns:
            matches = list(re.finditer(pattern, response, re.DOTALL))
            for match in matches:
                groups = match.groups()
                if len(groups) == 3:  # 带编号
                    tag_type, number, content = groups
                    if tag_type not in self.known_types:
                        content = content.strip()
                        if content:
                            if tag_type not in unknown_notes:
                                unknown_notes[tag_type] = []
                            unknown_notes[tag_type].append((number, content))
                            logger.warning(f"发现未知标签类型: {tag_type}{number}")
                elif len(groups) == 2:  # 无编号
                    tag_type, content = groups
                    if tag_type not in self.known_types:
                        content = content.strip()
                        if content:
                            if tag_type not in unknown_notes:
                                unknown_notes[tag_type] = []
                            # 自动编号
                            number = str(len(unknown_notes[tag_type]) + 1)
                            unknown_notes[tag_type].append((number, content))
                            logger.warning(f"发现未知标签类型: {tag_type}{number}")
        
        return unknown_notes


# 创建全局实例
_extractor = RobustNotesExtractor()


def extract_notes(response: str) -> Dict[str, List[Tuple[str, str]]]:
    """
    从响应文本中提取所有XML格式的notes
    
    Args:
        response: Action的输出文本
        
    Returns:
        字典，key为note类型，value为(编号, 内容)的列表
        例如: {"resonant": [("1", "内容1"), ("2", "内容2")]}
    """
    return _extractor.extract_notes(response)


def extract_and_create_notes(response: str, source: str, workspace, expected_types: Optional[List[str]] = None) -> List[str]:
    """
    提取notes并直接添加到workspace
    
    Args:
        response: Action输出
        source: 来源标识
        workspace: WorkSpace实例
        expected_types: 期望的note类型列表，如果提供则只提取这些类型
        
    Returns:
        创建的note id列表
    """
    # 提取notes
    notes_by_type = extract_notes(response)
    
    # 如果指定了期望类型，只保留这些类型
    if expected_types:
        filtered_notes = {}
        for note_type, notes_list in notes_by_type.items():
            if note_type in expected_types:
                filtered_notes[note_type] = notes_list
            else:
                logger.debug(f"跳过非期望类型 {note_type}: {len(notes_list)} 条")
        notes_by_type = filtered_notes
    
    created_ids = []
    
    # 导入AI味句子改写器
    # from core.ai_sentence_reviser import revise_ai_sentences, should_revise_action_type
    
    # 添加到workspace
    for note_type, notes_list in notes_by_type.items():
        # 检查是否需要进行AI味句子改写
        # needs_revision = should_revise_action_type(note_type)
        
        for number, content in notes_list:
            # 对写作类action的notes进行AI味句子改写
            # if needs_revision:
            #     logger.info(f"对 {note_type} 进行AI味句子改写...")
            #     revised_content = revise_ai_sentences(content)
            #     if revised_content != content:
            #         logger.info(f"AI味句子改写完成，内容已优化")
            #         content = revised_content
            #     else:
            #         logger.debug(f"未发现需要改写的AI味句子")
            
            # 创建note
            try:
                note_id = workspace.create_note(note_type, content, source)
                created_ids.append(note_id)
                logger.debug(f"创建note: {note_id} (XML编号: {number})")
            except Exception as e:
                logger.error(f"创建note失败: {e}")
                continue
    
    return created_ids 