from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from pathlib import Path
import json
import logging # Added for logging
import re # Added for re.search in agent_node
from dotenv import load_dotenv
import os # Added for os.path.basename
load_dotenv()
# Import existing tool classes
from tools.add_stamp import AddStampTool
from tools.merge import MergeTool
from tools.redact import RedactTool
from tools.split import SplitTool
from core.engine import run_tool as engine_run_tool # <--- 新增導入

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # You can adjust the level

# Determine Project Root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Initialize LLM
LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0) # Changed to gpt-4o-mini as per previous setup

# Instantiate existing tools
# These are the tools LangGraph will use.
# Their .name and .description attributes will be used by the agent_node's LLM.
# Their .run() method will be called by the tool_node.
tools_instances = [
    AddStampTool(root_dir=PROJECT_ROOT),
    MergeTool(root_dir=PROJECT_ROOT),
    RedactTool(root_dir=PROJECT_ROOT),
    SplitTool(root_dir=PROJECT_ROOT)
]

# Helper function to extract type string from JSON schema property details
def _extract_type_from_schema_details(prop_details: dict) -> str:
    if not isinstance(prop_details, dict):
        logger.error(f"DEBUG: _extract_type_from_schema_details received non-dict: {type(prop_details)}")
        return "schema_error"

    final_types = set()

    # Handle 'type' field (can be string or list)
    type_info = prop_details.get('type')
    if type_info:
        if isinstance(type_info, list):
            for t_item in type_info:
                if t_item != 'null': # Usually omit 'null' for display if 'optional' implies it
                    final_types.add(str(t_item))
        elif type_info != 'null':
            final_types.add(str(type_info))

    # Handle 'anyOf' (common for Optional or Literal)
    any_of_info = prop_details.get('anyOf')
    if any_of_info and isinstance(any_of_info, list):
        for sub_schema in any_of_info:
            if isinstance(sub_schema, dict):
                sub_type_info = sub_schema.get('type')
                if sub_type_info and sub_type_info != 'null':
                    if isinstance(sub_type_info, list):
                         for t_item in sub_type_info:
                            if t_item != 'null':
                                final_types.add(str(t_item))
                    else:
                        final_types.add(str(sub_type_info))
                elif sub_schema.get('enum') and not sub_type_info: 
                    # If sub_schema is like {"enum": ["A", "B"]}, it's an enum type.
                    # Add "enum" if no more specific type found in this sub_schema.
                    final_types.add("enum")


    # Handle 'enum' (can appear with 'type' or standalone)
    enum_info = prop_details.get('enum')
    if enum_info:
        if not final_types: # If no other type info yet, classify as enum
            final_types.add("enum")
            # Optionally, include some enum values for clarity:
            # enum_values_str = ", ".join(f"'{str(v)}'" for v in enum_info[:3])
            # final_types.add(f"enum({enum_values_str}{'...' if len(enum_info) > 3 else ''})")
    
    if not final_types: # Fallback if no type information could be extracted
        return "unknown"
    
    return " or ".join(sorted(list(final_types)))


