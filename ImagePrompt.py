#!/usr/bin/env python3

import argparse
import logging
import sys
import threading
import time
from pathlib import Path
from queue import Queue, Empty
from threading import Lock, Event
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from core import WorkSpace, ConversationManager
from agents import Concierge, Orchestrator, Tactician
from model_base import get_session_stats, model_manager, set_current_model, get_current_model_name
from kimi_provider import KimiProvider
from dynamic_loading import show_dynamic_loading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('imageprompt.log')]
)
logger = logging.getLogger(__name__)

# Rich console
console = Console()


class ImagePromptCLI:
    """ImagePrompt CLI"""

    def __init__(self):
        # 初始化模型系统
        self._initialize_models()

        # 初始化核心组件
        self.workspace = WorkSpace()
        self.conversation = ConversationManager()
        self.concierge = Concierge(self.workspace, self.conversation)
        self.orchestrator_running = False

        # 初始化Orchestrator
        self.orchestrator = Orchestrator(
            self.workspace,
            self.conversation
        )
        self.tactician = Tactician(self.workspace, self.conversation)

        # 任务队列和线程管理
        self._task_queue = Queue()
        self._task_lock = Lock()
        self._current_task_event = Event()
        self._current_task_hash = None  # 用于检测任务变化
        self._orchestrator_thread = None
        self._shutdown_event = Event()

    def _initialize_models(self):
        """初始化模型系统"""
        try:
            # 只注册Kimi K2.5模型
            kimi_provider = KimiProvider()
            model_manager.register_provider(kimi_provider)
            set_current_model("kimi-k2.5")
        except Exception as e:
            logger.error(f"❌ 模型系统初始化失败: {e}")
            raise

    def _is_different_task(self, new_task: str) -> bool:
        """检测是否切换到了完全不同的任务"""
        if self._current_task_hash is None:
            return False
        # 简单的任务相似度检测：检查关键词重叠度
        import re
        new_words = set(re.findall(r'\w+', new_task.lower()))
        old_words = set(re.findall(r'\w+', self._current_task_hash.lower()))
        if not new_words or not old_words:
            return True
        overlap = len(new_words & old_words)
        # 如果重叠度低于50%，认为是不同任务
        return overlap < min(len(new_words), len(old_words)) * 0.5

    def _clear_tactician_if_needed(self, task_message: str):
        """如果检测到任务变化，清除Tactician分析结果"""
        if self._is_different_task(task_message):
            logger.info(f"检测到任务变化，清除旧的Tactician分析")
            self.workspace.tactician_analysis = {}

    def _set_current_task(self, task_message: str):
        """设置当前任务哈希"""
        self._current_task_hash = task_message

    def _queue_task(self, task_message: str):
        """将任务加入队列"""
        with self._task_lock:
            self._task_queue.put(task_message)

    def _run_orchestrator_internal(self, task_message: str):
        """Orchestrator内部执行逻辑"""
        try:
            self.orchestrator_running = True
            self.conversation.set_orchestrator_running(True)
            console.print("\n[cyan]🎯 Orchestrator 开始执行任务...[/cyan]\n")

            # Tactician策略分析 - 检测任务变化
            self._clear_tactician_if_needed(task_message)
            if not self.workspace.tactician_analysis:
                console.print("[dim]🤔 启动Tactician策略分析...[/dim]")
                success = self.tactician.analyze_task(task_message)
                if success:
                    analysis = self.workspace.tactician_analysis
                    strategy_count = len(analysis.get('strategy_notes', []))
                    console.print(f"[green]✅ 策略分析完成: {strategy_count}个策略Notes[/green]")
                else:
                    console.print("[yellow]⚠️ Tactician分析未产生有效结果，继续执行[/yellow]")

            # ReAct循环
            execution_log = []
            max_iterations = 3  # 最多3轮
            completed = False

            for iteration in range(max_iterations):
                # 调用Orchestrator
                result = self.orchestrator.process_task(task_message, execution_log)

                # 检查是否完成
                if result["completed"]:
                    completed = True
                    console.print("\n[bold green]🎉 任务已完成！[/bold green]\n")
                    break

                # 执行所有命令
                round_notes = []  # 收集本轮创建的notes
                if result["execute_commands"]:
                    # 循环执行所有命令
                    for cmd_idx, cmd in enumerate(result["execute_commands"]):
                        console.print(f"[dim]执行命令 {cmd_idx + 1}/{len(result['execute_commands'])}: {cmd['action']}[/dim]")

                        # 执行步骤
                        from agents.orchestrator import execute
                        step_result = execute(
                            cmd['action'],
                            cmd['instruction'],
                            self.workspace,
                            self.conversation
                        )

                        # 记录执行结果
                        execution_log.append({
                            "iteration": iteration + 1,
                            "command_index": cmd_idx,
                            "action": cmd['action'],
                            "instruction": cmd['instruction'],
                            "result": step_result
                        })

                        # 收集本轮创建的notes
                        round_notes.extend(step_result.get('notes_created', []))

                        if not step_result['success']:
                            console.print(f"[red]❌ 步骤执行失败: {step_result.get('error')}[/red]")

                # 每轮执行完后，更新execution_record的notes信息
                if round_notes:
                    self.conversation.update_latest_execution_notes(round_notes)

            # 达到最大轮次
            if not completed and iteration == max_iterations - 1:
                console.print("[yellow]⚠️ 达到最大执行轮次[/yellow]")

            # 显示创建的notes
            all_notes_created = []
            for log in execution_log:
                all_notes_created.extend(log['result'].get('notes_created', []))

            if all_notes_created:
                console.print("\n[bold cyan]📝 创建的内容：[/bold cyan]")

                # 按状态分类显示notes
                star_notes = []
                archive_notes = []
                trash_notes = []
                unreviewed_notes = []

                # 分类所有notes
                for note_id in all_notes_created:
                    note = self.workspace.get_note(note_id)
                    if note:
                        status = note.get("review_status")
                        if status == "star":
                            star_notes.append((note_id, note))
                        elif status == "archive":
                            archive_notes.append((note_id, note))
                        elif status == "trash":
                            trash_notes.append((note_id, note))
                        else:
                            unreviewed_notes.append((note_id, note))

                # 显示star notes（金色边框）
                if star_notes:
                    console.print("\n[bold yellow]⭐ 高价值内容：[/bold yellow]")
                    for note_id, note in star_notes:
                        content = note["content"]
                        display_content = '\n'.join(line.strip() for line in content.split('\n') if line.strip())

                        console.print(Panel(
                            display_content,
                            title=f"[bold yellow]⭐ @{note_id}[/bold yellow]",
                            border_style="yellow"
                        ))

                # 显示archive notes（正常蓝色边框）
                if archive_notes:
                    if star_notes:
                        console.print("\n[dim]📝 保留内容：[/dim]")
                    for note_id, note in archive_notes:
                        content = note["content"]
                        display_content = '\n'.join(line.strip() for line in content.split('\n') if line.strip())

                        console.print(Panel(
                            display_content,
                            title=f"[blue]@{note_id}[/blue]",
                            border_style="blue"
                        ))

                # 显示未评审notes（正常蓝色边框）
                if unreviewed_notes:
                    if star_notes or archive_notes:
                        console.print("\n[dim]📄 未评审内容：[/dim]")
                    for note_id, note in unreviewed_notes:
                        content = note["content"]
                        display_content = '\n'.join(line.strip() for line in content.split('\n') if line.strip())

                        console.print(Panel(
                            display_content,
                            title=f"[blue]@{note_id}[/blue]",
                            border_style="blue"
                        ))

                # 显示trash notes作为警示（红色边框）
                if trash_notes:
                    console.print("\n[bold red]🗑️ 质量问题警示：[/bold red]")
                    for note_id, note in trash_notes:
                        comment = note.get("review_comment", "质量问题")
                        console.print(Panel(
                            f"[red]⚠️ {comment}[/red]",
                            title=f"[red]🗑️ @{note_id}[/red]",
                            border_style="red"
                        ))

            # 显示总统计信息
            stats = get_session_stats()
            # 计算各种token统计
            thinking_tokens = stats['total_thinking_tokens']
            billable_tokens = stats['total_input_tokens'] + stats['total_output_tokens']
            total_tokens = billable_tokens + thinking_tokens

            stats_text = f"[bold cyan]📊 本次执行统计：[/bold cyan]\n"
            stats_text += f"• LLM调用次数: {stats['total_calls']}\n"
            stats_text += f"• 输入Token: {stats['total_input_tokens']:,}\n"
            stats_text += f"• 输出Token: {stats['total_output_tokens']:,}\n"
            if thinking_tokens > 0:
                stats_text += f"• 思考Token: {thinking_tokens:,} (按输出价格计费)\n"
            stats_text += f"• 计费Token: {stats['total_input_tokens'] + stats['total_output_tokens'] + thinking_tokens:,}\n"
            stats_text += f"• 总Token: {total_tokens:,}\n"
            stats_text += f"• 总费用: [bold yellow]${stats['total_cost']:.4f}[/bold yellow]"

            console.print("\n" + "─" * 80)
            console.print(Panel(
                stats_text,
                title="[bold green]✨ Orchestrator执行完成！[/bold green]",
                border_style="green"
            ))
            console.print("[dim]您可以继续输入新的需求或查看创建的内容[/dim]")
            console.print("[dim]请输入您的下一个需求...[/dim]\n")

        except Exception as e:
            logger.error(f"Orchestrator执行失败: {str(e)}", exc_info=True)
            console.print(f"[red]❌ 执行出错: {str(e)}[/red]")
        finally:
            self.orchestrator_running = False
            self.conversation.set_orchestrator_running(False)
            # 处理队列中的下一个任务
            self._process_next_in_queue()

    def _process_next_in_queue(self):
        """处理队列中的下一个任务"""
        with self._task_lock:
            try:
                # 检查队列中是否有待处理的任务
                while not self._task_queue.empty():
                    next_task = self._task_queue.get_nowait()
                    # 如果有关闭事件信号，停止处理
                    if next_task is None or self._shutdown_event.is_set():
                        return
                    # 启动新线程执行任务
                    self._orchestrator_thread = threading.Thread(
                        target=self._run_orchestrator_internal,
                        args=(next_task,),
                        daemon=False
                    )
                    self._orchestrator_thread.start()
                    return
            except Empty:
                pass

    def run_orchestrator_async(self, task_message: str):
        """异步运行Orchestrator - 带任务队列"""
        # 先检测任务变化（需要在设置当前任务之前）
        self._clear_tactician_if_needed(task_message)

        with self._task_lock:
            # 设置当前任务
            self._set_current_task(task_message)

            # 如果已经有线程在运行，加入队列
            if self._orchestrator_thread is not None and self._orchestrator_thread.is_alive():
                self._queue_task(task_message)
                console.print("[dim]📝 任务已加入队列，等待执行...[/dim]")
                return

            # 启动新线程
            self._orchestrator_thread = threading.Thread(
                target=self._run_orchestrator_internal,
                args=(task_message,),
                daemon=False  # 改为非守护线程，确保完整执行
            )
            self._orchestrator_thread.start()

    def handle_user_input(self, user_input: str):
        """处理用户输入"""
        # 记录当前orchestrator调用数量
        before_count = len(self.conversation.get_recent_orchestrator_calls(limit=None))

        # 将输入传递给Concierge
        response = self.concierge.process_user_input(user_input)
        console.print(f"\n[bold blue]🤖 Lumina[/bold blue]: [italic]{response}[/italic]")

        # 检查是否有新的orchestrator调用
        after_count = len(self.conversation.get_recent_orchestrator_calls(limit=None))

        if after_count > before_count:
            # 有新的orchestrator调用
            # 设置最新的orchestrator调用为活跃状态
            self.conversation.set_active_orchestrator_call(after_count - 1)

            if self.orchestrator_running:
                # Orchestrator正在运行，新需求会被自动感知
                console.print("\n[dim]📨 已将您的新需求传递给正在执行的Orchestrator[/dim]")
                console.print(Panel.fit(
                    "[yellow]⏳ Orchestrator仍在执行中...[/yellow]\n"
                    "[dim]执行完成后会显示提示[/dim]",
                    border_style="yellow"
                ))
            else:
                # 需要启动Orchestrator
                recent_calls = self.conversation.get_recent_orchestrator_calls(1)
                if recent_calls:
                    task_message = recent_calls[0]["message"]
                    console.print("\n[cyan]🎯 Orchestrator 唤醒中...[/cyan]\n")
                    self.run_orchestrator_async(task_message)
        else:
            # 没有触发orchestrator，普通对话
            if self.orchestrator_running:
                console.print(Panel.fit(
                    "[dim]💬 与Concierge的对话[/dim]\n"
                    "[yellow]Orchestrator仍在后台执行中...[/yellow]",
                    border_style="dim"
                ))

    def run_batch_test(self, csv_path: str):
        """运行批量测试"""
        from batch_test import BatchTestRunner

        # 检查CSV文件是否存在
        if not Path(csv_path).exists():
            console.print(f"[red]❌ CSV文件不存在: {csv_path}[/red]")
            return

        # 确认批量测试
        console.print(f"\n[yellow]📋 批量测试模式[/yellow]")
        console.print(f"输入文件: {csv_path}")

        if not Confirm.ask("确认开始批量测试？"):
            console.print("[yellow]已取消批量测试[/yellow]")
            return

        # 运行批量测试
        runner = BatchTestRunner()
        output_path = runner.run_batch_test(csv_path)

        if output_path:
            console.print(f"\n[green]✅ 批量测试完成，结果保存到: {output_path}[/green]")
        else:
            console.print(f"\n[red]❌ 批量测试失败[/red]")

    def run(self, args=None):
        """主循环"""
        # 如果是批量测试模式
        if args and hasattr(args, 'batch') and args.batch:
            self.run_batch_test(args.batch)
            return

        # 显示动态加载效果
        show_dynamic_loading()

        # 显示当前模型（固定为Kimi K2.5）
        current_model = get_current_model_name()
        console.print(f"\n[dim]🤖 当前模型: {current_model}[/dim]")
        console.print("[dim]开始对话...[/dim]\n")

        # 主循环
        while True:
            try:
                # 获取用户输入
                console.print()
                user_input = Prompt.ask("[bold green]💬 You[/bold green]").strip()
                if not user_input:
                    continue

                # 处理退出命令
                if user_input.lower() in ['exit', 'quit', 'bye', '退出']:
                    # 等待Orchestrator线程结束
                    self._shutdown_event.set()
                    if self._orchestrator_thread and self._orchestrator_thread.is_alive():
                        console.print("[dim]等待Orchestrator线程结束...[/dim]")
                        self._orchestrator_thread.join(timeout=5)
                    console.print("\n[yellow]感谢使用Lumina，再见！[/yellow]")
                    break

                # 处理帮助命令
                if user_input.lower() in ['help', '帮助']:
                    self.show_help()
                    continue

                # 处理状态命令
                if user_input.lower() in ['status', '状态']:
                    self.show_status()
                    continue

                # 处理批量测试命令
                if user_input.lower() in ['batch', '批量测试']:
                    csv_path = Prompt.ask("[bold green]请输入CSV文件路径[/bold green]")
                    if csv_path:
                        self.run_batch_test(csv_path)
                    continue

                # 处理普通输入
                self.handle_user_input(user_input)

            except KeyboardInterrupt:
                console.print("\n[yellow]⚠️  已中断当前操作[/yellow]")
                continue
            except Exception as e:
                console.print(Panel(
                    f"[red]发生错误: {str(e)}[/red]",
                    title="❌ 错误",
                    border_style="red"
                ))
                logger.error(f"主循环错误: {str(e)}", exc_info=True)

    def show_help(self):
        """显示帮助信息"""
        help_panel = Panel(
            "[bold]基本命令：[/bold]\n"
            "• exit/quit - 退出程序\n"
            "• help - 显示此帮助\n"
            "• status - 显示系统状态\n"
            "• batch - 启动批量测试模式\n\n"
            "[bold]使用说明：[/bold]\n"
            "• 直接输入您的需求\n"
            "• LLM调用详情会自动显示\n"
            "• 使用 @note_id 引用已创建的内容\n\n"
            "[bold]批量测试：[/bold]\n"
            "• 使用 --batch <csv_path> 启动批量模式\n"
            "• CSV文件需要包含 'query' 列\n"
            "• 结果会自动保存为新的CSV文件",
            title="[bold cyan]📖 帮助信息[/bold cyan]",
            border_style="cyan"
        )
        console.print(help_panel)

    def show_status(self):
        """显示当前状态"""
        status_info = []

        # 当前模型
        current_model = get_current_model_name()
        if current_model:
            status_info.append(f"• 当前模型: {current_model}")
        else:
            status_info.append("[red]• 当前模型: 未设置[/red]")

        # Orchestrator状态
        if self.orchestrator_running:
            status_info.append("[green]• Orchestrator: 运行中[/green]")
        else:
            status_info.append("[dim]• Orchestrator: 空闲[/dim]")

        # Notes统计
        notes_count = len(self.workspace.notes)
        status_info.append(f"• Notes数量: {notes_count}")

        # 队列状态
        queue_size = self._task_queue.qsize()
        if queue_size > 0:
            status_info.append(f"[yellow]• 待处理任务: {queue_size}[/yellow]")

        # Token使用统计
        stats = get_session_stats()
        if stats['total_calls'] > 0:
            thinking_tokens = stats['total_thinking_tokens']
            billable_tokens = stats['total_input_tokens'] + stats['total_output_tokens']
            total_tokens = billable_tokens + thinking_tokens

            status_info.append("")
            status_info.append("[bold cyan]💰 Token使用统计:[/bold cyan]")
            status_info.append(f"• LLM调用次数: {stats['total_calls']}")
            status_info.append(f"• 输入Token: {stats['total_input_tokens']:,}")
            status_info.append(f"• 输出Token: {stats['total_output_tokens']:,}")
            if thinking_tokens > 0:
                status_info.append(f"• 思考Token: {thinking_tokens:,} (按输出价格计费)")
            status_info.append(f"• 计费Token: {stats['total_input_tokens'] + stats['total_output_tokens'] + thinking_tokens:,}")
            status_info.append(f"• 总Token: {total_tokens:,}")
            status_info.append(f"• 总费用: [yellow]${stats['total_cost']:.4f}[/yellow]")

        status_panel = Panel(
            "\n".join(status_info),
            title="[bold cyan]📊 系统状态[/bold cyan]",
            border_style="cyan"
        )
        console.print(status_panel)


def main():
    """主函数"""
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(
            description="ImagePrompt - 多Agent AI图像提示词生产系统",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
使用示例:
  python ImagePrompt.py                    # 正常交互模式
  python ImagePrompt.py --batch test.csv   # 批量测试模式

批量测试说明:
  CSV文件格式: 只需要一个 'query' 列，包含要测试的查询
  输出: 自动生成带时间戳的结果CSV文件，包含详细的LLM调用记录
            """
        )
        parser.add_argument(
            '--batch', '-b',
            type=str,
            help='批量测试模式：指定包含query列的CSV文件路径'
        )

        args = parser.parse_args()

        # 创建CLI实例并运行
        cli = ImagePromptCLI()
        cli.run(args)

    except Exception as e:
        logger.error(f"程序错误: {str(e)}", exc_info=True)
        console.print(f"\n[red]程序错误: {str(e)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
