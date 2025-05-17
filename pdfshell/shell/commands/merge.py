import click
from ..core import execute

@click.command()
@click.argument("cmd_line", nargs=-1)
def merge(cmd_line):
    """手動呼叫 merge（等同 run）"""
    # 在 click.get_current_context().obj 中獲取 console
    # 這需要在 shell/app.py 中設定
    # @shell decorator 的 context_settings 參數可以傳遞 obj
    # 例如 @shell(prompt='pdfshell> ', context_settings={'obj': {'console': console}})
    # 不過 click-shell 的文件對於如何正確傳遞和訪問 obj 不夠清晰
    # DAY6.md 的範例中 console 是全域變數，這裡暫時先移除 console 的傳遞
    # 實際執行時，需要確保 execute 函數能獲取到 console 物件
    # 一個簡單的方式是將 console 也設為 core.py 的全域變數或傳遞給 execute
    # 為了符合 DAY6.md 的結構，我們假設 execute 可以自行處理 console
    # 或是在 app.py 的 execute 調用中傳入
    current_ctx = click.get_current_context(silent=True)
    console_obj = None
    if current_ctx and hasattr(current_ctx, 'obj') and current_ctx.obj and 'console' in current_ctx.obj:
        console_obj = current_ctx.obj['console']
    
    if console_obj:
        execute("merge " + " ".join(cmd_line), console_obj)
    else:
        # Fallback or error handling if console is not found
        # For Day 6, app.py's run command passes console directly.
        # This direct command might not have it unless set up in context.
        # For simplicity, we'll assume execute can handle it or we improve context passing later.
        # Reverting to a simpler call as per Day 6 spirit, though context passing is better.
        from ..app import console as global_console # Accessing app's global console as a fallback
        execute("merge " + " ".join(cmd_line), global_console) 