import re
import io
from typing import List, Optional, Type
from pathlib import Path
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import black
import logging # Added logging

class RedactSchema(BaseModel):
    file: str = Field(description="The FULL PATH to the input PDF file.")
    patterns: List[str] = Field(description="A list of regex patterns to search for and redact.")
    output: Optional[str] = Field(default=None, description="The FULL PATH for the output redacted PDF file. If None, '_redacted' is appended to the input file name in the same directory.")

def run(args: dict) -> str:
    """Redacts text in a PDF file based on a list of regex patterns.
    For MVP, this draws a noticeable black box on pages where a pattern is matched.
    Assumes 'file' and 'output' (if provided) in args are full, validated, absolute paths.
    """
    input_file_str: str = args['file']
    patterns_list: List[str] = args['patterns']
    output_file_str: Optional[str] = args.get('output')

    try:
        input_file_path = Path(input_file_str)

        if output_file_str:
            output_final_path = Path(output_file_str)
        else:
            output_final_path = input_file_path.with_stem(input_file_path.stem + "_redacted").with_suffix(".pdf")

        compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns_list]

        reader = PdfReader(input_file_str)
        writer = PdfWriter()

        if not reader.pages:
            # Although engine should validate, good to have a check if an empty PDF somehow passes
            logging.warning(f"Input PDF {input_file_str} has no pages.")
            # Decide behavior: return original path, raise error, or return empty PDF path?
            # For now, let's write an empty PDF to the output path if no pages.
            # Or, more consistently, if the writer ends up with no pages, handle it there.
            pass # Let it proceed, writer will be empty if no pages.

        for page_obj in reader.pages:
            page_text = page_obj.extract_text() or ""
            overlay_packet = io.BytesIO()
            
            page_width = float(page_obj.mediabox.width)
            page_height = float(page_obj.mediabox.height)
            c = Canvas(overlay_packet, pagesize=(page_width, page_height))
            
            found_match_on_page = False
            for pattern in compiled_patterns:
                if pattern.search(page_text):
                    found_match_on_page = True
                    break
            
            if found_match_on_page:
                box_height = 20 
                y_position = page_height / 2 - (box_height / 2)
                c.setFillColor(black)
                c.rect(0, y_position, page_width, box_height, stroke=0, fill=1)
                c.save()
                overlay_packet.seek(0)
                
                overlay_reader = PdfReader(overlay_packet)
                if overlay_reader.pages:
                    overlay_page = overlay_reader.pages[0]
                    page_obj.merge_page(overlay_page)
            
            writer.add_page(page_obj)
        
        if not writer.pages and reader.pages: # Input had pages, but output doesn't (e.g. all pages redacted away - not current logic)
             logging.info(f"Redaction resulted in an empty PDF for {input_file_str}. Writing an empty PDF.")
        elif not writer.pages and not reader.pages:
            logging.info(f"Input PDF {input_file_str} was empty. Writing an empty output PDF.")

        with open(output_final_path, "wb") as fp:
            writer.write(fp)
        
        return str(output_final_path) # Return the full output path

    except Exception as e:
        # logging.error(f"RedactTool error: {traceback.format_exc()}")
        raise RuntimeError(f"An unexpected error occurred while redacting the PDF: {e}")

class RedactTool(BaseTool):
    name: str = "redact"
    description: str = ("Redacts text in a PDF file based on a list of regex patterns. "
                       "For MVP, this draws a noticeable black box on pages where a pattern is matched. "
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
