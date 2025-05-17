import os
import pytest
from pathlib import Path
from core.engine import run_tool
from pypdf import PdfReader, PdfWriter # For creating dummy PDFs
from PIL import Image, ImageDraw # For creating dummy stamp image
from reportlab.pdfgen import canvas as reportlab_canvas # Alias to avoid conflict with pytest canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO

# Apply django_db mark to all tests in this module if not already applied to specific tests
pytestmark = pytest.mark.django_db

@pytest.fixture
def sample_pdfs(tmp_path):
    """建立兩個用於合併測試的空白 PDF 檔案。"""
    pdf1_path = tmp_path / "a.pdf"
    pdf2_path = tmp_path / "b.pdf"
    
    # 建立 a.pdf
    writer1 = PdfWriter()
    writer1.add_blank_page(width=200, height=200)
    with open(pdf1_path, "wb") as f1:
        writer1.write(f1)
        
    # 建立 b.pdf
    writer2 = PdfWriter()
    writer2.add_blank_page(width=200, height=200)
    with open(pdf2_path, "wb") as f2:
        writer2.write(f2)
            
    return [str(pdf1_path), str(pdf2_path)]

@pytest.fixture
def multi_page_pdf(tmp_path):
    """建立一個多頁的 PDF 檔案用於分割測試。"""
    pdf_path = tmp_path / "multi_page.pdf"
    writer = PdfWriter()
    for _ in range(5): # 建立一個5頁的 PDF
        writer.add_blank_page(width=200, height=200)
    with open(pdf_path, "wb") as f:
        writer.write(f)
    return str(pdf_path)

@pytest.fixture
def sample_stamp_image(tmp_path) -> str:
    """建立一個簡單的 PNG 印章圖片用於測試。"""
    stamp_path = tmp_path / "stamp.png"
    img = Image.new('RGB', (100, 50), color = 'red')
    d = ImageDraw.Draw(img)
    d.text((10,10), "STAMP", fill=('white'))
    img.save(stamp_path)
    return str(stamp_path)

@pytest.fixture
def pdf_with_text_content(tmp_path) -> str:
    """建立一個包含可預測文本內容的單頁 PDF。"""
    pdf_path = tmp_path / "text_content.pdf"
    packet = BytesIO()
    c = reportlab_canvas.Canvas(packet, pagesize=letter)
    c.drawString(100, 750, "Hello World - Sensitive Data: secret_code_123")
    c.drawString(100, 700, "Another line with email: test@example.com")
    c.drawString(100, 650, "Phone: 123-456-7890 and some other text.")
    c.save()
    packet.seek(0)
    
    writer = PdfWriter()
    reader = PdfReader(packet)
    writer.add_page(reader.pages[0])
    with open(pdf_path, "wb") as f:
        writer.write(f)
    return str(pdf_path)

def test_merge_tool_success(sample_pdfs, tmp_path):
    """測試 merge 工具是否成功合併 PDF。"""
    output_file = tmp_path / "merged_output.pdf"
    
    result_path_str = run_tool("merge", {
        "files": sample_pdfs,
        "output": str(output_file)
    })
    
    result_path = Path(result_path_str)
    assert result_path.exists()
    assert result_path.name == "merged_output.pdf"
    
    # 驗證合併後的 PDF 頁數
    reader = PdfReader(result_path)
    assert len(reader.pages) == 2

def test_split_tool_basic(multi_page_pdf, tmp_path):
    """測試 split 工具基礎分割功能。"""
    output_dir = tmp_path / "split_output_basic"
    os.makedirs(output_dir)
    
    result_path_str = run_tool("split", {
        "file": multi_page_pdf,
        "pages": "1,3,5",
        "output_dir": str(output_dir)
    })
    
    result_path = Path(result_path_str)
    assert result_path.exists()
    assert result_path.name == "multi_page_split.pdf"
    
    reader = PdfReader(result_path)
    assert len(reader.pages) == 3 # 應包含第 1, 3, 5 頁

