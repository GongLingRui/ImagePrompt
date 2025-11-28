#!/usr/bin/env python3
"""
批量测试模块
支持从CSV文件读取query，批量运行ImagePrompt系统并记录详细信息
"""

import csv
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn

from core import WorkSpace, ConversationManager
from agents import Concierge, Orchestrator, Tactician
from model_base import get_session_stats, reset_session_stats, model_manager, set_current_model

# 配置日志
logger = logging.getLogger(__name__)
console = Console()

class LLMCallRecorder:
    """LLM调用记录器，用于批量测试时记录详细信息"""
    
    def __init__(self):
        self.calls = []
    
    def record_call(self, prompt_type: str, user_prompt: str, response: str, 
                   input_tokens: int, output_tokens: int, thinking_tokens: int, 
                   call_cost: float, total_cost: float):
        """记录一次LLM调用"""
        self.calls.append({
            'timestamp': datetime.now().isoformat(),
            'prompt_type': prompt_type,
            'user_prompt': user_prompt,
            'response': response,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'thinking_tokens': thinking_tokens,
            'call_cost': call_cost,
            'total_cost': total_cost
        })
    
    def get_calls(self) -> List[Dict]:
        """获取所有记录的调用"""
        return self.calls.copy()
    
    def clear(self):
        """清除所有记录"""
        self.calls.clear()

