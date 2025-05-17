import importlib
import yaml
import logging
from pathlib import Path # Added Path
from .secure import validate, hash_file
# from .alert import notify_slack # Commented out for now
from trace.models import Operation # Import the Operation model
from django.conf import settings # Import settings to access PDF_FILES_ROOT, PDF_UPLOADS_ROOT

# Placeholder for log_trace, will be implemented later with Trace model
# from trace.models import Operation # This will be used when trace is set up
def log_trace(tool_name: str, args: dict, in_hash: str | None, out_hash: str | None, status: str = "success", error_message: str | None = None):
    """
    Logs the operation details to the Operation model in the database.
    Args should contain the full physical paths used.
    """
    try:
        Operation.objects.create(
            tool=tool_name,
            args=args, # These args should now contain full paths
            in_hash=in_hash,
            out_hash=out_hash,
            status=status,
            error_message=error_message
        )
        logging.info(f"Successfully logged trace for tool: {tool_name}, status: {status}")
    except Exception as e:
        # If logging to DB fails, log this critical error to system logs
        logging.critical(f"Failed to log trace to database for tool {tool_name}: {e}", exc_info=True)

# Define known path keys for input and output
# This is a simplification. A more robust solution might involve tool-specific metadata.
INPUT_PATH_KEYS = ['file', 'files', 'stamp_path'] # 'files' can be a list
OUTPUT_PATH_KEYS = ['output', 'output_dir']

def _resolve_and_validate_path(
    filename: str, 
    target_base_path: Path, 
    expected_validation_root: Path, 
    is_input: bool, 
    session_id: str | None, 
    arg_key: str
) -> str:
    """
    Resolves a filename against a target_base_path and validates it against expected_validation_root.
    Ensures parent directories exist for output files/dirs.
    """
    # Basic sanitization for filename itself, should not contain traversal attempts.
    if '..' in filename or (('/' in filename or '\\' in filename) and arg_key not in ['output_dir']): # allow / for output_dir if needed
        # For session inputs/outputs, filename should be simple. For CLI, it can be relative but not malicious.
        if session_id or (not session_id and (filename.startswith('/') or filename.startswith('~'))):
            logging.error(f"Invalid filename format for '{arg_key}': '{filename}'. Contains path separators or traversal attempts.")
            raise ValueError(f"Invalid filename '{filename}' for argument '{arg_key}'. Filenames should be simple or safe relative paths.")

    full_path = (target_base_path / filename).resolve()

    if not is_input: # Handling output paths
        if arg_key == 'output_dir':
            full_path.mkdir(parents=True, exist_ok=True)
        else: # Output file
            full_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Validation
    # For output directories, a simpler check to ensure it's under the expected root.
    if arg_key == 'output_dir' and not is_input:
        if not str(full_path.absolute()).startswith(str(expected_validation_root.resolve().absolute())):
            logging.error(f"Output directory traversal attempt: {full_path} is not under {expected_validation_root}")
            raise ValueError("Access denied: Output directory is outside of its designated scope.")
        # Double check for ".." after resolve, though resolve() should handle canonical paths.
        path_parts = full_path.parts
        if any("..\"".encode() in part.encode() for part in path_parts): # Check bytes to be safe
            logging.error(f"Output directory traversal attempt using '..': {full_path}")
            raise ValueError("Access denied: Invalid path components ('..') found in output directory.")
    else: # Input files or output files (not dirs)
        current_accepted_mime_types = None
        if arg_key == 'stamp_path' and is_input: # Specific handling for stamp_path
            current_accepted_mime_types = ['image/png', 'image/jpeg', 'image/jpg'] # Add other image types if needed
        
        validate(
            str(full_path), 
            expected_root=expected_validation_root, 
            session_id=session_id, 
            is_input=is_input,
            accepted_mime_types=current_accepted_mime_types # Pass the accepted types
        )

    return str(full_path)

def _process_single_path(path_str: str, base_path: Path, is_input: bool, session_id: str | None, arg_key: str) -> str:
    """ 
    DEPRECATED in favor of logic within process_path_arg to handle shared files.
    Kept for reference during refactoring if needed, but should be removed later.
    """
    # This function is now superseded by the logic directly in process_path_arg
    # which needs to check settings.DEFAULT_SHARED_FILES.
    # The core resolving and validation logic is moved to _resolve_and_validate_path.
    raise NotImplementedError("_process_single_path is deprecated.")

