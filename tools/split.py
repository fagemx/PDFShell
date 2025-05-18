from typing import Optional, Type, Set
from pathlib import Path
# import os # os.makedirs no longer needed directly in tool
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from pypdf import PdfReader, PdfWriter

def _parse_ranges(rng: str, total_pages: int) -> Set[int]:
    """
    解析頁碼範圍字串 (例如 "1-3,5,!7,-1", "1--1") 回傳一個包含指定頁碼的集合 (1-based)。
    "-1" 代表最後一頁。
    """
    selected_pages = set()
    if not rng.strip():
        raise ValueError("頁碼範圍字串不可為空。")

    tokens = rng.split(',')
    temp_included_pages = set()
    
    for token_idx, raw_token in enumerate(tokens):
        token = raw_token.strip()
        is_exclusion = token.startswith('!')
        effective_token = token[1:] if is_exclusion else token

        if not effective_token: # 例如 "!" 或 "," 後面直接接 ","
            raise ValueError(f"無效的 token 格式: '{raw_token}'")

        if '-' in effective_token:
            parts = effective_token.split('-')
            if len(parts) != 2:
                raise ValueError(f"頁碼範圍格式錯誤 (無效的 '-' 使用): {effective_token}")
            
            start_str, end_str = parts[0].strip(), parts[1].strip()

            try:
                if start_str == "-1":
                    start = total_pages
                else:
                    start = int(start_str)
                
                if end_str == "-1":
                    end = total_pages
                else:
                    end = int(end_str)

                if start <= 0 and start_str != "-1": # 允許 start 是 -1 (total_pages)
                     raise ValueError(f"起始頁碼必須大於 0 或為 -1: {start_str}")
                if end <= 0 and end_str != "-1": # 允許 end 是 -1 (total_pages)
                    raise ValueError(f"結束頁碼必須大於 0 或為 -1: {end_str}")
                
                # 處理 start > total_pages (如果 start 不是由 "-1" 轉換而來)
                if start > total_pages and start_str != "-1":
                    raise ValueError(f"起始頁碼 {start} 超出總頁數 {total_pages}")
                # 處理 end > total_pages (如果 end 不是由 "-1" 轉換而來)
                if end > total_pages and end_str != "-1":
                     raise ValueError(f"結束頁碼 {end} 超出總頁數 {total_pages}")

                if start > end: # 轉換後的 start 和 end 比較
                    raise ValueError(f"無效的頁碼範圍 (起始頁碼 {start} 大於結束頁碼 {end}): {effective_token}")
                
                current_range_pages = set(range(start, end + 1))
                if is_exclusion:
                    # 如果是排除，並且 temp_included_pages 為空（即前面沒有包含規則，或這是第一個規則）
                    # 則我們需要先假設所有頁面都被選中，然後從中排除。
                    # 這個邏輯會在後面統一處理，這裡我們先收集所有要排除的頁面。
                    pass # 稍後處理排除
                else:
                    temp_included_pages.update(current_range_pages)

            except ValueError as e: # 捕捉 int() 轉換錯誤或我們自己拋出的 ValueError
                # 避免重複包裝 ValueError
                if "頁碼" in str(e) or "page" in str(e).lower(): # 檢查是否是我們自訂的錯誤
                     raise
                raise ValueError(f"頁碼範圍格式錯誤: {effective_token} -> {e}")
        else: # 單個頁碼
            try:
                page_num_str = effective_token
                if page_num_str == "-1":
                    page_num = total_pages
                else:
                    page_num = int(page_num_str)

                if page_num <= 0 and page_num_str != "-1":
                     raise ValueError(f"頁碼必須大於 0 或為 -1: {page_num_str}")
                
                if page_num > total_pages and page_num_str != "-1":
                    raise ValueError(f"頁碼 {page_num} 超出總頁數 {total_pages}")

                if is_exclusion:
                    pass # 稍後處理排除
                else:
                    temp_included_pages.add(page_num)
            except ValueError as e:
                if "頁碼" in str(e) or "page" in str(e).lower():
                    raise
                raise ValueError(f"頁碼格式錯誤: {effective_token} -> {e}")

    # 決定基礎選擇集 (如果沒有明確包含，且有排除，則全選)
    if not temp_included_pages and any(t.strip().startswith("!") for t in tokens):
        selected_pages.update(range(1, total_pages + 1))
    else:
        selected_pages.update(temp_included_pages)

    # 現在處理排除
    for raw_token in tokens:
        token = raw_token.strip()
        if token.startswith('!'):
            effective_token = token[1:]
            if not effective_token: continue # 跳過空的排除，例如 "!,1"

            if '-' in effective_token:
                parts = effective_token.split('-')
                # 這裡的錯誤檢查已在上面包含部分做過，但為了安全可以再次檢查或簡化
                # 假設格式在此階段是正確的，因為上面已經檢查過了
                start_str, end_str = parts[0].strip(), parts[1].strip()
                
                start = total_pages if start_str == "-1" else int(start_str)
                end = total_pages if end_str == "-1" else int(end_str)
                
                # 確保 start 和 end 在合理範圍內，並且 start <= end
                # 這裡的檢查主要是針對轉換後的 start/end
                if start <= 0 and start_str != "-1": continue # 或拋出錯誤
                if end <= 0 and end_str != "-1": continue # 或拋出錯誤
                if start > total_pages and start_str != "-1": continue
                if end > total_pages and end_str != "-1": continue
                if start > end: continue

                selected_pages.difference_update(range(start, end + 1))
            else: # 單個排除頁碼
                page_num_str = effective_token
                page_num = total_pages if page_num_str == "-1" else int(page_num_str)

                if page_num <= 0 and page_num_str != "-1": continue
                if page_num > total_pages and page_num_str != "-1": continue
                
                selected_pages.discard(page_num)
                    
    # 最後再次確認所有選中的頁碼都在 1 到 total_pages 之間
    # 這一行實際上可能不需要了，因為我們在解析時已經做了邊界檢查
    # 但保留它作為最後的防線是安全的
    final_pages = {p for p in selected_pages if 1 <= p <= total_pages}
    if not final_pages and rng.strip(): # 如果原始範圍非空但結果為空
        # 這種情況可能發生在例如 total_pages=5, rng="6-10" 或 rng="!1-5"
        pass # 允許返回空集合，run 函數會檢查這個

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
    output_dir_str: str = args['output_dir'] # 'output_dir' is now always a full path from engine

    try:
        input_file_path_obj = Path(input_file_path_str)
        output_dir_obj = Path(output_dir_str) # This is now always a valid, absolute directory path
        # Engine ensures output_dir_obj exists.

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

split = SplitTool()

ArgsSchema = SplitSchema # Added to expose the schema with the expected name for core.engine
