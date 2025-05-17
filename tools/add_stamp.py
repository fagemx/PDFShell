from typing import Optional, Type, Literal
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from pathlib import Path
from pypdf import PdfReader, PdfWriter, PageObject
from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import letter # Not strictly needed if using target page dimensions
from io import BytesIO
import logging

class AddStampSchema(BaseModel):
    file: str = Field(description="The FULL PATH to the input PDF file.")
    stamp_path: str = Field(description="The FULL PATH to the stamp image file (e.g., PNG, JPG).")
    page: int = Field(description="The page number to add the stamp to. Use 1 for the first page, -1 for the last page.")
    pos: Optional[Literal["br", "tr", "tl", "bl"]] = Field(default="br", description="Position of the stamp. Defaults to 'br'.")
    scale: Optional[float] = Field(default=1.0, description="Scale factor for the stamp image. Defaults to 1.0.")
    output: Optional[str] = Field(default=None, description="The FULL PATH for the output stamped PDF file. If None, '_stamped' is appended to the input file name in the same directory.")

def run(args: dict) -> str:
    """Adds an image stamp to a specified page of a PDF file.
    Assumes 'file', 'stamp_path', and 'output' (if provided) in args are full, validated, absolute paths.
    """
    input_file_str: str = args['file']
    stamp_image_str: str = args['stamp_path']
    page_num: int = args['page']
    position: str = args.get('pos', "br")
    scale_factor: float = args.get('scale', 1.0)
    output_file_str: Optional[str] = args.get('output')

    try:
        input_file_path = Path(input_file_str)
        stamp_image_path = Path(stamp_image_str)

        if output_file_str:
            output_final_path = Path(output_file_str)
        else:
            # If output is not provided by engine, create it in the same dir as input
            output_final_path = input_file_path.with_stem(input_file_path.stem + "_stamped").with_suffix(".pdf")
        
        # Engine should have created the parent directory for output_final_path if it was in args.
        # If output was None and we just constructed output_final_path, we rely on input_file_path.parent existing.
        # This is generally safe as input_file_path is validated.

        reader = PdfReader(input_file_str)
        if not reader.pages:
            raise ValueError("The input PDF has no pages.")

        writer = PdfWriter() # Initialize writer here to add all pages

        if page_num == 0: # Stamp all pages
            for i, current_target_page in enumerate(reader.pages):
                packet = BytesIO()
                canvas_width = float(current_target_page.mediabox.width)
                canvas_height = float(current_target_page.mediabox.height)
                c = canvas.Canvas(packet, pagesize=(canvas_width, canvas_height))

                img_base_w, img_base_h = 150, 75
                img_w, img_h = img_base_w * scale_factor, img_base_h * scale_factor

                if position == "br": xy = (canvas_width - img_w - 20, 20)
                elif position == "tr": xy = (canvas_width - img_w - 20, canvas_height - img_h - 20)
                elif position == "tl": xy = (20, canvas_height - img_h - 20)
                elif position == "bl": xy = (20, 20)
                else: xy = (canvas_width - img_w - 20, 20) # Default to bottom-right

                c.drawImage(str(stamp_image_path), xy[0], xy[1], width=img_w, height=img_h, mask='auto')
                c.save()
                packet.seek(0)

                overlay_reader = PdfReader(packet)
                if not overlay_reader.pages:
                    logging.warning(f"Failed to create overlay for page {i+1}. Skipping stamp for this page.")
                    # Add original page without stamp if overlay fails
                    # writer.add_page(current_target_page) # This would add it again if loop continues, instead make sure all pages are added at the end or original is preserved
                    # The current_target_page is a reference from reader.pages, so if we don't merge, it remains original.
                    # We must add *every* page from the reader to the writer, stamped or not.
                    continue # Skip merging for this page
                
                current_target_page.merge_page(overlay_reader.pages[0])
                # No need to add page to writer here, done after loop for all pages from reader
            
            # After loop, all pages (modified or not) from reader are added to writer
            for p_item in reader.pages:
                writer.add_page(p_item)

        else: # Stamp a single page
            actual_page_input_for_user_msg = page_num # page_num is already not 0 here
            
            if actual_page_input_for_user_msg < 0:
                target_page_index = len(reader.pages) + actual_page_input_for_user_msg
            else:
                target_page_index = actual_page_input_for_user_msg - 1

            if not (0 <= target_page_index < len(reader.pages)):
                raise ValueError(f"Page number {actual_page_input_for_user_msg} is out of range for PDF with {len(reader.pages)} pages.")

            target_page: PageObject = reader.pages[target_page_index]
            packet = BytesIO()
            canvas_width = float(target_page.mediabox.width)
            canvas_height = float(target_page.mediabox.height)
            c = canvas.Canvas(packet, pagesize=(canvas_width, canvas_height))

            img_base_w, img_base_h = 150, 75 
            img_w, img_h = img_base_w * scale_factor, img_base_h * scale_factor

            if position == "br": xy = (canvas_width - img_w - 20, 20)
            elif position == "tr": xy = (canvas_width - img_w - 20, canvas_height - img_h - 20)
            elif position == "tl": xy = (20, canvas_height - img_h - 20)
            elif position == "bl": xy = (20, 20)
            else: xy = (canvas_width - img_w - 20, 20) # Default to bottom-right

            c.drawImage(str(stamp_image_path), xy[0], xy[1], width=img_w, height=img_h, mask='auto')
            c.save()
            packet.seek(0)

            overlay_reader = PdfReader(packet)
            if not overlay_reader.pages:
                raise ValueError("Failed to create overlay page from stamp.")
            
            target_page.merge_page(overlay_reader.pages[0])
            
            # Add all pages from reader to writer, ensuring modified one is included
            for p_item in reader.pages:
                writer.add_page(p_item)

        with open(output_final_path, "wb") as fp:
            writer.write(fp)
        
        return str(output_final_path) # Return the full output path

    except ValueError as e: # Covers page range, no pages in PDF, overlay creation fail
        raise
    except Exception as e:
        # import traceback
        # logging.error(f"AddStampTool error: {traceback.format_exc()}")
        raise RuntimeError(f"An unexpected error occurred while adding the stamp: {e}")

class AddStampTool(BaseTool):
    name: str = "add_stamp"
    description: str = ("Adds an image stamp to a specified page of a PDF file. "
                       "Expects full paths for 'file', 'stamp_path', and 'output' (if provided).")
    args_schema: Type[BaseModel] = AddStampSchema

    def _run(
        self,
        file: str,
        stamp_path: str,
        page: int,
        pos: Optional[str] = "br",
        scale: Optional[float] = 1.0,
        output: Optional[str] = None,
    ) -> str:
        args_dict = {
            "file": file,
            "stamp_path": stamp_path,
            "page": page,
            "pos": pos,
            "scale": scale,
        }
        if output:
            args_dict["output"] = output
        # If output is None here, the standalone `run` will create a default name
        # in the same directory as the input file.
        return run(args_dict)

# If this file were to be loaded by a loader that expects a single 'tool' instance:
# tool = AddStampTool()
# However, with create_structured_chat_agent, we'll import the class and instantiate it in agent.py
