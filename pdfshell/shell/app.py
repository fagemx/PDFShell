import django
import os
import sys # Keep sys for quit_command

# --- Django Setup ---
# Ensure DJANGO_SETTINGS_MODULE is set *before* importing parts of Django or calling setup.
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pdfshell_srv.settings')

# Configure Django settings and populate the app registry.
# This must be done before accessing django.apps or models.
# We check if settings are already configured to avoid re-running setup if this module is imported multiple times
# or if setup was done elsewhere.
# The original error "AttributeError: module 'django' has no attribute 'apps'" suggests that
# 'django.conf' itself or 'django.conf.settings' might not be fully available before setup.
# A more robust check is to see if 'django.setup()' itself has run.
# However, the standard way is to check settings.configured.
# If 'django.conf' or 'django.conf.settings' are problematic before setup,
# then a simple 'import django; django.setup()' (after setting env var) is common.
try:
    # It's crucial that django.setup() is called before further Django-dependent imports or attribute access.
    # We check settings.configured to prevent re-initialization if already done.
    if not django.conf.settings.configured:
        django.setup()
except AttributeError:
    # This case handles if django.conf or django.conf.settings isn't available yet,
    # which implies setup hasn't run and django is in a minimal state.
    django.setup()
except Exception as e: # Catch a broader range of exceptions during setup
    print(f"Error during Django setup in shell/app.py: {e}")
    # Depending on the severity, you might want to re-raise or sys.exit
    raise # Re-raise the exception to see the full traceback if setup fails critically
# --- End Django Setup ---

import click # Keep click for @pdfshell.command()
from click_shell import make_click_shell
import click_shell.core # Explicitly import to check its path
# from rich.console import Console # No longer needed if shell_history is removed
# from .core import fetch_history # No longer needed if shell_history is removed
from cli.main import cli as main_cli_group # Import the main cli group from cli/main.py

# DEBUGGING: Print the path of the loaded click_shell.core module
print(f"DEBUG_SHELL_APP: Path of click_shell.core module: {click_shell.core.__file__}")

# console = Console() # No longer needed if shell_history is removed

# DEBUGGING: Check types before make_click_shell
print(f"DEBUG_SHELL_APP: Type of main_cli_group: {type(main_cli_group)}")
print(f"DEBUG_SHELL_APP: Is main_cli_group a click.BaseCommand? {isinstance(main_cli_group, click.BaseCommand)}")
print(f"DEBUG_SHELL_APP: Is main_cli_group a click.Group? {isinstance(main_cli_group, click.Group)}")
print(f"DEBUG_SHELL_APP: Type of click.Context: {type(click.Context)}")

# Create a click.Context for main_cli_group
# The info_name can be the command name or a generic name like 'cli' or 'pdfshell'
# Ensure any necessary parent context or extra args are handled if needed, but for basic use this is typical.
ctx_for_shell = click.Context(main_cli_group, info_name=main_cli_group.name or 'pdfshell')
print(f"DEBUG_SHELL_APP: Type of created ctx_for_shell: {type(ctx_for_shell)}")

# Create the shell using make_click_shell with the dynamically generated cli group
# The prompt and intro can be customized as before.
# All commands defined in main_cli_group (merge, split, add_stamp, redact, and the CLI's history)
# will now be available in the shell.
pdfshell = make_click_shell(
    ctx_for_shell,  # <--- Pass the created context here
    prompt='pdfshell> ', 
    intro='Interactive PDF Shell. Type "help" for available commands or "<command> --help" for command specific help. 注意：所有檔案操作預設相對於專案根目錄下的 \'files/\' 資料夾。'
)

# Add a custom 'history' command to the shell, potentially overriding or supplementing
# the one from main_cli_group if a different presentation is desired in the shell.
# Or, if main_cli_group.history is sufficient, this custom one might not be strictly necessary
# unless shell-specific formatting (like Rich) is a must here instead of in cli.main.history_cmd.
# Day 7 plan: "在 shell/app.py 中新增 history 自訂命令。 history 指令調用 shell/core.py 中的 fetch_history 函數"
# This implies a shell-specific history command.
# Removing custom shell_history as main_cli_group should provide it.
# @pdfshell.command("history")
# @click.option('--limit', default=10, type=int, help='要顯示的操作記錄數量 (預設: 10)')
# def shell_history(limit):
#     """顯示互動式 Shell 中的最近操作歷史記錄。"""
#     try:
#         operations = fetch_history(limit)
#         if not operations:
#             console.print("沒有操作歷史記錄可顯示。")
#             return
# 
#         console.print(f"顯示最近 {len(operations)} 條操作歷史記錄:")
#         for op in operations:
#             # Using Rich Console for potentially better formatting in the interactive shell
#             status = getattr(op, 'status', 'N/A')
#             error_msg = getattr(op, 'error_message', '')
#             
#             console.print(f"- [dim]{op.created_at.strftime('%Y-%m-%d %H:%M:%S')}[/] | [bold cyan]{op.tool:<10}[/] | In: {op.in_hash[:8] if op.in_hash else 'N/A'} | Out: {op.out_hash[:8] if op.out_hash else 'N/A'} | Status: {status}")
#             if status == "error" and error_msg:
#                 # Indent error message slightly
#                 console.print(f"    [red]Error:[/] {error_msg[:100] + '...' if len(error_msg) > 100 else error_msg}")
#     except Exception as e:
#         console.print(f"[bold red]查詢歷史記錄時發生錯誤:[/]")
#         console.print_exception(show_locals=True) # Rich console can print exception details

# The quit command can remain as part of click-shell or a custom one like this.
# click-shell by default provides `exit` and `quit`.
# Removing custom_quit_command as click-shell provides default quit/exit behavior.
# If custom sys.exit behavior is strictly needed, it would require a different integration method.
# @pdfshell.command(name='quit') # This will also cause an AttributeError
# def custom_quit_command():
#     """離開 PDF Shell 互動式環境。"""
#     # console.print("正在退出 PDF Shell...") # Using Rich console
#     click.echo("正在退出 PDF Shell...") # click.echo is also fine
#     sys.exit(0)

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
    pdfshell.cmdloop()

"""
Day 7 Changes:
- Replaced the manual @shell decorator and `run`, `commands` commands.
- Imported `main_cli_group` from `cli.main`.
- Used `make_click_shell(ctx_for_shell, ...)` to initialize `pdfshell`, passing a Context.
  This makes all dynamically loaded tools from `cli/main.py` available as direct subcommands in the shell.
- Removed shell-specific `history` command; assuming `main_cli_group` provides it.
- Ensured Django is set up at the beginning for the history command (if used from main_cli_group).
- Removed custom `quit` command; relying on click-shell default.
""" 