# Helper to get tool information for the LLM prompt
def get_tool_info_for_llm():
    info_lines = []
    for tool in tools_instances:
        description = getattr(tool, 'description', 'No description available.')
        args_schema_desc = ""
        if hasattr(tool, 'args_schema'):
            try:
                schema = tool.args_schema.model_json_schema()
                props = schema.get('properties', {})
                required = schema.get('required', [])
                param_descs = []
                for name, details in props.items():
                    is_req = "required" if name in required else "optional"
                    
                    type_display: str
                    desc_display: str

                    if not isinstance(details, dict):
                        # CRITICAL: Handle cases where 'details' is not a dict (e.g., FieldInfo)
                        logger.error(f"Schema details for property '{tool.name}.{name}' is not a dictionary. Got {type(details)}. Value: {details}")
                        type_display = "error_parsing_type"
                        # Attempt to get description from FieldInfo if that's what 'details' is
                        if hasattr(details, 'description') and isinstance(details.description, str):
                            desc_display = details.description
                        else:
                            desc_display = 'error_parsing_description'
                    else:
                        type_display = _extract_type_from_schema_details(details)
                        desc_display = details.get('description', '')
                    
                    # CUSTOM MODIFICATION FOR add_stamp TOOL's page PARAMETER
                    if tool.name == "add_stamp" and name == "page":
                        desc_display = desc_display.rstrip('.') + ". Use 0 for all pages."

                    param_descs.append(f"  - {name} ({type_display}, {is_req}): {desc_display}")
                if param_descs:
                    # Ensure backslashes in string literals are escaped for the f-string
                    args_schema_desc = "\n  Parameters:\n" + "\n".join(param_descs)
                
                # CUSTOM MODIFICATION FOR SPLIT TOOL PAGES PARAMETER
                if tool.name == "split":
                    pages_param_index = -1
                    for i, desc in enumerate(param_descs):
                        if desc.strip().startswith("- pages (string, required)"):
                            pages_param_index = i
                            break
                    
                    if pages_param_index != -1:
                        param_descs[pages_param_index] = (
                            "  - pages (string, required): Page ranges to split.\n"
                            "      Use a comma-separated list of page numbers or ranges.\n"
                            "      - A range is 'start-end' (e.g., \"2-5\" for pages 2 through 5).\n"
                            "      - Individual pages are just numbers (e.g., \"1,7,9\").\n"
                            "      - To exclude pages, prefix with '!' (e.g., \"!3\" excludes page 3, \"!2-4\" excludes pages 2 through 4).\n"
                            "      - Examples:\n"
                            "          - \"1-3,5\": Selects pages 1, 2, 3, and 5.\n"
                            "          - \"!7\": Selects all pages except page 7.\n"
                            "          - \"2-5,!3\": Selects pages 2, 4, and 5 (pages 2 through 5, but exclude page 3).\n"
                            "          - \"1,-1\": Selects the first and the last page (if total pages is known, interpret -1 as last page number).\n"
                            "      - To express \"remove the first and last page and keep the middle part\" for a PDF with N pages, you would specify \"2-(N-1)\".\n"
                            "        If N is unknown, you should use 'clarify' to ask for N or a more specific range like \"pages 2 through 10\".\n"
                            "        Do NOT invent complex syntaxes like '2-!1' or use variables like 'N' directly in the parameter value."
                        )
                        args_schema_desc = "\n  Parameters:\n" + "\n".join(param_descs)

            except Exception as e:
                logger.warning(f"Could not get schema for tool {tool.name}: {e}", exc_info=True)

        info_lines.append(f"- Tool Name: {tool.name}\n  Description: {description}{args_schema_desc}")
    return "\n".join(info_lines)

TOOL_INFO_FOR_LLM = get_tool_info_for_llm()

# LangGraph State
class AgentState(dict):
    input: str # User's latest text input
    history: list[tuple[str, str]] 
    tool_name: str | None
    tool_args: dict | None
    output: str | None
    error: str | None
    # New state fields based on Phase 4 requirements
    session_id: str | None # Current session ID
    available_files: list[dict] # List of dicts like {'user_label': 'original.pdf', 'session_filename': 'uuid.pdf'}

def format_history(history: list[tuple[str, str]]) -> str:
    if not history:
        return "No previous conversation."
    formatted_history = []
    for user_msg, agent_msg in history:
        formatted_history.append(f"User: {user_msg}\nAssistant: {agent_msg}")
    return "\n\n".join(formatted_history)

