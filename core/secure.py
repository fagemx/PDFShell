import os
import hashlib
import mimetypes
import logging
from pathlib import Path
from typing import List, Optional
from .alert import notify_slack

MAX_SIZE_MB = 25

def validate(
    full_path_str: str, 
    expected_root: Path, 
    session_id: str | None = None, 
    is_input: bool = True,
    accepted_mime_types: Optional[List[str]] = None
) -> bool:
    """
    Validates a file based on its full path, expected root directory, size, and MIME type.
    Ensures the file is within the expected root and does not use path traversal.
    Raises ValueError or FileNotFoundError if validation fails.
    Returns True if validation passes.
    """
    try:
        full_path = Path(full_path_str).resolve()
    except Exception as e:
        logging.error(f"Path resolution error for {full_path_str}: {e}")
        error_message = f"Invalid file path format: {full_path_str}"
        # notify_slack(f"❌ PDFShell Validation Error: {error_message} (Session: {session_id})")
        raise ValueError(error_message) from e

    # Determine the path to check against expected_root
    # For inputs, it's the file itself. For outputs, it's the parent directory.
    path_to_check_against_root = full_path if is_input else full_path.parent

    # 1. Check if the resolved path (or its parent for outputs) is within the expected_root
    if not str(path_to_check_against_root.absolute()).startswith(str(expected_root.resolve().absolute())):
        logging.error(f"Path traversal attempt or incorrect root: {path_to_check_against_root} is not under {expected_root}")
        error_message = f"Access denied: File path is outside of its designated directory."
        # notify_slack(f"❌ PDFShell Security Alert: Path Traversal Attempt? {path_to_check_against_root} outside {expected_root} (Session: {session_id})")
        raise ValueError(error_message)

    # 2. Double check for ".." in the path components after resolving,
    #    although resolve() should handle this, an explicit check is safer.
    #    This applies to both input and output paths.
    if ".." in full_path.parts:
        logging.error(f"Path traversal attempt using '..': {full_path}")
        error_message = "Access denied: Invalid path components ('..') found."
        # notify_slack(f"❌ PDFShell Security Alert: Path Traversal Attempt with '..' in {full_path} (Session: {session_id})")
        raise ValueError(error_message)

    # File existence and type check (only for inputs)
    if is_input:
        if not full_path.exists():
            logging.error(f"File not found for validation: {full_path}")
            error_message = f"File not found: {full_path.name}" # Show only filename to user
            # notify_slack(f"❌ PDFShell Validation Error: {error_message} (Path: {full_path}, Session: {session_id})")
            raise FileNotFoundError(error_message)
        if not full_path.is_file():
            logging.error(f"Path is not a file for validation: {full_path}")
            error_message = f"Path is not a file: {full_path.name}" # Show only filename to user
            # notify_slack(f"❌ PDFShell Validation Error: {error_message} (Path: {full_path}, Session: {session_id})")
            raise ValueError(error_message)

        # File size limit (only for inputs, or for outputs after creation if desired, but typically for inputs)
        try:
            file_size = full_path.stat().st_size
            if file_size > MAX_SIZE_MB * 1024 * 1024:
                logging.warning(f"File validation failed: {full_path} (Size: {file_size} bytes) exceeds {MAX_SIZE_MB}MB limit.")
                error_message = f"File '{full_path.name}' too large. Maximum size is {MAX_SIZE_MB}MB."
                # notify_slack(f"❌ PDFShell Validation Error: {error_message} (Path: {full_path}, Session: {session_id})")
                raise ValueError(error_message)
        except OSError as e:
            logging.error(f"Could not get file size for {full_path}: {e}")
            error_message = f"Could not get file size for {full_path.name}: {e}"
            # notify_slack(f"❌ PDFShell Validation Error: {error_message} (Path: {full_path}, Session: {session_id})")
            raise ValueError(error_message) from e

        # MIME type check (only for inputs)
        if accepted_mime_types is None:
            # Default to only accepting PDF if no specific list is provided
            accepted_mime_types = ["application/pdf"]
        
        mime_type, _ = mimetypes.guess_type(str(full_path))
        if mime_type not in accepted_mime_types:
            logging.warning(f"File validation failed: {full_path} (MIME type: {mime_type}) is not in accepted list: {accepted_mime_types}.")
            error_message = f"Invalid file type for '{full_path.name}': {mime_type}. Accepted types are: {', '.join(accepted_mime_types)}."
            # notify_slack(f"❌ PDFShell Validation Error: {error_message} (Path: {full_path}, Session: {session_id})")
            raise ValueError(error_message)
    
    logging.info(f"Path validation successful for: {full_path} (Input: {is_input}, Session: {session_id})")
    return True

