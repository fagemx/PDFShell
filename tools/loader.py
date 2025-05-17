import yaml
import importlib
import inspect
import textwrap
# from langchain.agents import Tool # No longer needed, aiming for BaseTool or @tool from core
from langchain_core.tools import BaseTool, Tool as CoreTool # For instance checking of @tool decorated functions
from pathlib import Path
import os

# Assuming loader.py is in PDFShell/tools/loader.py
# Then PDFShell/ is the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def load_tools(folder_path_str: str = "tools") -> list[BaseTool]:
    """
    Dynamically loads tools from YAML specifications and Python modules.
    Prioritizes finding @tool decorated functions (matching YAML name).
    Falls back to finding BaseTool subclasses (matching class.name with YAML name).
    """
    loaded_tools = []
    # Try to interpret folder_path_str relative to project root if it's not absolute
    tools_folder = Path(folder_path_str)
    if not tools_folder.is_absolute() and not tools_folder.exists():
        tools_folder = PROJECT_ROOT / folder_path_str

    if not tools_folder.is_dir():
        print(f"Critical: Tools folder '{tools_folder}' not found. Cannot load tools.")
        return []

    for yml_file in tools_folder.glob("*.yml"):
        try:
            spec = yaml.safe_load(yml_file.read_text(encoding="utf-8"))
            module_name_str = yml_file.stem
            yaml_tool_name = spec.get('name')
            if not yaml_tool_name:
                print(f"Warning: 'name' not found in YAML file {yml_file.name}. Skipping.")
                continue

            full_module_name = f"{tools_folder.name}.{module_name_str}"
            tool_module = importlib.import_module(full_module_name)
            
            found_tool_instance = None

            # 1. Try to get @tool decorated function (which is already a Tool instance)
            potential_tool_obj = getattr(tool_module, yaml_tool_name, None)
            if potential_tool_obj and isinstance(potential_tool_obj, (BaseTool, CoreTool)):
                 # Check if its name matches, though getattr already did by name
                if hasattr(potential_tool_obj, 'name') and potential_tool_obj.name == yaml_tool_name:
                    found_tool_instance = potential_tool_obj
                    # For @tool decorated functions, root_dir might need to be passed differently
                    # or handled within the function if it accepts a root_dir_str argument.
                    # We can try to set it if the tool instance allows, but this is less standard for @tool
                    if hasattr(found_tool_instance, 'root_dir') and isinstance(getattr(found_tool_instance, 'root_dir', None), Path):
                        # This is more for BaseTool subclasses. @tool might not have this attribute.
                        # setattr(found_tool_instance, 'root_dir', PROJECT_ROOT) # Avoid if not designed for it
                        pass 
                    # The add_stamp example was modified to accept root_dir_str.
                    # We could try to inject PROJECT_ROOT to its execution if its schema supports it,
                    # but that requires more complex schema introspection here or a wrapper.
                    # For now, assume the @tool function handles its paths or uses cwd.
                    print(f"Info: Loaded '{yaml_tool_name}' as an @tool decorated function from '{full_module_name}.py'.")

            # 2. If not found, try to find a BaseTool subclass (existing logic)
            if not found_tool_instance:
                tool_class = None
                for attr_name in dir(tool_module):
                    attr = getattr(tool_module, attr_name)
                    if inspect.isclass(attr) and \
                       issubclass(attr, BaseTool) and \
                       attr is not BaseTool and \
                       inspect.getmodule(attr) == tool_module:
                        if hasattr(attr, 'name') and getattr(attr, 'name') == yaml_tool_name:
                            tool_class = attr
                            break
                
                if tool_class:
                    tool_instance_from_class = tool_class()
                    if hasattr(tool_instance_from_class, 'root_dir') and isinstance(getattr(tool_instance_from_class, 'root_dir', None), Path):
                        tool_instance_from_class.root_dir = PROJECT_ROOT
                    
                    if not tool_instance_from_class.name: # Should be set by class
                        tool_instance_from_class.name = yaml_tool_name
                    if not tool_instance_from_class.description:
                        yaml_desc = spec.get("description", f"Tool {yaml_tool_name} from {yml_file.name}")
                        tool_instance_from_class.description = textwrap.dedent(yaml_desc.strip())
                    
                    found_tool_instance = tool_instance_from_class
                    print(f"Info: Loaded '{yaml_tool_name}' as a BaseTool subclass from '{full_module_name}.py'.")

            # Final check and append
            if found_tool_instance:
                # Ensure description is set if @tool didn't get it from docstring automatically for the Tool instance
                if not getattr(found_tool_instance, 'description', None):
                    yaml_desc = spec.get("description", f"Tool {yaml_tool_name} from {yml_file.name}")
                    # Langchain @tool usually gets description from docstring. This is a fallback.
                    # For BaseTool instances, it's usually set in the class or via this logic already.
                    try:
                        found_tool_instance.description = textwrap.dedent(yaml_desc.strip())
                    except AttributeError: # Some tool instances might not allow direct assignment
                        print(f"Warning: Could not set description for tool {yaml_tool_name}.")
                loaded_tools.append(found_tool_instance)
            else:
                # No @tool function and no BaseTool subclass found
                print(f"Warning: Could not find a loadable tool (neither @tool function nor BaseTool subclass) named '{yaml_tool_name}' in module '{full_module_name}'. Tool from '{yml_file.name}' not loaded.")

        except FileNotFoundError:
            print(f"Warning: YAML file {yml_file} not found (should not happen as we are globbing).")
        except ImportError as e:
            print(f"Warning: Could not import module {full_module_name}: {e}")
        except AttributeError as e:
            print(f"Warning: Attribute error processing tool from {yml_file.name} (module: {full_module_name}): {e}")
        except Exception as e:
            print(f"Critical: Error loading tool from {yml_file.name} (module: {full_module_name}): {e}")
            import traceback
            traceback.print_exc()
            
    return loaded_tools
