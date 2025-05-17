import pytest
import json
from pathlib import Path
from django.urls import reverse
from django.test import Client # Django測試客戶端
from pypdf import PdfWriter # 用於建立測試PDF

# pytest標記，表示這些測試需要資料庫設定(即使我們目前API不直接寫DB，但好習慣)
pytestmark = pytest.mark.django_db

@pytest.fixture
def client():
    """提供一個Django測試客戶端實例。"""
    return Client()

@pytest.fixture
def sample_pdf_for_api(tmp_path_factory):
    """為API測試建立一個臨時的單頁PDF檔案，並回傳其路徑。"""
    # 使用 tmp_path_factory 來確保檔案在測試結束後被清理
    # Django測試中的臨時檔案不應依賴於settings.MEDIA_ROOT
    # https://docs.pytest.org/en/6.2.x/tmpdir.html#the-tmp-path-factory-fixture
    pdf_dir = tmp_path_factory.mktemp("api_pdfs")
    pdf_path = pdf_dir / "api_sample.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with open(pdf_path, "wb") as f:
        writer.write(f)
    return str(pdf_path)

@pytest.fixture
def two_sample_pdfs_for_api(tmp_path_factory):
    """為API測試建立兩個臨時的單頁PDF檔案，並回傳其路徑列表。"""
    pdf_dir = tmp_path_factory.mktemp("api_more_pdfs")
    pdf1_path = pdf_dir / "api_a.pdf"
    pdf2_path = pdf_dir / "api_b.pdf"
    
    writer1 = PdfWriter()
    writer1.add_blank_page(width=210, height=297) # A4 size
    with open(pdf1_path, "wb") as f1:
        writer1.write(f1)
        
    writer2 = PdfWriter()
    writer2.add_blank_page(width=210, height=297)
    with open(pdf2_path, "wb") as f2:
        writer2.write(f2)
            
    return [str(pdf1_path), str(pdf2_path)]

def test_merge_api_success(client, two_sample_pdfs_for_api, tmp_path):
    """測試 /api/v1/merge/ 端點成功合併。"""
    url = reverse("tool_view", kwargs={"tool": "merge"})
    # 確保輸出檔案名在tmp_path下，避免汙染專案目錄
    output_filename = tmp_path / "api_merged_output.pdf" 
    
    payload = {
        "files": two_sample_pdfs_for_api,
        "output": str(output_filename) 
    }
    
    response = client.post(url, data=json.dumps(payload), content_type="application/json")
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "ok"
    assert Path(response_data["output"]).exists()
    assert Path(response_data["output"]).name == "api_merged_output.pdf"

def test_merge_api_missing_params(client):
    """測試 /api/v1/merge/ 端點缺少必要參數時的錯誤處理。"""
    url = reverse("tool_view", kwargs={"tool": "merge"})
    
    # 缺少 files
    payload_no_files = {"output": "test.pdf"}
    response_no_files = client.post(url, data=json.dumps(payload_no_files), content_type="application/json")
    assert response_no_files.status_code == 400 # Bad Request
    # Pydantic v2 的錯誤回傳格式可能不同，這裡假設 detail 是一個 list of errors
    # 或是檢查 response_no_files.json()["detail"] 是否包含關於 'files' 欄位缺失的訊息
    # 例如： assert any("files" in err.get("loc", []) for err in response_no_files.json().get("detail", []))
    error_detail_no_files = response_no_files.json().get("detail", [])
    assert isinstance(error_detail_no_files, list)
    assert len(error_detail_no_files) > 0
    assert "files" in error_detail_no_files[0].get("loc", [])

    # 缺少 output
    payload_no_output = {"files": ["a.pdf", "b.pdf"]}
    response_no_output = client.post(url, data=json.dumps(payload_no_output), content_type="application/json")
    assert response_no_output.status_code == 400
    error_detail_no_output = response_no_output.json().get("detail", [])
    assert isinstance(error_detail_no_output, list)
    assert len(error_detail_no_output) > 0
    assert "output" in error_detail_no_output[0].get("loc", [])

def test_split_api_success(client, sample_pdf_for_api, tmp_path):
    """測試 /api/v1/split/ 端點成功分割。"""
    url = reverse("tool_view", kwargs={"tool": "split"})
    output_dir = tmp_path / "api_split_output" # 確保輸出目錄在tmp_path下
    # output_dir 不需要預先建立，工具本身會建立
    
    payload = {
        "file": sample_pdf_for_api,
        "pages": "1", # 分割出第一頁
        "output_dir": str(output_dir)  
    }
    
    response = client.post(url, data=json.dumps(payload), content_type="application/json")
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "ok"
    
    output_file_path = Path(response_data["output"])
    assert output_file_path.exists()
    assert output_file_path.name == "api_sample_split.pdf" # 根據 split.py 的命名邏輯
    assert output_file_path.parent.name == "api_split_output"

def test_api_invalid_tool(client):
    """測試 API 請求一個不存在的工具。"""
    url = reverse("tool_view", kwargs={"tool": "non_existent_tool"})
    payload = {}
    response = client.post(url, data=json.dumps(payload), content_type="application/json")
    assert response.status_code == 404 # Not Found (因為工具不存在於SCHEMAS)

def test_api_wrong_method(client):
    """測試 API 使用不正確的 HTTP 方法請求端點。"""
    url = reverse("tool_view", kwargs={"tool": "merge"})
    response = client.get(url) # 使用 GET 而非 POST
    # 預期405 Method Not Allowed
    assert response.status_code == 405 # 更新預期的狀態碼