def hash_file(path: str) -> str:
    """
    Calculates the SHA-256 hash of a file.
    """
    # Ensure file exists before hashing
    if not os.path.exists(path) or not os.path.isfile(path):
        logging.error(f"File not found for hashing: {path}")
        # Depending on desired behavior, could raise error or return a specific value
        raise FileNotFoundError(f"File not found for hashing: {path}")

    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(4096) # Read in 4KB chunks
                if not chunk:
                    break
                h.update(chunk)
    except IOError as e:
        logging.error(f"Could not read file for hashing {path}: {e}")
        raise IOError(f"Could not read file for hashing {path}: {e}")
        
    hex_digest = h.hexdigest()
    logging.info(f"Hashed file {path}: {hex_digest}")
    return hex_digest

# Placeholder for stripping JavaScript or other potentially malicious content from PDFs.
# This is a complex task and pypdf itself has some capabilities that can be explored.
# For MVP, this might be out of scope or a very basic attempt.
# from pypdf import PdfReader, PdfWriter
# def remove_javascript(input_path: str, output_path: str):
#     """
#     Attempts to remove JavaScript from a PDF.
#     Note: This is a simplistic approach and may not cover all cases.
#     """
#     try:
#         reader = PdfReader(input_path)
#         writer = PdfWriter()
#         writer.clone_document_from_reader(reader) # Clones the document structure
#         # pypdf's PdfWriter by default might not carry over JS, or specific methods are needed
#         # to strip it. Checking writer.remove_javascript() or similar if available.
#         # As of pypdf 3.x.x, direct JS removal might be through sanitization options
#         # or by rebuilding the PDF without JS actions.
#         # For now, simply cloning and writing might strip some JS, but not reliably.
#         
#         # A more robust way would be to iterate through objects and remove /S /JavaScript actions
#         # but this is low-level and error-prone.
#         # writer.remove_links() # Example, not for JS but shows removal capabilities
#         # writer.remove_annotations(annotation_filter=lambda annot: annot.get("/Subtype") == "/Widget" and annot.get("/FT") == "/Sig") # Example
# 
#         # If pypdf has a built-in sanitize or strip_javascript, use it.
#         # Otherwise, this function might need a more advanced library or be very limited.
#         # For MVP, we state this is a complex area.
#         # The PRD mentions "strip embedded JS" - pypdf might do this by default when
#         # simply reading and writing pages, or it might require explicit action.
#         # Let's assume for now that a simple read-write cycle with pypdf helps,
#         # but acknowledge it's not a foolproof solution.
#         
#         # writer.remove_custom_javascript_actions() # Fictional method, check pypdf docs
# 
#         with open(output_path, "wb") as f:
#             writer.write(f)
#         logging.info(f"Attempted to remove JavaScript from {input_path}, saved to {output_path}")
#     except Exception as e:
#         logging.error(f"Error removing JavaScript from {input_path}: {e}")
#         # Decide: raise error or proceed with original file?
#         # For now, log and potentially an admin should be notified.
#         # Depending on security policy, might re-raise or copy original.
#         # For MVP, simply logging the error might suffice.
#         raise # Re-raise for now to indicate failure in this step