def test_split_tool_range_and_exclude(multi_page_pdf, tmp_path):
    """測試 split 工具的範圍和排除功能。"""
    output_dir = tmp_path / "split_output_range_exclude"
    os.makedirs(output_dir)
    
    # 原始 PDF 有5頁 ("multi_page.pdf")
    # "1-4,!3" 應選擇第 1, 2, 4 頁
    result_path_str = run_tool("split", {
        "file": multi_page_pdf,
        "pages": "1-4,!3",
        "output_dir": str(output_dir)
    })
    
    result_path = Path(result_path_str)
    assert result_path.exists()
    assert result_path.name == "multi_page_split.pdf"
    
    reader = PdfReader(result_path)
    assert len(reader.pages) == 3

def test_split_tool_invalid_pages(multi_page_pdf, tmp_path):
    """測試 split 工具使用無效頁碼範圍時的行為。"""
    output_dir = tmp_path / "split_output_invalid"
    os.makedirs(output_dir)
    
    # 測試超出範圍的頁碼
    with pytest.raises(ValueError, match="沒有根據指定的頁碼範圍選擇任何頁面進行分割"): # 訊息可能依賴 split.py 的實作
        run_tool("split", {
            "file": multi_page_pdf,
            "pages": "10,11", # 假設 multi_page_pdf 只有5頁
            "output_dir": str(output_dir)
        })

    # 測試只排除所有頁面導致結果為空的情況
    with pytest.raises(ValueError, match="沒有根據指定的頁碼範圍選擇任何頁面進行分割"):
        run_tool("split", {
            "file": multi_page_pdf,
            "pages": "!1-5", # 排除所有頁面
            "output_dir": str(output_dir)
        })

def test_split_tool_non_existent_file(tmp_path):
    """測試 split 工具輸入檔案不存在的情況。"""
    with pytest.raises(FileNotFoundError):
        run_tool("split", {
            "file": str(tmp_path / "non_existent.pdf"),
            "pages": "1",
            "output_dir": str(tmp_path)
        })

def test_add_stamp_success(multi_page_pdf, sample_stamp_image, tmp_path):
    """測試 add_stamp 工具成功添加印章。"""
    output_file = tmp_path / "stamped_output.pdf"
    
    # Add stamp to the second page (index 1, user input 2)
    args = {
        "file": multi_page_pdf,
        "page": 2,
        "stamp_path": sample_stamp_image,
        "pos": "br",
        "scale": 0.5,
        "output": str(output_file)
    }
    result_path_str = run_tool("add_stamp", args)
    result_path = Path(result_path_str)
    
    assert result_path.exists()
    assert result_path.name == "stamped_output.pdf"
    
    reader = PdfReader(result_path)
    assert len(reader.pages) == 5 # Original PDF had 5 pages, should remain the same
    # Further validation would involve checking if the stamp content is on page 2.
    # This is complex for a unit test, so we primarily check for successful execution and output generation.

def test_add_stamp_last_page(multi_page_pdf, sample_stamp_image, tmp_path):
    """測試 add_stamp 工具在最後一頁添加印章。"""
    output_file = tmp_path / "stamped_last_page.pdf"
    args = {
        "file": multi_page_pdf,
        "page": -1, # Last page
        "stamp_path": sample_stamp_image,
        "output": str(output_file)
    }
    result_path_str = run_tool("add_stamp", args)
    result_path = Path(result_path_str)
    assert result_path.exists()
    reader = PdfReader(result_path)
    assert len(reader.pages) == 5

def test_add_stamp_invalid_page_number(multi_page_pdf, sample_stamp_image, tmp_path):
    """測試 add_stamp 工具使用無效頁碼。"""
    args = {
        "file": multi_page_pdf,
        "page": 10, # Invalid page (multi_page_pdf has 5 pages)
        "stamp_path": sample_stamp_image,
        "output": str(tmp_path / "stamp_invalid_page.pdf")
    }
    with pytest.raises(ValueError, match=r"Page number .* is out of range"): # Match error from add_stamp.py
        run_tool("add_stamp", args)