def process_path_arg(arg_value, base_path_for_cli: Path, session_id: str | None, is_input: bool, arg_key: str):
    """
    Processes a single file path argument or a list of them.
    Validates and resolves paths, considering session context and default shared files.
    Returns the processed path string or list of path strings.
    """
    if isinstance(arg_value, list):
        processed_paths = []
        for p_item in arg_value:
            if not isinstance(p_item, str):
                raise ValueError(f"Invalid path item in list for argument '{arg_key}': {p_item}")
            # Recursive call for list items
            processed_paths.append(
                process_path_arg(p_item, base_path_for_cli, session_id, is_input, arg_key)
            )
        return processed_paths
    elif isinstance(arg_value, str):
        filename_from_llm_or_cli = arg_value
        
        if session_id: # Session context
            session_upload_dir = settings.PDF_UPLOADS_ROOT / session_id
            session_upload_dir.mkdir(parents=True, exist_ok=True) # Ensure session dir exists

            if is_input:
                # 1. Try session-specific uploaded file first
                potential_session_file = session_upload_dir / filename_from_llm_or_cli
                if potential_session_file.exists():
                    return _resolve_and_validate_path(
                        filename_from_llm_or_cli, 
                        session_upload_dir, 
                        session_upload_dir, 
                        is_input, 
                        session_id, 
                        arg_key
                    )
                # 2. If not in session uploads, try default shared files
                elif filename_from_llm_or_cli in getattr(settings, 'DEFAULT_SHARED_FILES', []):
                    potential_shared_file = settings.PDF_FILES_ROOT / filename_from_llm_or_cli
                    if potential_shared_file.exists():
                        return _resolve_and_validate_path(
                            filename_from_llm_or_cli, 
                            settings.PDF_FILES_ROOT, 
                            settings.PDF_FILES_ROOT, 
                            is_input, 
                            session_id, # Pass session_id for context, though validation root is PDF_FILES_ROOT
                            arg_key
                        )
                    else:
                        logging.error(f"Default shared file '{filename_from_llm_or_cli}' defined in settings but not found at {potential_shared_file}")
                        raise FileNotFoundError(f"Shared file '{filename_from_llm_or_cli}' not found.")
                else:
                    logging.error(f"File '{filename_from_llm_or_cli}' not found in session '{session_id}' nor as a default shared file.")
                    raise FileNotFoundError(f"File '{filename_from_llm_or_cli}' not available in this session.")
            else: # Output path for a session context (is_input=False)
                # Outputs always go to the session's upload directory
                return _resolve_and_validate_path(
                    filename_from_llm_or_cli, 
                    session_upload_dir, 
                    session_upload_dir, 
                    is_input, 
                    session_id, 
                    arg_key
                )
        else: # CLI context (no session_id)
            # All paths are relative to base_path_for_cli (which is PDF_FILES_ROOT)
            return _resolve_and_validate_path(
                filename_from_llm_or_cli, 
                base_path_for_cli, 
                base_path_for_cli, 
                is_input, 
                session_id, # None here
                arg_key
            )
    else:
        raise ValueError(f"Invalid path argument type for '{arg_key}': {type(arg_value)}")