class BatchTestRunner:
    """批量测试运行器"""
    
    def __init__(self):
        self.llm_recorder = LLMCallRecorder()
        self.workspace = None
        self.conversation = None
        self.concierge = None
        self.orchestrator = None
        self.tactician = None
        
        # Monkey patch LLM调用记录
        self._patch_llm_recording()
    
    def _patch_llm_recording(self):
        """修改LLM调用记录，使其记录到我们的记录器而不是显示面板"""
        from model_base import create_llm_panel
        
        # 保存原始函数
        self._original_create_llm_panel = create_llm_panel
        
        # 创建新的记录函数
        def recording_create_llm_panel(prompt_type: str, user_prompt: str, response: str, 
                                     input_tokens: int, output_tokens: int, thinking_tokens: int, 
                                     call_cost: float, total_cost: float):
            """记录LLM调用而不是显示面板"""
            self.llm_recorder.record_call(
                prompt_type, user_prompt, response,
                input_tokens, output_tokens, thinking_tokens,
                call_cost, total_cost
            )
        
        # 替换model_base和kimi_provider中的create_llm_panel
        import model_base
        import kimi_provider

        model_base.create_llm_panel = recording_create_llm_panel
        kimi_provider.create_llm_panel = recording_create_llm_panel

    def _restore_llm_recording(self):
        """恢复原始的LLM记录方式"""
        import model_base
        import kimi_provider

        model_base.create_llm_panel = self._original_create_llm_panel
        kimi_provider.create_llm_panel = self._original_create_llm_panel

    def initialize_system(self):
        """初始化ImagePrompt系统"""
        # 初始化模型系统 - 只用Kimi K2.5
        from kimi_provider import KimiProvider

        model_manager.register_provider(KimiProvider())

        # 设置默认模型为 Kimi K2.5
        set_current_model("kimi-k2.5")
        console.print(f"[dim]🤖 默认模型: Kimi K2.5[/dim]")
        
        # 初始化核心组件
        self.workspace = WorkSpace()
        self.conversation = ConversationManager()
        self.concierge = Concierge(self.workspace, self.conversation)
        self.orchestrator = Orchestrator(self.workspace, self.conversation)
        self.tactician = Tactician(self.workspace, self.conversation)
    
    def read_queries_from_csv(self, csv_path: str) -> List[str]:
        """从CSV文件读取查询，智能处理有/无列标题的情况"""
        queries = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            if not lines:
                console.print(f"[red]❌ CSV文件为空: {csv_path}[/red]")
                return []
            
            # 检查第一行是否是列标题
            first_line = lines[0].strip()
            if first_line.lower() == 'query':
                # 标准格式：有列标题
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if 'query' in row and row['query'].strip():
                            queries.append(row['query'].strip())
                console.print(f"[green]✅ 从 {csv_path} 读取了 {len(queries)} 个查询（标准CSV格式）[/green]")
            else:
                # 简化格式：每行直接是查询内容
                for line in lines:
                    query = line.strip()
                    if query:  # 跳过空行
                        queries.append(query)
                console.print(f"[green]✅ 从 {csv_path} 读取了 {len(queries)} 个查询（简化格式）[/green]")
                
            return queries
        except Exception as e:
            console.print(f"[red]❌ 读取CSV文件失败: {e}[/red]")
            return []
    
    def process_single_query(self, query: str, query_index: int) -> Dict[str, Any]:
        """处理单个查询"""
        console.print(f"[dim]处理查询 {query_index + 1}: {query[:50]}...[/dim]")
        
        # 重置统计和记录
        reset_session_stats()
        self.llm_recorder.clear()
        
        # 重置工作空间和对话管理器
        self.workspace = WorkSpace()
        self.conversation = ConversationManager()
        self.concierge = Concierge(self.workspace, self.conversation)
        self.orchestrator = Orchestrator(self.workspace, self.conversation)
        self.tactician = Tactician(self.workspace, self.conversation)
        
        try:
            start_time = time.time()
            
            # 第一步：处理用户输入
            before_count = len(self.conversation.get_recent_orchestrator_calls(limit=None))
            concierge_response = self.concierge.process_user_input(query)
            after_count = len(self.conversation.get_recent_orchestrator_calls(limit=None))
            
            # 检查是否需要追问
            if "<confirm>" in concierge_response:
                # 自动回复"都行，你来定"
                follow_up_response = self.concierge.process_user_input("都行，你来定")
                concierge_response = follow_up_response
                after_count = len(self.conversation.get_recent_orchestrator_calls(limit=None))
            
            orchestrator_output = ""
            created_notes = []
            
            # 如果触发了Orchestrator
            if after_count > before_count:
                recent_calls = self.conversation.get_recent_orchestrator_calls(1)
                if recent_calls:
                    task_message = recent_calls[0]["message"]
                    
                    # 检查是否需要Tactician分析
                    if not hasattr(self.workspace, 'tactician_analysis') or not self.workspace.tactician_analysis:
                        success = self.tactician.analyze_task(task_message)
                        if success:
                            analysis = self.workspace.tactician_analysis
                            console.print(f"[dim]策略分析: {len(analysis.get('question_notes', []))}个问题Notes[/dim]")
                    
                    # 执行一轮Orchestrator（按要求只运行一轮）
                    execution_log = []
                    result = self.orchestrator.process_task(task_message, execution_log)
                    
                    orchestrator_output = result["response"]
                    
                    # 执行commands
                    if result["execute_commands"]:
                        for cmd_idx, cmd in enumerate(result["execute_commands"]):
                            from agents.orchestrator import execute
                            step_result = execute(
                                cmd['action'],
                                cmd['instruction'],
                                self.workspace,
                                self.conversation
                                # orchestrator=self.orchestrator  # 注释掉reflection相关参数
                            )
                            
                            execution_log.append({
                                "iteration": 1,
                                "command_index": cmd_idx,
                                "action": cmd['action'],
                                "instruction": cmd['instruction'],
                                "result": step_result
                            })
                            
                            created_notes.extend(step_result.get('notes_created', []))
            
            end_time = time.time()
            
            # 获取最终统计
            final_stats = get_session_stats()
            
            # 获取创建的内容
            final_content = ""
            if created_notes:
                for note_id in created_notes[-3:]:  # 最后3个notes
                    note = self.workspace.get_note(note_id)
                    if note:
                        final_content += f"@{note_id}: {note['content']}\n\n"
            
            # 返回结果
            return {
                'query': query,
                'query_index': query_index,
                'concierge_response': concierge_response,
                'orchestrator_output': orchestrator_output,
                'final_content': final_content.strip(),
                'created_notes': created_notes,
                'execution_time': end_time - start_time,
                'stats': final_stats,
                'llm_calls': self.llm_recorder.get_calls(),
                'success': True,
                'error': None
            }
            
        except Exception as e:
            console.print(f"[red]❌ 处理查询失败: {e}[/red]")
            return {
                'query': query,
                'query_index': query_index,
                'concierge_response': "",
                'orchestrator_output': "",
                'final_content': "",
                'created_notes': [],
                'execution_time': 0,
                'stats': get_session_stats(),
                'llm_calls': self.llm_recorder.get_calls(),
                'success': False,
                'error': str(e)
            }
    
    def run_batch_test(self, csv_path: str, output_path: Optional[str] = None) -> str:
        """运行批量测试"""
        try:
            # 读取查询
            queries = self.read_queries_from_csv(csv_path)
            if not queries:
                return ""
            
            # 初始化系统
            self.initialize_system()
            
            # 生成输出文件名
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"batch_test_results_{timestamp}.csv"
            
            results = []
            total_stats = {
                'total_calls': 0,
                'total_input_tokens': 0,
                'total_output_tokens': 0,
                'total_thinking_tokens': 0,
                'total_cost': 0.0
            }
            
            # 处理每个查询
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("批量测试进行中...", total=len(queries))
                
                for i, query in enumerate(queries):
                    result = self.process_single_query(query, i)
                    results.append(result)
                    
                    # 累积统计
                    stats = result['stats']
                    total_stats['total_calls'] += stats['total_calls']
                    total_stats['total_input_tokens'] += stats['total_input_tokens']
                    total_stats['total_output_tokens'] += stats['total_output_tokens']
                    total_stats['total_thinking_tokens'] += stats['total_thinking_tokens']
                    total_stats['total_cost'] += stats['total_cost']
                    
                    progress.advance(task)
            
            # 导出结果
            self._export_results(results, total_stats, output_path)
            
            return output_path
            
        except Exception as e:
            console.print(f"[red]❌ 批量测试失败: {e}[/red]")
            return ""
        finally:
            # 恢复原始LLM记录方式
            self._restore_llm_recording()
    
    def _export_results(self, results: List[Dict], total_stats: Dict, output_path: str):
        """导出结果为CSV"""
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                # 准备CSV列
                fieldnames = [
                    'query_index', 'query', 'success', 'error',
                    'concierge_response', 'orchestrator_output', 'final_content',
                    'created_notes_count', 'execution_time',
                    'llm_calls_count', 'input_tokens', 'output_tokens', 'thinking_tokens', 'cost',
                    'llm_calls_detail'  # JSON格式的详细信息
                ]
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in results:
                    # 准备LLM调用详情
                    llm_calls_detail = []
                    for call in result['llm_calls']:
                        llm_calls_detail.append({
                            'prompt_type': call['prompt_type'],
                            'input_tokens': call['input_tokens'],
                            'output_tokens': call['output_tokens'],
                            'thinking_tokens': call['thinking_tokens'],
                            'cost': call['call_cost'],
                            'user_prompt_length': len(call['user_prompt']),
                            'response_length': len(call['response'])
                        })
                    
                    writer.writerow({
                        'query_index': result['query_index'] + 1,
                        'query': result['query'],
                        'success': result['success'],
                        'error': result['error'] or '',
                        'concierge_response': result['concierge_response'],
                        'orchestrator_output': result['orchestrator_output'],
                        'final_content': result['final_content'],
                        'created_notes_count': len(result['created_notes']),
                        'execution_time': f"{result['execution_time']:.2f}s",
                        'llm_calls_count': len(result['llm_calls']),
                        'input_tokens': result['stats']['total_input_tokens'],
                        'output_tokens': result['stats']['total_output_tokens'],
                        'thinking_tokens': result['stats']['total_thinking_tokens'],
                        'cost': f"${result['stats']['total_cost']:.4f}",
                        'llm_calls_detail': json.dumps(llm_calls_detail, ensure_ascii=False)
                    })
            
            # 显示总结
            success_count = sum(1 for r in results if r['success'])
            console.print(Panel(
                f"[bold green]✅ 批量测试完成！[/bold green]\n\n"
                f"• 总查询数: {len(results)}\n"
                f"• 成功: {success_count}\n"
                f"• 失败: {len(results) - success_count}\n"
                f"• 总LLM调用: {total_stats['total_calls']}\n"
                f"• 总Token: {total_stats['total_input_tokens'] + total_stats['total_output_tokens'] + total_stats['total_thinking_tokens']:,}\n"
                f"• 总费用: [yellow]${total_stats['total_cost']:.4f}[/yellow]\n\n"
                f"[dim]结果已保存到: {output_path}[/dim]",
                title="批量测试结果",
                border_style="green"
            ))
            
        except Exception as e:
            console.print(f"[red]❌ 导出结果失败: {e}[/red]") 