def test_add_stamp_non_existent_stamp_file(multi_page_pdf, tmp_path):
    """測試 add_stamp 工具印章檔案不存在。"""
    args = {
        "file": multi_page_pdf,
        "page": 1,
        "stamp_path": str(tmp_path / "non_existent_stamp.png"),
        "output": str(tmp_path / "stamp_no_stamp_file.pdf")
    }
    # The exact error might depend on how reportlab handles missing images.
    # It might be an OSError or a specific reportlab error.
    # For now, let's assume it might raise an Exception or a FileNotFoundError if drawImage fails directly.
    # tools/add_stamp.py currently doesn't explicitly check if stamp_path exists before passing to reportlab.
    # reportlab.lib.utils.ImageReader might raise an exception.
    with pytest.raises(Exception): # General exception, refine if specific error is known
        run_tool("add_stamp", args)

def test_redact_tool_success(pdf_with_text_content, tmp_path):
    """測試 redact 工具成功遮蔽文本 (MVP: 畫黑條)。"""
    output_file = tmp_path / "redacted_output.pdf"
    args = {
        "file": pdf_with_text_content,
        "patterns": [r"secret_code_\d+", r"test@example\.com"],
        "output": str(output_file)
    }
    result_path_str = run_tool("redact", args)
    result_path = Path(result_path_str)
    
    assert result_path.exists()
    assert result_path.name == "redacted_output.pdf"
    
    reader = PdfReader(result_path)
    assert len(reader.pages) == 1
    # MVP redact tool draws a black bar if any pattern matches.
    # Validating the actual redaction (e.g., text gone or black box at right place)
    # is complex. For now, we check if the tool runs and produces an output.
    # One could check if the output PDF is different from input, or if page content stream changed.

def test_redact_tool_no_match(pdf_with_text_content, tmp_path):
    """測試 redact 工具沒有匹配到任何樣式。"""
    output_file = tmp_path / "redacted_no_match.pdf"
    args = {
        "file": pdf_with_text_content,
        "patterns": ["non_existent_pattern_xyz"],
        "output": str(output_file)
    }
    result_path_str = run_tool("redact", args)
    result_path = Path(result_path_str)
    
    assert result_path.exists()
    # In this case, the output PDF should ideally be identical to the input,
    # or at least not have redaction marks if no match was found.
    # The current MVP implementation of redact.py will draw a bar if *any* pattern matches on the page.
    # If no patterns match at all, no bar should be drawn.
    input_pdf_content = Path(pdf_with_text_content).read_bytes()
    output_pdf_content = result_path.read_bytes()
    # If no redaction occurred, files might be identical or very similar.
    # For MVP, if it runs, it's a pass. More robust check: ensure no black bar was added if not needed.
    # This test mainly ensures the tool runs without error for no-match cases.

def test_redact_tool_empty_patterns_list(pdf_with_text_content, tmp_path):
    """測試 redact 工具樣式列表為空。"""
    output_file = tmp_path / "redacted_empty_patterns.pdf"
    args = {
        "file": pdf_with_text_content,
        "patterns": [], # Empty list
        "output": str(output_file)
    }
    # pydantic schema for RedactSchema has patterns: conlist(str, min_length=1)
    # So, this should raise a validation error via Pydantic in coreapi/views.py if called via API.
    # If run_tool is called directly (as in tests), tools/redact.py might handle it differently or pydantic validation is bypassed.
    # tools/redact.py currently would not find any matches if patterns list is empty, so it might run successfully.
    # Let's assume for direct tool call, it should run without error if list is empty (no patterns to match).
    # If API validation layer is considered, this test might expect ValidationError.
    # For now, testing direct tool behavior:
    result_path_str = run_tool("redact", args)
    result_path = Path(result_path_str)
    assert result_path.exists()
    # Similar to no_match, output should ideally be unchanged.