def run_tool(tool_name: str, original_args: dict, session_id: str | None = None):
    """
    Dynamically loads and runs a tool module.
    Manages path validation and construction based on session or CLI context.
    """
    args = original_args.copy() # Work on a copy to modify paths

    # Determine base paths
    pdf_files_root = settings.PDF_FILES_ROOT
    pdf_uploads_root = settings.PDF_UPLOADS_ROOT

    processed_input_paths_for_hash = []
    primary_in_hash = None # Initialize primary_in_hash

    try:
        # Process input paths
        for key in INPUT_PATH_KEYS:
            if key in args:
                # base_path_for_cli is only used if session_id is None
                args[key] = process_path_arg(args[key], settings.PDF_FILES_ROOT, session_id, is_input=True, arg_key=key)
                
                # Update processed_input_paths_for_hash after successful processing
                current_processed_val = args[key]
                if isinstance(current_processed_val, list):
                    processed_input_paths_for_hash.extend(current_processed_val)
        else:
                    processed_input_paths_for_hash.append(current_processed_val)

        # Process output paths (before tool execution, to validate target location)
        for key in OUTPUT_PATH_KEYS:
            if key in args:
                # base_path_for_cli is only used if session_id is None
                args[key] = process_path_arg(args[key], settings.PDF_FILES_ROOT, session_id, is_input=False, arg_key=key)

        in_hash_map = {}
        if processed_input_paths_for_hash:
            if isinstance(args.get('files'), list) and all(isinstance(p, str) for p in args.get('files', [])):
                 for p_path_str in args['files']:
                      in_hash_map[p_path_str] = hash_file(p_path_str)
            elif isinstance(args.get('file'), str):
                 in_hash_map[args['file']] = hash_file(args['file'])
            
            if processed_input_paths_for_hash: # Check again if list is not empty
                primary_in_hash = hash_file(processed_input_paths_for_hash[0])

        tool_module = importlib.import_module(f"tools.{tool_name}")
        logging.info(f"Executing tool: {tool_name} with processed args: {args} (Session: {session_id})")
        
        # Tool's run function should now use the full, validated paths from args
        tool_output = tool_module.run(args) # args now contains full paths

        output_path_to_hash = None
        if tool_output and isinstance(tool_output, str): # Assuming tool returns a single output file path
            # The tool_output path should already be an absolute, validated path (constructed by the tool or passed through args)
            # If the tool constructs its own output path, it must adhere to the session/CLI logic
            # For now, we assume 'output' in args was the intended full path for single file output
            if 'output' in args and args['output'] == tool_output:
                 output_path_to_hash = args['output']
            elif Path(tool_output).exists(): # If tool returns a path not in args, validate it now.
                # This scenario is tricky: what should be the expected_root?
                # For now, let's assume tool_output if a path, is already correct / validated by tool itself.
                # A more robust approach is for tools to *always* use the 'output' arg.
                output_path_to_hash = tool_output
                # Re-validate if it wasn't from args, assuming session context if available for uploads.
                # This part needs careful thought on contracts with tools.
                # validate(output_path_to_hash, pdf_uploads_root / session_id if session_id else pdf_files_root, session_id)

        out_hash = hash_file(output_path_to_hash) if output_path_to_hash and Path(output_path_to_hash).exists() else None
        
        # Log with original_args to see what user provided, but engine used 'args'
        log_trace(tool_name, args, primary_in_hash, out_hash, status="success")
        
        # --- BEGIN MODIFICATION: Return only basename for session files ---
        if session_id and tool_output and isinstance(tool_output, str):
            try:
                tool_output_path = Path(tool_output)
                # Check if the output path is within the session's upload directory
                session_upload_dir = settings.PDF_UPLOADS_ROOT / session_id
                if tool_output_path.is_relative_to(session_upload_dir.resolve()):
                    logging.info(f"run_tool: Returning basename '{tool_output_path.name}' for session output file '{tool_output}'")
                    return tool_output_path.name # Return only the filename
            except Exception as e:
                # Log if there's an issue with path comparison, but proceed to return original tool_output
                logging.warning(f"run_tool: Could not determine if '{tool_output}' is a session file, returning full path. Error: {e}")
        # --- END MODIFICATION ---
        
        return tool_output

    except FileNotFoundError as e:
        error_message = f"Error in run_tool ({tool_name}, Session: {session_id}): File not found - {e}"
        logging.error(error_message)
        # notify_slack(f"❌ PDFShell Engine Error: {error_message}")
        log_trace(tool_name, original_args, primary_in_hash, None, status="error", error_message=str(e))
        raise
    except ValueError as e: # Catches validation errors and other value errors
        error_message = f"Error in run_tool ({tool_name}, Session: {session_id}): Validation error or invalid arguments - {e}"
        logging.error(error_message)
        # notify_slack(f"❌ PDFShell Engine Error: {error_message}")
        log_trace(tool_name, original_args, primary_in_hash, None, status="error", error_message=str(e))
        raise
    except ImportError as e:
        error_message = f"Error in run_tool ({tool_name}, Session: {session_id}): Tool module not found - {e}"
        logging.error(error_message)
        # notify_slack(f"❌ PDFShell Engine Error: {error_message}")
        log_trace(tool_name, original_args, None, None, status="error", error_message=str(e))
        raise
    except Exception as e:
        error_message = f"An unexpected error occurred in run_tool ({tool_name}, Session: {session_id}): {e}"
        logging.error(error_message, exc_info=True)
        # notify_slack(f"❌ PDFShell Engine Error (Unexpected): {error_message}")
        log_trace(tool_name, original_args, primary_in_hash, None, status="error", error_message=str(e)) 
        raise
