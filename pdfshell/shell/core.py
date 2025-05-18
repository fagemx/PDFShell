import time
from rich.console import Console
# from core.engine import run_tool # No longer directly called here
# from tools.loader import load_tools # No longer needed here

# _TOOLS = {t.name: t.description for t in load_tools()} # Remove

# def list_commands(): # Remove
#     return _TOOLS.items()

# def _parse(cmd_line: str): # Remove entire function
#     parts = shlex.split(cmd_line)
#     if not parts:
#         raise ValueError("Empty command")
#     name, opts = parts[0], parts[1:]
#     if name not in _TOOLS:
#         raise ValueError(f"Unknown command: {name}")

#     args = {}
#     i = 0
#     while i < len(opts):
#         opt = opts[i]
#         if opt.startswith("--"):
#             key = opt.lstrip("--")
#             if i + 1 < len(opts) and not opts[i+1].startswith("--"):
#                 current_values = []
#                 i += 1
#                 while i < len(opts) and not opts[i].startswith("--"):
#                     current_values.append(opts[i])
#                     i += 1
                
#                 if not current_values:
#                     raise ValueError(f"Missing value for {key}")

#                 final_value = current_values[0] if len(current_values) == 1 else current_values
                
#                 if key in args: 
#                     if not isinstance(args[key], list):
#                         args[key] = [args[key]]
#                     if isinstance(final_value, list):
#                         args[key].extend(final_value)
#                     else:
#                         args[key].append(final_value)
#                 else:
#                     args[key] = final_value
#                 continue 
#             else: 
#                 raise ValueError(f"Missing value for option {key} or malformed command.")
#         else:
#             raise ValueError(f"Unexpected argument: {opt}. Options must start with --")
#         # i += 1 # This line was problematic in original, should be handled by loop logic
            
#     return name, args

# def execute(cmd_line: str, console: Console): # Remove entire function
#     try:
#         tool, args = _parse(cmd_line)
#         console.print(f"[bold]▶ {tool}[/] {args}")
#         start = time.perf_counter()
#         output = run_tool(tool, args)
#         elapsed = time.perf_counter() - start
#         console.print(f"[green]✅ Done[/] ({elapsed:.2f}s) → {output}")
#     except Exception as e:
#         console.print_exception()

# --- Django Setup ---
# Ensure this is handled appropriately, either here or in manage.py/wsgi.py
# For commands run via shell, Django might need to be initialized.
# The app.py already has Django setup, so it might not be needed here
# if this file only contains utilities.
import os
import django

if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pdfshell_srv.settings')
try:
    if not django.apps.apps.ready and not django.conf.settings.configured:
        django.setup()
except RuntimeError as e: # Could be "Django settings already configured."
    print(f"Django setup in shell/core.py warning/error: {e}")
# --- End Django Setup ---

from apptrace.models import Operation

def fetch_history(limit: int = 10):
    """
    從資料庫獲取操作歷史記錄。
    """
    try:
        operations = Operation.objects.order_by('-created_at')[:limit]
        return operations
    except Exception as e:
        # Log or handle exception appropriately
        # For now, re-raise or return empty list
        print(f"Error fetching history: {e}")
        return []

# Example of how Rich console might be used for history, though app.py will format it
# console_for_history = Console() 
# def display_history_rich(operations):
#     for op in operations:
#         console_for_history.print(f"[bold]{op.created_at:%H:%M:%S}[/] {op.tool} {op.args} {op.out_hash[:6] if op.out_hash else 'N/A'}")

"""
Day 7 變更:
- 移除了 _parse, list_commands, 和 execute 函數，因為 shell/app.py 將使用 make_click_shell
  直接整合 cli/main.py 中的 Click 命令。
- 添加了 fetch_history 函數，用於從 apptrace.models.Operation 查詢操作歷史。
- Django 初始化代碼保留（或調整），以確保在 fetch_history 中可以訪問 ORM。
""" 