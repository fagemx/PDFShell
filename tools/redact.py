import re
# import io # 可能不再需要 io # Removing this line as per plan
from typing import List, Optional, Type
from pathlib import Path
from langchain_core.tools import BaseTool # 保留 Langchain 整合
from pydantic import BaseModel, Field # 保留 Pydantic 驗證
import logging

# 新增 Docling 導入
from docling.document_converter import DocumentConverter
# from pypdf import PdfReader, PdfWriter # 這些可能不再直接使用，或僅用於後續的視覺遮蔽（本次不作此目標）
# from reportlab.pdfgen.canvas import Canvas # 同上
# from reportlab.lib.colors import black # 同上


class RedactSchema(BaseModel): # Pydantic Schema 維持不變
    file: str = Field(description="The FULL PATH to the input PDF file.")
    patterns: List[str] = Field(description="A list of regex patterns to search for and redact.")
    output: Optional[str] = Field(default=None, description="The FULL PATH for the output redacted TEXT/MARKDOWN file. If None, '_redacted.txt' is appended to the input file name in the same directory.") # 修改描述

def run(args: dict) -> str:
    """
    Redacts text in a PDF file based on a list of regex patterns using Docling.
    Outputs a text or markdown file with matched patterns replaced by [REDACTED].
    Assumes 'file' and 'output' in args are full, validated, absolute paths.
    """
    input_file_str: str = args['file']
    patterns_list: List[str] = args['patterns']
    output_final_path_str: str = args['output'] # 'output' is now always a full path from engine

    try:
        input_file_path = Path(input_file_str) # Still needed for logging and to check existence
        if not input_file_path.exists():
            logging.error(f"Input file not found: {input_file_str}")
            raise FileNotFoundError(f"Input file not found: {input_file_str}")

        output_final_path = Path(output_final_path_str)
        # Engine ensures parent directory for output_final_path exists.
        # Suffix check for .txt or .md can remain if desired, or be removed if engine guarantees correct default suffix.
        # For now, let's assume engine provides a filename with a sensible suffix like .md for redact default.
        # if output_final_path.suffix.lower() not in ['.txt', '.md']:
        #     logging.warning(f"Output file {output_final_path} does not have .txt or .md suffix. Defaulting to .md for content.")

        logging.info(f"Redacting PDF: {input_file_path} with Docling. Outputting to: {output_final_path}")

        # Docling 讀取/解析文件
        converter = DocumentConverter()
        docling_doc = converter.convert(str(input_file_path)) # convert() 需要 string 類型的路徑

        # 取得 Markdown 格式的內容 (Docling 能較好地處理版面結構轉 Markdown)
        # 如果只要純文字，可以用 docling_doc.document.get_full_text() 或類似方法
        content = docling_doc.document.export_to_markdown()
        if not content:
            logging.warning(f"Docling extracted no content from {input_file_path}")
            # 寫入一個空的輸出檔案
            with open(output_final_path, "w", encoding="utf-8") as f:
                f.write("")
            return str(output_final_path)

        compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns_list]
        
        redacted_content = content
        for pattern in compiled_patterns:
            # 將匹配到的文字替換為 "[REDACTED]"
            redacted_content = pattern.sub("[REDACTED]", redacted_content)

        # 寫入處理後的 Markdown 內容
        with open(output_final_path, "w", encoding="utf-8") as f:
            f.write(redacted_content)
        
        logging.info(f"Redacted content saved to {output_final_path}")
        return str(output_final_path)

    except FileNotFoundError as e:
        logging.error(f"File not found during redaction: {e}")
        raise e # 重新拋出以便上層處理
    except Exception as e:
        logging.error(f"Error during Docling redaction process: {e}", exc_info=True) # exc_info=True 會記錄堆疊追蹤
        raise RuntimeError(f"An unexpected error occurred while redacting the PDF with Docling: {e}")

# BaseTool class 和 _run 方法保持不變，因為它只是調用上面的 run 函數
class RedactTool(BaseTool):
    name: str = "redact"
    description: str = ("Redacts text in a PDF file based on a list of regex patterns using Docling. "
                       "Outputs a text/markdown file with matched patterns replaced by [REDACTED]. " # 更新描述
                       "Expects full paths for 'file' and 'output' (if provided).")
    args_schema: Type[BaseModel] = RedactSchema

    def _run(self, file: str, patterns: List[str], output: Optional[str] = None) -> str:
        args_dict = {
            "file": file,
            "patterns": patterns,
        }
        if output:
            args_dict["output"] = output
        return run(args_dict)

redact = RedactTool()

ArgsSchema = RedactSchema # Added to expose the schema with the expected name for core.engine
