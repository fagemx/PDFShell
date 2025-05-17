import click
from core.engine import run_tool
from tools.loader import load_tools # Added for dynamic command loading
import os # For history command
import django # For history command

# Helper function to convert YAML type to Click type
def get_click_type(type_str):
    if type_str == 'str':
        return str
    elif type_str == 'int':
        return int
    elif type_str == 'float':
        return float
    elif type_str == 'bool':
        return bool
    elif type_str.startswith('List['): # e.g. List[str]
        # For List[str], click handles multiple strings by default with multiple=True
        # The inner type (str, int, etc.) will be the type for each item.
        inner_type_str = type_str[5:-1]
        return get_click_type(inner_type_str)
    return str # Default to string if unknown

@click.group()
def cli():
    """PDF Shell: 一個用於 PDF 操作的命令列工具"""
    # Django setup for history command if it remains or for other potential needs
    # Moved Django setup here to ensure it's run once when cli group is initialized
    # if any command (like history) needs it.
    if not os.environ.get('DJANGO_SETTINGS_MODULE'):
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pdfshell_srv.settings')
    try:
        if not django.apps.apps.ready and not django.conf.settings.configured:
            django.setup()
    except RuntimeError as e:
        print(f"Django setup in cli/main.py warning/error: {e}")

# Dynamically load tools and create commands
# This assumes load_tools() returns a list of objects,
# where each object has 'name', 'description', and 'inputs' attributes.
# 'inputs' is a dict: {'param_name': {'type': 'str', 'required': True, 'default': ..., 'help': ..., 'multiple': False}}

tool_specs = load_tools() # Load tool specifications once