# Agent node: LLM decides which tool to call
def agent_node(state: AgentState):
    logger.info("---AGENT NODE---")
    user_input = state['input']
    history = state.get('history', [])
    
    # Get new session-related info from state
    session_id = state.get('session_id')
    available_files = state.get('available_files', [])

    formatted_hist = format_history(history)
    
    uploaded_files_info_for_prompt = ""
    if available_files:
        file_details_for_prompt = []
        for f_info in available_files:
            # Ensure f_info is a dict and has the expected keys
            if isinstance(f_info, dict) and 'user_label' in f_info and 'session_filename' in f_info:
                file_details_for_prompt.append(
                    f"- Friendly Name: '{f_info['user_label']}' (Refer to this as: '{f_info['session_filename']}' in tool arguments)"
                )
            else:
                logger.warning(f"AGENT_NODE (Session: {session_id}): Invalid item in available_files: {f_info}")

        if file_details_for_prompt:
            uploaded_files_info_for_prompt = "\n\nAvailable files for this session ('{session_id}'):\n" + "\n".join(file_details_for_prompt)
    else:
        uploaded_files_info_for_prompt = f"\n\nNo files have been uploaded or made available for this session ('{session_id}')."


    prompt_template = f"""This is a multi-turn conversation for session_id: '{session_id}'.
Previous exchanges:
{formatted_hist}

User's latest request: {user_input}{uploaded_files_info_for_prompt}

Available tools:
{TOOL_INFO_FOR_LLM}

IMPORTANT INSTRUCTIONS FOR TOOL ARGUMENTS AND FILE HANDLING:
1.  Analyze the user's request, conversation history, and the 'Available files for this session' list.
2.  INPUT FILES: 
    - If the user's request implies using one or more of the 'Available files for this session', you MUST use the corresponding 'Refer to this as: <session_filename>' value (e.g., 'uuid_contract.pdf' or 'sample1.pdf') as the file argument for the relevant tool (e.g., in 'file', 'files', 'stamp_path' arguments).
    - CRITICAL: The value you use for these file arguments MUST be EXACTLY the <session_filename> string provided in the 'Available files' list. DO NOT add any prefixes like 'files/', 'uploads/', or any other path segments to this filename.
    - DO NOT use the 'Friendly Name' (e.g., 'original.pdf') in tool arguments.
    - DO NOT ask the user for filenames if they have already provided files that seem relevant.
    - If the user refers to a file not in the 'Available files for this session' list, you MUST use the 'clarify' tool to ask them to upload or specify correctly.
3.  OUTPUT FILES:
    - For tool arguments that specify an output file (e.g., 'output' in merge, redact, add_stamp; 'output_dir' for split implies files will be created there), you MUST provide a NEW, SIMPLE FILENAME (e.g., 'merged_document.pdf', 'stamped_page.pdf'). 
    - This simple filename will be automatically saved within the current session's directory ('{session_id}').
    - DO NOT attempt to construct full paths or include session_id in the output filename you provide in the tool_args.
    - For the 'split' tool, the 'output_dir' argument will be handled by the system to be a directory within the session. You should still provide a simple directory name if the tool schema requires 'output_dir' (e.g. "split_output"), or if the tool schema expects the output to be named based on input, do not specify 'output' or 'output_dir' unless the schema explicitly requires it to be a new name. (Refer to tool schema for 'split' on how it handles output naming).
4.  CLARIFICATION:
    - If the request is a general greeting, or too vague, use the 'clarify' tool (e.g., tool_args: {{\"message\": \"Hello! How can I help you with your PDFs today?\"}}).
    - If necessary information for a PDF operation is missing (even after checking history and available files), use 'clarify' to ask for it (e.g., tool_args: {{\"message\": \"Which page would you like to stamp?\"}}).
5.  TOOL SELECTION: If the request is clear and all information is present, select the appropriate tool and fill its 'tool_args' PRECISELY according to the rules above and the tool's parameter schema.
6.  RESPONSE FORMAT: Always respond with a single JSON object containing \"tool_name\" (string) and \"tool_args\" (a dictionary).

Example for 'merge' using available files:
Suppose 'Available files for this session' includes:
- Friendly Name: 'document_A.pdf' (Refer to this as: 'file_uuid_A.pdf' in tool arguments)
- Friendly Name: 'document_B.pdf' (Refer to this as: 'file_uuid_B.pdf' in tool arguments)
User request: \"Merge document_A and document_B and call it final_merged.pdf\"
LLM Response: {{\"tool_name\": \"merge\", \"tool_args\": {{\"files\": [\"file_uuid_A.pdf\", \"file_uuid_B.pdf\"], \"output\": \"final_merged.pdf\"}}}}

Example for 'add_stamp' using an available file:
Suppose 'Available files for this session' includes:
- Friendly Name: 'contract.pdf' (Refer to this as: 'contract_id_123.pdf' in tool arguments)
- Friendly Name: 'system_logo.png' (Refer to this as: 'system_logo.png' in tool arguments) <--- Example of a shared file
User request: \"Add system_logo.png to page 1 of contract.pdf. Save it as stamped_contract.pdf\"
LLM Response: {{"tool_name": "add_stamp", "tool_args": {{"file": "contract_id_123.pdf", "stamp_path": "system_logo.png", "page": 1, "output": "stamped_contract.pdf"}}}}
(If stamp_path refers to a file NOT in 'Available files', LLM should use 'clarify' to ask for the stamp file.)

Example of INCORRECT input file argument (DO NOT DO THIS):
Suppose 'Available files for this session' includes:
- Friendly Name: 'sample.pdf' (Refer to this as: 'sample.pdf' in tool arguments)
User request: "Add a stamp to sample.pdf"
WRONG LLM Response: {{"tool_name": "add_stamp", "tool_args": {{"file": "files/sample.pdf", ...}}}}
CORRECT LLM Response: {{"tool_name": "add_stamp", "tool_args": {{"file": "sample.pdf", ...}}}}

Example for 'clarify' (file not available):
User request: \"Split important_document.pdf\"
(Assume 'important_document.pdf' is NOT in 'Available files for this session')
LLM Response: {{\"tool_name\": \"clarify\", \"tool_args\": {{\"message\": \"The file 'important_document.pdf' is not available in this session. Please upload it or specify an available file.\"}}}}
"""
    
    try:
        logger.info(f"LLM Prompt for agent_node:\n{prompt_template}")
        llm_response_content = LLM.invoke(prompt_template).content
        logger.info(f"LLM Response content: {llm_response_content}")
        
        # Attempt to find and parse the JSON part of the response
        # LLMs can sometimes return text around the JSON.
        json_match = re.search(r'```json\n(.*?)```', llm_response_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # If no markdown block, assume the whole content is JSON or parse directly
            json_str = llm_response_content

        parsed_response = json.loads(json_str)
        tool_name = parsed_response.get("tool_name")
        tool_args = parsed_response.get("tool_args", {})

        if not tool_name:
            raise ValueError("LLM response did not include a tool_name.")

        logger.info(f"Selected tool: {tool_name}, Args: {tool_args}")
        # Preserve file paths in the state if they were part of the agent's decision
        return {
            "tool_name": tool_name, 
            "tool_args": tool_args, 
            "input": user_input, 
            "error": None,
            "session_id": session_id,
            "available_files": available_files
        }

    except json.JSONDecodeError as e:
        logger.error(f"Agent_node: Failed to parse LLM JSON response: {e}")
        logger.error(f"LLM raw response was: {llm_response_content}") # Log the raw response for debugging
        return {"error": "Failed to parse LLM response.", "output": "I could not understand how to proceed. Please try rephrasing.", "input": user_input}
    except Exception as e:
        logger.error(f"Agent_node: Error: {e}", exc_info=True) # Added exc_info for better debugging
        return {"error": str(e), "output": "An unexpected error occurred while planning the action.", "input": user_input}

# Tool node: Executes the selected tool
def tool_node(state: AgentState):
    logger.info("---TOOL NODE---")
    tool_name = state.get("tool_name")
    tool_args = state.get("tool_args")
    session_id = state.get("session_id") # Get session_id from state

    if not tool_name:
        logger.error("Error in tool_node: tool_name is not set.")
        return {"error": "Tool name not decided by agent.", "output": "Agent did not specify a tool to run."}
    
    if tool_name == "clarify": # Handle clarification case directly
        message_to_user = tool_args.get("message", tool_args.get("query", "請問需要什麼協助嗎？"))
        return {"output": message_to_user, "error": None}

    try:
        logger.info(f"Calling core.engine.run_tool for: {tool_name} with args: {tool_args} and session_id: {session_id}")
        # 將原始的 tool_args (包含簡單檔名) 和 session_id 傳遞給 engine.run_tool
        # engine.run_tool 內部會處理路徑解析和實際的工具執行
        result = engine_run_tool(tool_name, tool_args, session_id=session_id)
        logger.info(f"core.engine.run_tool for {tool_name} executed. Result: {result}")
        return {"output": result, "error": None}
    except FileNotFoundError as e:
        logger.error(f"Tool_node: FileNotFoundError during core.engine.run_tool for {tool_name}: {e}", exc_info=True)
        # 將 FileNotFoundError 更明確地傳遞給前端
        error_message = f"檔案未找到：{e.filename}" if hasattr(e, 'filename') else str(e)
        return {"output": f"執行工具 {tool_name} 失敗: {error_message}", "error": error_message}
    except ValueError as e: # 捕獲來自 engine 或 secure.validate 的 ValueError
        logger.error(f"Tool_node: ValueError during core.engine.run_tool for {tool_name}: {e}", exc_info=True)
        return {"output": f"執行工具 {tool_name} 時發生參數或驗證錯誤: {str(e)}", "error": str(e)}
    except Exception as e:
        logger.error(f"Tool_node: Unexpected error during core.engine.run_tool for {tool_name}: {e}", exc_info=True)
        # 對於其他未知錯誤，返回通用錯誤訊息
        return {"output": f"執行工具 {tool_name} 時發生預期外的內部錯誤。", "error": str(e)}

# Define the graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("tool_executor", tool_node)

# Define edges
workflow.set_entry_point("agent")
workflow.add_edge("agent", "tool_executor")
workflow.add_edge("tool_executor", END) 

# Compile the graph
app = workflow.compile()

# Main execution function, similar to the old nl_execute
def nl_execute(payload: dict) -> dict: # Updated signature
    logger.info(f"---NL_EXECUTE START--- Payload received: {payload}")

    user_text = payload.get('text', "")
    session_id = payload.get('session_id')
    available_files = payload.get('available_files', [])
    history = payload.get('history', [])

    if not session_id:
        logger.error("NL_EXECUTE: session_id is missing from payload.")
        return {"error": "Session ID is required.", "output": "Error: Session ID missing."}
    if not user_text and not available_files: # If no text and no files to act upon
        logger.warning(f"NL_EXECUTE (Session: {session_id}): No user text and no available files. Returning clarification.")
        return {"output": "Hello! How can I help you today? Please provide some text or upload files.", "log_entries": ["Agent clarified due to empty input."]}


    # Initialize state for LangGraph
    initial_state = AgentState(
        input=user_text,
        history=history,
        session_id=session_id,
        available_files=available_files,
        tool_name=None,
        tool_args=None,
        output=None,
        error=None
    )
    try:
        final_state = app.invoke(initial_state)
        logger.info(f"Final state: {final_state}")
        
        return final_state

    except Exception as e:
        logger.error(f"Critical error in nl_execute: {e}", exc_info=True)
        return AgentState(input=user_text, error=str(e), output=f"An unexpected critical error occurred: {e}", session_id=session_id, available_files=available_files)


if __name__ == '__main__':
    # Example usage
    if not (PROJECT_ROOT / "sample1.pdf").exists():
        (PROJECT_ROOT / "sample1.pdf").write_text("This is a dummy PDF for sample1.")
        logger.info(f"Created dummy PDF file at {PROJECT_ROOT / 'sample1.pdf'}")
    if not (PROJECT_ROOT / "sample2.pdf").exists():
        # Create a dummy 3-page PDF for sample2.pdf for testing split
        from pypdf import PdfWriter
        writer = PdfWriter()
        for i in range(3):
            writer.add_blank_page(width=210, height=297) # A4 size
        with open(PROJECT_ROOT / "sample2.pdf", "wb") as f:
            writer.write(f)
        logger.info(f"Created dummy 3-page PDF file at {PROJECT_ROOT / 'sample2.pdf'}")

    if not (PROJECT_ROOT / "stamp.png").exists():
        (PROJECT_ROOT / "stamp.png").write_text("This is a dummy PNG for stamp.")
        logger.info(f"Created dummy PNG file at {PROJECT_ROOT / 'stamp.png'}")

    # --- Test Case: Multi-turn conversation for split --- 
    print("\n--- Test Case: Multi-turn conversation for split ---")
    
    # Turn 1: User asks to remove first and last page (ambiguous)
    query1 = "請從 sample2.pdf 中移除第 1 頁和最後一頁，保留中間的部分"
    print(f"\nExecuting Query 1: '{query1}'")
    response1_state = nl_execute({"text": query1, "history": []})
    print(f"Agent Output 1: {response1_state.get('output')}")
    
    # Simulate history for Turn 2
    current_history = []
    if response1_state.get('output'): # Add to history if clarify tool was used
        current_history.append((query1, response1_state.get('output')))

    # Turn 2: User provides total pages
    query2 = "sample2.pdf 共有3頁"
    print(f"\nExecuting Query 2: '{query2}' (with history)")
    response2_state = nl_execute({"text": query2, "history": current_history})
    print(f"Agent Output 2: {response2_state.get('output')}")
    print(f"Full state for response 2: {response2_state}")
    # --- End Test Case ---

    queries = [
        "Hello there!",
        "Can you merge sample1.pdf and sample2.pdf into merged_sample.pdf?",
        "Add stamp.png to sample1.pdf on page 1 and save it as stamped_output.pdf",
        # "Bogus instruction to test error handling" # Covered by multi-turn test implicitly
    ]

    for test_query in queries:
        print(f"\nExecuting query: '{test_query}'")
        try:
            # For single turn queries, history is empty
            output_state = nl_execute({"text": test_query, "history": []})
            print(f"Agent Output: {output_state.get('output')}")
            if output_state.get('error'):
                 print(f"Agent Error: {output_state.get('error')}")
        except Exception as e:
            print(f"Error during main execution for query '{test_query}': {e}")

    # --- Test Case: File Upload --- (Simulated by providing paths)
    print("\n--- Test Case: File Upload for merge ---")
    # Create dummy uploaded files for testing this scenario
    dummy_uploaded_file1_path = PROJECT_ROOT / "uploaded_doc1.pdf"
    dummy_uploaded_file2_path = PROJECT_ROOT / "uploaded_doc2.pdf"
    dummy_uploaded_file1_path.write_text("Content of uploaded doc1")
    dummy_uploaded_file2_path.write_text("Content of uploaded doc2")

    upload_query = "Merge the two files I uploaded and call it merged_uploads.pdf"
    print(f"\nExecuting Query (with simulated upload): '{upload_query}'")
    upload_response_state = nl_execute({
        "text": upload_query, 
        "history": [], 
        "available_files": [
            {"user_label": "uploaded_doc1.pdf", "session_filename": "uuid_doc1.pdf"},
            {"user_label": "uploaded_doc2.pdf", "session_filename": "uuid_doc2.pdf"}
        ]
    })
    print(f"Agent Output (Upload): {upload_response_state.get('output')}")
    print(f"Full state for upload response: {upload_response_state}")

    # Clean up dummy uploaded files
    if dummy_uploaded_file1_path.exists(): os.remove(dummy_uploaded_file1_path)
    if dummy_uploaded_file2_path.exists(): os.remove(dummy_uploaded_file2_path)

    # Example of how tool info looks for the prompt
    # print("\n--- TOOL INFO FOR LLM ---")
    # print(TOOL_INFO_FOR_LLM)
