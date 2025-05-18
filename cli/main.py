import click
from core.engine import run_tool
from tools.loader import load_tools # Added for dynamic command loading
import os # For history command
import django # For history command
from typing import Union, get_args, List, Optional, Any, get_origin # Ensure this is present
import sys # Added for debug prints

# Helper function to convert YAML type to Click type
# This function might need adjustment if types are now actual Python types from Pydantic
def get_click_type(type_obj):
    # isinstance checks for actual types
    if type_obj == str:
        return str
    elif type_obj == int:
        return int
    elif type_obj == float:
        return float
    elif type_obj == bool:
        return bool
    if hasattr(type_obj, '__origin__') and hasattr(type_obj, '__args__'): # Checks for generic types like List[str]
        if type_obj.__origin__ == list and type_obj.__args__:
            return get_click_type(type_obj.__args__[0]) # Recursive call for inner type
    return str # Default to string if unknown or complex

@click.group()
def cli():
    """PDF Shell: 一個用於 PDF 操作的命令列工具"""
    pass

# Dynamically load tools and create commands
tool_specs = load_tools() # Load tool specifications once

for tool_spec in tool_specs:
    def create_command_callback(spec_name):
        def command_callback(**kwargs):
            # Auto-convert all tuple inputs (from click multiple=True) to list for run_tool
            for k, v in kwargs.items():
                if isinstance(v, tuple):
                    kwargs[k] = list(v)
            try:
                result = run_tool(spec_name, kwargs)
                click.echo(f"已成功執行工具 '{spec_name}'. 結果: {result}")
            except Exception as e:
                click.echo(f"執行工具 '{spec_name}' 時發生錯誤 ({type(e).__name__}): {e}", err=True)
        return command_callback

    # Create the command
    cmd = click.Command(name=tool_spec.name, 
                        callback=create_command_callback(tool_spec.name), 
                        help=tool_spec.description or f"執行 {tool_spec.name} 工具")

    # Add options dynamically in reverse order of definition for consistent help text
    if hasattr(tool_spec, 'args_schema') and tool_spec.args_schema:
        pydantic_model = tool_spec.args_schema
        for param_name, field_info in reversed(list(pydantic_model.model_fields.items())):
            original_help = field_info.description
            
            known_path_keys = ['file', 'files', 'stamp_path', 'output', 'output_dir']
            param_help = original_help
            if param_name in known_path_keys:
                warning_text = " (此路徑相對於預設的 'files/' 目錄。請勿嘗試存取 'uploads/' 或其他系統目錄)"
                param_help = f"{original_help}{warning_text}" if original_help else warning_text.strip()

            is_field_required = field_info.is_required() # Store Pydantic's requirement status
            
            option_kwargs = { # Initialize option_kwargs
                'help': param_help
            }

            # Determine actual_click_type and is_multiple from annotation
            param_type_annotation = field_info.annotation
            is_multiple = False
            actual_click_type = str # Default type

            if hasattr(param_type_annotation, '__origin__') and hasattr(param_type_annotation, '__args__'):
                if param_type_annotation.__origin__ == list and param_type_annotation.__args__:
                    is_multiple = True
                    actual_click_type = get_click_type(param_type_annotation.__args__[0])
                elif param_type_annotation.__origin__ == Union:
                    non_none_args = [arg for arg in param_type_annotation.__args__ if type(None) not in get_args(arg) and arg is not type(None)]
                    if non_none_args:
                        actual_click_type = get_click_type(non_none_args[0])
            else:
                actual_click_type = get_click_type(param_type_annotation)

            option_kwargs['type'] = actual_click_type
            option_kwargs['multiple'] = is_multiple # This will be False for output_dir

            # Determine 'required' and 'default' for Click
            is_pydantic_required = field_info.is_required() # Get Pydantic's requirement status

            if param_name == 'output_dir' and tool_spec.name == 'split': # Specific override for split's output_dir
                print(f"DEBUG_CLI_MAIN: Applying OVERRIDE for {tool_spec.name} / {param_name} (make optional for Click)", file=sys.stderr)
                option_kwargs['required'] = False
                option_kwargs['default'] = None
            elif param_name == 'output' and tool_spec.name == 'merge': # Specific override for merge's output
                print(f"DEBUG_CLI_MAIN: Applying OVERRIDE for {tool_spec.name} / {param_name} (make optional for Click)", file=sys.stderr)
                option_kwargs['required'] = False
                option_kwargs['default'] = None
            elif param_name == 'output' and tool_spec.name == 'add_stamp': # Specific override for add_stamp's output
                print(f"DEBUG_CLI_MAIN: Applying OVERRIDE for {tool_spec.name} / {param_name} (make optional for Click)", file=sys.stderr)
                option_kwargs['required'] = False
                option_kwargs['default'] = None
            elif param_name == 'output' and tool_spec.name == 'redact': # Specific override for redact's output
                print(f"DEBUG_CLI_MAIN: Applying OVERRIDE for {tool_spec.name} / {param_name} (make optional for Click)", file=sys.stderr)
                option_kwargs['required'] = False
                option_kwargs['default'] = None
            elif actual_click_type == bool:
                option_kwargs['is_flag'] = True
                option_kwargs['required'] = False 
                if field_info.default is not None and not isinstance(field_info.default, type(Ellipsis)) and not (hasattr(field_info.default, '__class__') and 'PydanticUndefined' in str(field_info.default.__class__)):
                    option_kwargs['default'] = bool(field_info.default)
                else:
                    option_kwargs['default'] = False
            elif not is_pydantic_required: # Optional non-boolean, non-overridden fields
                option_kwargs['required'] = False
                if field_info.default is not None and not isinstance(field_info.default, type(Ellipsis)) and not (hasattr(field_info.default, '__class__') and 'PydanticUndefined' in str(field_info.default.__class__)):
                    option_kwargs['default'] = field_info.default
                elif field_info.default_factory is not None:
                    option_kwargs['default'] = field_info.default_factory()
                else:
                    option_kwargs['default'] = None
            else: # Required by Pydantic (and not overridden)
                option_kwargs['required'] = True
            
            # Ensure multiple is correctly set if not a list type (already done by is_multiple initialization)
            # if not is_multiple:
            #    option_kwargs['multiple'] = False

            # Debug print for output_dir specifically
            if tool_spec.name == "split" and param_name == "output_dir":
                # print(f"DEBUG_CLI_MAIN: For {tool_spec.name} / {param_name}:") # Redundant with override print
                print(f"DEBUG_CLI_MAIN:   is_pydantic_required: {is_field_required}", file=sys.stderr)
                print(f"DEBUG_CLI_MAIN:   final option_kwargs for Click: {option_kwargs}", file=sys.stderr)

            click_param_name = f"--{param_name.replace('_', '-')}"
            opt = click.Option([click_param_name], **option_kwargs)
            
            if tool_spec.name == "split" and param_name == "output_dir":
                 print(f"DEBUG_CLI_MAIN:   Created click.Option with params: {opt.to_info_dict()}", file=sys.stderr)
            cmd.params.insert(0, opt)
            
    cli.add_command(cmd)


# The manually defined history command remains as is for now,
# as it's not loaded from a YAML tool spec.
@cli.command("history")
@click.option('--limit', default=10, type=int, help='要顯示的操作記錄數量 (預設: 10)')
def history_cmd(limit):
    """顯示最近的操作歷史記錄"""
    try:
        from apptrace.models import Operation 
        operations = Operation.objects.order_by('-created_at')[:limit]
        if not operations:
            click.echo("沒有操作歷史記錄可顯示。")
            return
        click.echo(f"顯示最近 {len(operations)} 條操作歷史記錄:")
        for op in operations:
            status = getattr(op, 'status', 'N/A')
            error_msg = getattr(op, 'error_message', '')
            click.echo(f"- {op.created_at.strftime('%Y-%m-%d %H:%M:%S')} | {op.tool:<10} | In: {op.in_hash[:8] if op.in_hash else 'N/A'} | Out: {op.out_hash[:8] if op.out_hash else 'N/A'} | Status: {status}")
            if status == "error" and error_msg:
                click.echo(f"    Error: {error_msg[:100] + '...' if len(error_msg) > 100 else error_msg}")
    except Exception as e:
        click.echo(f"查詢歷史記錄時發生錯誤: {e}", err=True)

if __name__ == '__main__':
    cli()