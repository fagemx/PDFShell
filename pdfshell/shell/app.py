import django
import os
import sys # Keep sys for quit_command

# --- Django Setup ---
# This setup is crucial for when shell commands (like the new history command)
# need to access Django models. It was present before and should be maintained.
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pdfshell_srv.settings')
try:
    # Check if settings are already configured or apps are ready to avoid re-setup issues.
    if not django.apps.apps.ready and not django.conf.settings.configured:
        django.setup()
except RuntimeError as e:
    print(f"Django setup in shell/app.py warning/error: {e}")
# --- End Django Setup ---

import click # Keep click for @pdfshell.command()
from click_shell import make_click_shell
from rich.console import Console # Keep for formatting history output
# from .core import execute, list_commands # execute and list_commands are no longer needed from core
from .core import fetch_history # Import fetch_history for the new history command
from cli.main import cli as main_cli_group # Import the main cli group from cli/main.py

console = Console() # Keep console for rich output in history

# Create the shell using make_click_shell with the dynamically generated cli group
# The prompt and intro can be customized as before.
# All commands defined in main_cli_group (merge, split, add_stamp, redact, and the CLI's history)
# will now be available in the shell.
pdfshell = make_click_shell(
    main_cli_group, 
    prompt='pdfshell> ', 
    intro='Interactive PDF Shell. Type "help" for available commands or "<command> --help" for command specific help. 注意：所有檔案操作預設相對於專案根目錄下的 \'files/\' 資料夾。'
)

# Add a custom 'history' command to the shell, potentially overriding or supplementing
# the one from main_cli_group if a different presentation is desired in the shell.
# Or, if main_cli_group.history is sufficient, this custom one might not be strictly necessary
# unless shell-specific formatting (like Rich) is a must here instead of in cli.main.history_cmd.
# Day 7 plan: "在 shell/app.py 中新增 history 自訂命令。 history 指令調用 shell/core.py 中的 fetch_history 函數"
# This implies a shell-specific history command.
@pdfshell.command("history")
@click.option('--limit', default=10, type=int, help='要顯示的操作記錄數量 (預設: 10)')
def shell_history(limit):
    """顯示互動式 Shell 中的最近操作歷史記錄。"""
    try:
        operations = fetch_history(limit)
        if not operations:
            console.print("沒有操作歷史記錄可顯示。")
            return

        console.print(f"顯示最近 {len(operations)} 條操作歷史記錄:")
        for op in operations:
            # Using Rich Console for potentially better formatting in the interactive shell
            status = getattr(op, 'status', 'N/A')
            error_msg = getattr(op, 'error_message', '')
            
            console.print(f"- [dim]{op.created_at.strftime('%Y-%m-%d %H:%M:%S')}[/] | [bold cyan]{op.tool:<10}[/] | In: {op.in_hash[:8] if op.in_hash else 'N/A'} | Out: {op.out_hash[:8] if op.out_hash else 'N/A'} | Status: {status}")
            if status == "error" and error_msg:
                # Indent error message slightly
                console.print(f"    [red]Error:[/] {error_msg[:100] + '...' if len(error_msg) > 100 else error_msg}")
    except Exception as e:
        console.print(f"[bold red]查詢歷史記錄時發生錯誤:[/]")
        console.print_exception(show_locals=True) # Rich console can print exception details

# The quit command can remain as part of click-shell or a custom one like this.
# click-shell by default provides `exit` and `quit`.
# If we want to ensure our custom sys.exit behavior:
@pdfshell.command(name='quit')
def custom_quit_command():
    """離開 PDF Shell 互動式環境。"""
    # console.print("正在退出 PDF Shell...") # Using Rich console
    click.echo("正在退出 PDF Shell...") # click.echo is also fine
    sys.exit(0)

# Remove old commands command as 'help' will list all available commands from make_click_shell
# @pdfshell.command()
# def commands():
#     """列出所有可用工具"""
#     for name, desc in list_commands():
#         console.print(f"[cyan]{name}[/] – {desc}")

# Remove old run command as tools are now direct subcommands
# @pdfshell.command(context_settings=dict(ignore_unknown_options=True))
# @click.argument('text', nargs=-1)
# def run(text):
#     """直接輸入整行工具指令"""
#     cmd_line = " ".join(text)
#     execute(cmd_line, console)

if __name__ == "__main__":
    pdfshell()

"""
Day 7 Changes:
- Replaced the manual @shell decorator and `run`, `commands` commands.
- Imported `main_cli_group` from `cli.main`.
- Used `make_click_shell(main_cli_group, ...)` to initialize `pdfshell`.
  This makes all dynamically loaded tools from `cli/main.py` available as direct subcommands in the shell.
- Added a shell-specific `history` command that uses `fetch_history` from `shell.core` 
  and `rich.Console` for output formatting.
- Ensured Django is set up at the beginning for the history command.
- Kept a custom `quit` command for explicit exit behavior.
""" 