for tool_spec in tool_specs:
    # Need to capture tool_spec in a closure for the callback
    # Or define the callback in a way that tool_spec.name is correctly scoped
    def create_command_callback(spec_name):
        def command_callback(**kwargs):
            # Filter out None values for non-required options that were not provided
            # so run_tool receives a cleaner args dict, similar to how individual commands were structured.
            # However, Click by default doesn't pass options that were not provided, unless they have a default.
            # If an option has a default and is not provided, Click passes the default.
            # If it's not required and has no default, and not provided, it's not in kwargs.
            # This seems fine, run_tool should handle args as provided by Click.
            try:
                # Convert args with multiple=True back to lists if Click doesn't do it automatically
                # for dynamically added options (it usually does for tuple types)
                # For example, if 'files' is multiple=True, kwargs['files'] will be a tuple.
                # run_tool expects a list for 'files' in merge.
                processed_args = {}
                input_spec_for_tool = next((ts.inputs for ts in tool_specs if ts.name == spec_name), {})

                for k, v in kwargs.items():
                    # Check if the original spec indicated this should be a list (e.g. from multiple=True)
                    param_meta = input_spec_for_tool.get(k, {})
                    is_list_type = isinstance(param_meta.get('type'), str) and param_meta['type'].startswith('List[')
                    if param_meta.get('multiple') or is_list_type: # or (isinstance(v, tuple) and (param_meta.get('multiple') or is_list_type)):
                        processed_args[k] = list(v) if isinstance(v, tuple) else v # Ensure it's a list
                    else:
                        processed_args[k] = v
                
                result = run_tool(spec_name, processed_args)
                click.echo(f"已成功執行工具 '{spec_name}'. 結果: {result}")
            except Exception as e:
                click.echo(f"執行工具 '{spec_name}' 時發生錯誤: {e}", err=True)
        return command_callback

    # Create the command
    cmd = click.Command(name=tool_spec.name, 
                        callback=create_command_callback(tool_spec.name), 
                        help=tool_spec.description or f"執行 {tool_spec.name} 工具")

    # Add options dynamically in reverse order of definition for consistent help text
    if hasattr(tool_spec, 'inputs') and tool_spec.inputs:
        for param_name, param_meta in reversed(list(tool_spec.inputs.items())):
            original_help = param_meta.get('description', param_meta.get('help'))
            
            # Check if this parameter is a known path key
            # These keys are defined in core/engine.py, we'll hardcode them or pass them if possible
            # For now, hardcoding based on common knowledge from previous steps
            known_path_keys = ['file', 'files', 'stamp_path', 'output', 'output_dir']
            param_help = original_help
            if param_name in known_path_keys:
                warning_text = " (此路徑相對於預設的 'files/' 目錄。請勿嘗試存取 'uploads/' 或其他系統目錄)"
                param_help = f"{original_help}{warning_text}" if original_help else warning_text.strip()


            option_kwargs = {
                'required': param_meta.get('required', False),
                'help': param_help, # Use updated help text
                'default': param_meta.get('default') if param_meta.get('default') is not None else None,
            }
            
            # Determine type and multiple
            param_type_str = param_meta.get('type', 'str')
            is_multiple = param_meta.get('multiple', False) or param_type_str.startswith('List[')
            
            if is_multiple:
                option_kwargs['multiple'] = True
                # Click uses the type for each item in the tuple
                option_kwargs['type'] = get_click_type(param_type_str) if not param_type_str.startswith('List[') else get_click_type(param_type_str[5:-1])

            else:
                option_kwargs['type'] = get_click_type(param_type_str)

            # Remove default from kwargs if it's None, to let Click handle its own default (which is None)
            if option_kwargs['default'] is None:
                del option_kwargs['default']

            # Special handling for boolean flags if they are defined like that
            if option_kwargs.get('type') == bool:
                option_kwargs['is_flag'] = True
                # For flags, default is usually False if not specified
                if 'default' not in option_kwargs:
                     option_kwargs['default'] = False
                # Help text for flags might need adjustment e.g. "Enable feature X" vs "Value for X"
                option_kwargs['help'] = option_kwargs['help'] or f"Enable {param_name}"


            # Add click.option decorator
            # For dynamic creation, we add to command's params list
            # Parameter name for click is --param-name (with dashes)
            click_param_name = f"--{param_name.replace('_', '-')}"
            
            # Need to handle if default is None explicitly for non-required options
            # click.Option handles this correctly.
            
            opt = click.Option([click_param_name], **option_kwargs)
            cmd.params.insert(0, opt) # Insert at beginning to keep reversed order
            
    cli.add_command(cmd)


# The manually defined history command remains as is for now,
# as it's not loaded from a YAML tool spec.
@cli.command("history")
@click.option('--limit', default=10, type=int, help='要顯示的操作記錄數量 (預設: 10)')
def history_cmd(limit):
    """顯示最近的操作歷史記錄"""
    try:
        # Django setup is now at the group level, but ensure it's effective.
        # It should be, as it runs when cli() is invoked or any command is.
        from trace.models import Operation 

        operations = Operation.objects.order_by('-created_at')[:limit]
        if not operations:
            click.echo("沒有操作歷史記錄可顯示。")
            return

        click.echo(f"顯示最近 {len(operations)} 條操作歷史記錄:")
        for op in operations:
            # Adjusted output to match EXECUTION_PLAN_CHECKLIST.md Day 3 history command format more closely if needed
            # And ensure all fields are safely accessed.
            status = getattr(op, 'status', 'N/A') # Assuming 'status' field exists
            error_msg = getattr(op, 'error_message', '')
            
            click.echo(f"- {op.created_at.strftime('%Y-%m-%d %H:%M:%S')} | {op.tool:<10} | In: {op.in_hash[:8] if op.in_hash else 'N/A'} | Out: {op.out_hash[:8] if op.out_hash else 'N/A'} | Status: {status}")
            if status == "error" and error_msg:
                click.echo(f"    Error: {error_msg[:100] + '...' if len(error_msg) > 100 else error_msg}")
    except Exception as e:
        click.echo(f"查詢歷史記錄時發生錯誤: {e}", err=True)

if __name__ == '__main__':
    cli()
