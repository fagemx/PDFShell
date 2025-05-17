from typing import Optional, Type, Set
from pathlib import Path
# import os # os.makedirs no longer needed directly in tool
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from pypdf import PdfReader, PdfWriter

def _parse_ranges(rng: str, total_pages: int) -> Set[int]:
    """
    解析頁碼範圍字串 (例如 "1-3,5,!7") 回傳一個包含指定頁碼的集合 (1-based)。
    """
    selected_pages = set()
    if not rng.strip():
        raise ValueError("頁碼範圍字串不可為空。")

    tokens = rng.split(',')
    temp_included_pages = set()
    for token in tokens:
        token = token.strip()
        if not token.startswith('!'):
            if '-' in token:
                try:
                    start, end = map(int, token.split('-'))
                    if start <= 0 or end <= 0 or start > end:
                        raise ValueError(f"無效的頁碼範圍: {token}")
                    temp_included_pages.update(range(start, end + 1))
                except ValueError:
                    raise ValueError(f"頁碼範圍格式錯誤: {token}")
            else:
                try:
                    page_num = int(token)
                    if page_num <= 0:
                        raise ValueError(f"無效的頁碼: {token}")
                    temp_included_pages.add(page_num)
                except ValueError:
                    raise ValueError(f"頁碼格式錯誤: {token}")
    
    if not temp_included_pages and any(t.startswith("!") for t in tokens):
        selected_pages.update(range(1, total_pages + 1))
    else:
        selected_pages.update(temp_included_pages)

    for token in tokens:
        token = token.strip()
        if token.startswith('!'):
            token_val = token[1:]
            if '-' in token_val:
                try:
                    start, end = map(int, token_val.split('-'))
                    if start <= 0 or end <= 0 or start > end:
                        raise ValueError(f"無效的排除頁碼範圍: {token_val}")
                    selected_pages.difference_update(range(start, end + 1))
                except ValueError:
                    raise ValueError(f"排除頁碼範圍格式錯誤: {token_val}")
            else:
                try:
                    page_num = int(token_val)
                    if page_num <= 0:
                        raise ValueError(f"無效的排除頁碼: {token_val}")
                    selected_pages.discard(page_num)
                except ValueError:
                    raise ValueError(f"排除頁碼格式錯誤: {token_val}")
                    
    final_pages = {p for p in selected_pages if 1 <= p <= total_pages}
    return final_pages

class SplitSchema(BaseModel):
    file: str = Field(description="The FULL PATH to the input PDF file.")
    pages: str = Field(description="Page ranges to split (e.g., \"1-3,5,!7\").")
    output_dir: Optional[str] = Field(description="FULL PATH to the directory to save the split PDF files. If not provided, a default name in a standard location will be used by the engine.")

def run(args: dict) -> str:
    """Splits a PDF file into multiple pages or page ranges.
    Outputs a new PDF containing only the selected pages.
    The 'file' and 'output_dir' in args are expected to be full, validated, absolute paths.
    """
    input_file_path_str: str = args['file']
    pages_str: str = args['pages']
    # output_dir_str is a full path to a directory, validated and created by the engine.
    # The default value for output_dir in YAML is ".", engine resolves this.
    output_dir_str: str = args.get('output_dir') 

    if not output_dir_str:
        # This case should ideally be handled by the engine providing a default output path
        # or the tool yml having a more specific default that engine can resolve.
        # For now, if engine passes it as None/empty due to yml default '.', raise error or use input file's dir.
        # Let's assume engine guarantees output_dir is a valid dir path if the key was in original_args.
        # If 'output_dir' was NOT in original_args, then the tool should define a default name for 'output'
        # and the engine would prepare that. For split, the output is implicitly named.
        # This highlights a need for clarity on how output_dir for split interacts with engine logic.
        # For now, if engine provides it, we use it. If not, it's an issue.
        # The current engine logic for OUTPUT_PATH_KEYS['output_dir'] will ensure it's a valid full path to a directory.
        raise ValueError("output_dir must be provided by the calling engine after path processing.")

    try:
        input_file_path_obj = Path(input_file_path_str)
        output_dir_obj = Path(output_dir_str)

        reader = PdfReader(input_file_path_str)
        total_pages = len(reader.pages)
        
        selected_page_numbers = _parse_ranges(pages_str, total_pages)
        
        if not selected_page_numbers:
            raise ValueError("No pages selected for splitting based on the provided range.")

        writer = PdfWriter()
        pages_to_keep_indices = sorted([p - 1 for p in selected_page_numbers])  

        for page_index in pages_to_keep_indices:
            if 0 <= page_index < total_pages:
                writer.add_page(reader.pages[page_index])
        
        if not writer.pages:
            raise ValueError("No valid pages to write to the new PDF (selected pages might be out of actual page range)." )

        # Output filename is based on input file's stem
        output_filename = f"{input_file_path_obj.stem}_split.pdf"
        # The output_dir_obj is already a full, validated path to an existing directory
        output_file_full_path = output_dir_obj / output_filename

        with open(output_file_full_path, "wb") as fp:
            writer.write(fp)
        
        return str(output_file_full_path) # Return the full output path

    except ValueError as e: # Catch parsing errors or no pages selected
        raise # Re-raise for the engine to catch
    except Exception as e:
        # Log or handle more gracefully if needed
        # print(f"An unexpected error occurred in split tool: {e}")
        # import traceback
        # traceback.print_exc()
        raise RuntimeError(f"Error during PDF splitting: {e}")

class SplitTool(BaseTool):
    name: str = "split"
    description: str = "Splits a PDF file into multiple pages or page ranges. Outputs a new PDF containing only the selected pages. Expects full paths."
    args_schema: Type[BaseModel] = SplitSchema

    # root_dir: Path = Path.cwd() # No longer needed

    def _run(self, file: str, pages: str, output_dir: Optional[str] = None) -> str:
        # Engine calls tools.split.run(args)
        # This _run is for Langchain compatibility if used directly.
        # output_dir handling: if None, it means the tool's yml default (".") was used.
        # The standalone 'run' function now expects engine to resolve this default.
        # For direct _run call here, we'd need to simulate engine's default path resolution or have run handle it.
        
        # For simplicity, if _run is called directly, we assume it needs to construct a default if None.
        # However, the main `run` function is stricter as it expects engine-processed paths.
        # This highlights that `output_dir` default handling needs to be robust.
        # Let's assume _run call also means output_dir is a fully resolved path or needs default handling.
        args_dict = {"file": file, "pages": pages}
        if output_dir:
            args_dict["output_dir"] = output_dir
        else:
            # If called directly via Langchain and output_dir is None (meaning default '.'),
            # the `run` function above will currently raise an error.
            # This indicates that tools relying on implicit default output locations handled by the engine
            # are best called *through* the engine.
            # For a direct call, we might make `run` more flexible or have _run do more prep.
            # For now, this will likely fail if output_dir is None and _run is called.
            # A quick fix for _run might be: args_dict["output_dir"] = Path.cwd() / "output"
            # But this deviates from engine logic. Best to call via engine.
            pass # `run` will raise error if output_dir not in args or not processed correctly by engine.
                 # If yml default is '.', engine should resolve it to a concrete dir path.

        return run(args_dict)
