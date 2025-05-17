from typing import List, Type
from pathlib import Path
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from pypdf import PdfReader, PdfWriter
import logging

class MergeSchema(BaseModel):
    files: List[str] = Field(description="A list of FULL PATHS to the input PDF files to be merged.")
    output: str = Field(description="The FULL PATH for the output merged PDF file.")

# The engine will call a 'run' function directly, not as a BaseTool._run
# However, the schema can still be useful for validation if used elsewhere or for documentation.

# def run(args: dict) -> str: # Conforming to what engine.py expects
# This can be a standalone function if BaseTool structure is not strictly needed for dynamic loading by engine

# For consistency with how engine.py loads tools, we expect a run(args) function.
# If this file is meant to be a Langchain tool primarily, the structure might differ.
# Assuming engine.py is the primary consumer calling tools.tool_name.run(args)

def run(args: dict) -> str:
    """Merges multiple PDF files into a single PDF file.
    The 'files' and 'output' in args are expected to be full, validated, absolute paths.
    """
    files_list: List[str] = args['files']
    output_path_str: str = args['output']

    try:
        writer = PdfWriter()
        
        for file_path_str in files_list:
            # Paths are already full and validated by the engine
            reader = PdfReader(file_path_str)
            for page in reader.pages:
                writer.add_page(page)
        
        # Output path is also full and validated; parent directory created by engine
        with open(output_path_str, "wb") as f:
            writer.write(f)
        
        # === BEGIN DEBUGGING MODIFICATION ===
        logger = logging.getLogger(__name__) # Ensure logger is available
        output_path_obj = Path(output_path_str)
        if output_path_obj.exists() and output_path_obj.is_file():
            logger.info(f"MERGE TOOL: Successfully wrote output file to: {output_path_str} (Size: {output_path_obj.stat().st_size} bytes)")
        else:
            logger.error(f"MERGE TOOL: FAILED to write or find output file at: {output_path_str}")
        # === END DEBUGGING MODIFICATION ===

        return output_path_str # Return the full output path

    except Exception as e:
        # Log or handle more gracefully if needed
        # print(f"An unexpected error occurred in merge tool: {e}")
        # import traceback
        # traceback.print_exc()
        # Re-raise for the engine to catch and log centrally
        raise RuntimeError(f"Error during PDF merging: {e}")

# If you intend to keep the Langchain tool structure for other purposes:
class MergeTool(BaseTool):
    name: str = "merge"
    description: str = "Merges multiple PDF files into a single PDF file. Expects full paths."
    args_schema: Type[BaseModel] = MergeSchema

    # root_dir: Path = Path.cwd() # No longer needed if paths are absolute

    def _run(self, files: List[str], output: str) -> str:
        # This method would now call the standalone run function if you want to keep it
        # or duplicate the logic, ensuring paths are treated as absolute.
        # For the engine, it will call tools.merge.run(args)
        # If this _run is still needed, it should mirror the logic of the standalone run.
        
        # Simplified: assuming the standalone run function is the primary logic
        return run({"files": files, "output": output})
