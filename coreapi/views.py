from django.shortcuts import render
import json
from django.http import JsonResponse, HttpResponseBadRequest, Http404, HttpResponseServerError, FileResponse
from django.views.decorators.csrf import csrf_exempt # 允許 POST 請求 без CSRF token (用於 API)
from pydantic import ValidationError
import logging # 建議加入日誌
import os # Added for file operations
from pathlib import Path # Added Path
import uuid # For generating unique session filenames

from core.engine import run_tool
from .serializers import SCHEMAS
from agent.agent import nl_execute # 新增: 導入 nl_execute
from core.alert import notify_slack # 修改: 取消註釋並導入 notify_slack
from django.conf import settings # Import settings for PDF_UPLOADS_ROOT

logger = logging.getLogger(__name__) # 建議加入日誌

# Create your views here.

@csrf_exempt # 確保 API 端點可以接收 POST 請求
def tool_view(request, tool: str):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "只允許 POST 請求。"}, status=405) # 405 Method Not Allowed

    session_id = request.headers.get("X-Session-ID") # Or however session_id is passed

    if tool not in SCHEMAS:
        # raise Http404(f"不支援的工具：{tool}") # Http404 通常會渲染 HTML 錯誤頁面
        return JsonResponse({"status": "error", "message": f"不支援的工具：{tool}"}, status=404)

    try:
        # 嘗試從 request.body 解析 JSON 數據
        if request.body:
            data = json.loads(request.body)
        else:
            data = {} # 如果請求 body 為空，則使用空字典
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "無效的 JSON 格式。"}, status=400)

    try:
        # 使用對應的 Pydantic 模型驗證數據
        validated_data = SCHEMAS[tool](**data).model_dump() # 使用 model_dump() 獲取 dict
    except ValidationError as e:
        return JsonResponse({"status": "error", "message": "參數驗證失敗", "detail": e.errors()}, status=400)
    except Exception as e: # 其他潛在的 data 轉換錯誤
        return JsonResponse({"status": "error", "message": f"處理請求參數時發生預期外的錯誤：{str(e)}"}, status=400)

    try:
        # 調用核心引擎執行工具
        output_result = run_tool(tool, validated_data, session_id=session_id)
        return JsonResponse({"status": "ok", "output": output_result})
    except FileNotFoundError as e:
        return JsonResponse({"status": "error", "message": f"執行工具時檔案未找到：{str(e)}"}, status=400)
    except ValueError as e: # 例如 secure.py 中的驗證錯誤
        return JsonResponse({"status": "error", "message": f"執行工具時參數錯誤：{str(e)}"}, status=400)
    except Exception as e:
        # 考慮在這裡加入更詳細的日誌記錄 (logging)
        logger.error(f"執行工具 {tool} 失敗 (Session: {session_id})：{e}", exc_info=True)
        return JsonResponse({"status": "error", "message": f"執行工具 {tool} 時發生內部錯誤：{str(e)}"}, status=500)

@csrf_exempt
def nl_view(request):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "只允許 POST 請求。"}, status=405)

    # 1. Session Management
    if not request.session.session_key:
        request.session.create()
    session_id = request.session.session_key
    
    session_upload_dir = settings.PDF_UPLOADS_ROOT / session_id
    session_upload_dir.mkdir(parents=True, exist_ok=True)

    user_nl_text = ""
    available_files_for_llm = [] # List of dicts: {'user_label': 'original_name.pdf', 'session_filename': 'uuid_name.pdf'}
    
    # --- BEGIN MODIFICATION: Add default shared files ---
    if hasattr(settings, 'DEFAULT_SHARED_FILES') and isinstance(settings.DEFAULT_SHARED_FILES, list):
        for shared_filename in settings.DEFAULT_SHARED_FILES:
            # Check if the shared file actually exists in PDF_FILES_ROOT
            if (settings.PDF_FILES_ROOT / shared_filename).exists():
                available_files_for_llm.append({
                    'user_label': shared_filename, # User sees and refers to this name
                    'session_filename': shared_filename, # Agent uses this; engine will check PDF_FILES_ROOT
                    'isPublic': True # Mark default shared files as public
                })
            else:
                logger.warning(f"NL_VIEW (Session: {session_id}): Default shared file '{shared_filename}' not found in PDF_FILES_ROOT.")
    # --- END MODIFICATION ---
    
    # For JSON requests, this list might be passed directly, or constructed from session filenames
    history_for_llm = []

    try:
        if request.content_type.startswith('multipart/form-data'):
            logger.info(f"NL_VIEW (Session: {session_id}): Received multipart/form-data request")
            user_nl_text = request.POST.get('text', '')
            
            # Process history if provided
            history_str = request.POST.get('history', '[]')
            try:
                history_for_llm = json.loads(history_str)
                if not isinstance(history_for_llm, list): history_for_llm = []
            except json.JSONDecodeError:
                logger.warning(f"NL_VIEW (Session: {session_id}): Invalid history JSON: {history_str}")
                history_for_llm = []

            # Handle file uploads (e.g., up to 2 files as per old logic)
            # Max files can be made configurable or more dynamic
            for i in range(1, 3): # Assuming 'file1', 'file2'
                file_key = f'file{i}'
                uploaded_file = request.FILES.get(file_key)
                if uploaded_file:
                    original_filename = uploaded_file.name
                    # Sanitize original_filename before using it in Path
                    safe_original_stem = Path(original_filename).stem.replace(" ", "_").replace("/", "_").replace("\\\\", "_")
                    safe_original_suffix = Path(original_filename).suffix
                    
                    # Generate a unique filename for storage within the session directory
                    session_filename = f"{uuid.uuid4().hex}{safe_original_suffix}"
                    session_file_path = session_upload_dir / session_filename
                    
                    # --- BEGIN MODIFICATION: Ensure user uploaded files don't overwrite default shared files in the list by user_label ---
                    # Check if a default file with the same user_label already exists; if so, maybe warn or make user_label unique.
                    # For now, we'll allow it, but the LLM might get confused if user_labels are not unique.
                    # A more robust solution would be to ensure user_labels are unique, e.g., by appending (uploaded) if a conflict exists.
                    # However, the current available_files structure relies on session_filename for uniqueness for the agent.
                    
                    # Let's check if this original_filename (user_label) already exists from default files
                    # If so, perhaps we modify the user_label for the uploaded file for clarity to the LLM/user
                    # This is an advanced handling. For now, we just append.
                    # The primary key for the agent is 'session_filename'.
                    # --- END MODIFICATION ---

                    with open(session_file_path, 'wb+') as destination:
                        for chunk in uploaded_file.chunks():
                            destination.write(chunk)
                    
                    available_files_for_llm.append({
                        'user_label': original_filename, # For LLM to refer to, and for user display
                        'session_filename': session_filename, # For agent to use in tool calls
                        'isPublic': False # Files from user uploads are not public
                    })
                    logger.info(f"NL_VIEW (Session: {session_id}): Saved '{original_filename}' as '{session_filename}' in session directory.")

        elif request.content_type.startswith('application/json'):
            logger.info(f"NL_VIEW (Session: {session_id}): Received application/json request")
            if not request.body:
                return JsonResponse({"status": "error", "message": "JSON 請求內容不可為空。"}, status=400)
            
            data = json.loads(request.body)
            user_nl_text = data.get('text', '')
            history_for_llm = data.get('history', [])
            if not isinstance(history_for_llm, list): history_for_llm = []
            
            # If JSON request passes 'session_files', use them to reconstruct available_files_for_llm
            # This assumes client tracks uploaded files and sends their 'session_filename' and 'user_label'
            client_provided_files = data.get('session_files', []) 
            if isinstance(client_provided_files, list):
                for f_info in client_provided_files:
                    if isinstance(f_info, dict) and 'user_label' in f_info and 'session_filename' in f_info:
                        # Basic validation: check if session_filename actually exists in session_upload_dir
                        # (This part is for files uploaded by the user in the current session, which should be in session_upload_dir)
                        if (session_upload_dir / f_info['session_filename']).exists():
                             # --- BEGIN MODIFICATION: Prevent adding if it's a default file already added ---
                            is_default_file = False
                            if hasattr(settings, 'DEFAULT_SHARED_FILES') and f_info['session_filename'] in settings.DEFAULT_SHARED_FILES:
                                # Check if this 'session_filename' (which is the simple name for default files)
                                # matches one of the default shared files that would have been added earlier.
                                # This scenario (client sending a default file as a 'session_file') should ideally not happen
                                # if the client correctly distinguishes between new uploads and existing session files.
                                # However, if it does, we want to avoid duplicates in available_files_for_llm
                                # based on the 'session_filename' being the same as a default file's simple name.
                                for entry in available_files_for_llm:
                                    if entry['session_filename'] == f_info['session_filename'] and \
                                       entry['user_label'] == f_info['user_label']: # further ensure it's the same entry
                                        is_default_file = True
                                        break
                            if not is_default_file:
                                available_files_for_llm.append({
                                    'user_label': f_info['user_label'],
                                    'session_filename': f_info['session_filename'],
                                    'isPublic': False # Files from client's session_files list are session files, not public
                                })
                            # --- END MODIFICATION ---
                        else:
                            # If it's not in session_upload_dir, it might be a misreported default file.
                            # We already added default files. If it's a default file name, it should be found by engine.
                            # We log a warning if a client-provided session_filename for an uploaded file is not found.
                            if not (hasattr(settings, 'DEFAULT_SHARED_FILES') and f_info['session_filename'] in settings.DEFAULT_SHARED_FILES):
                                logger.warning(f"NL_VIEW (Session: {session_id}): Client provided session_filename '{f_info['session_filename']}' (user_label: '{f_info['user_label']}') for an uploaded file not found in session directory.")
            
            if not user_nl_text and not available_files_for_llm: # Check after adding default files too
                 return JsonResponse({"status": "error", "message": "請求 JSON 必須包含 'text' 或有效的 'session_files'。"}, status=400)
        else:
            return JsonResponse({"status": "error", "message": f"不支援的 Content-Type: {request.content_type}"}, status=415)

        # Prepare payload for nl_execute
        nl_execute_payload = {
            'text': user_nl_text,
            'session_id': session_id, # Pass session_id
            'available_files': available_files_for_llm, # Pass the list of available files
            'history': history_for_llm # Pass history
        }
        
        logger.info(f"NL_VIEW (Session: {session_id}): Calling nl_execute with payload: {nl_execute_payload}")
        final_agent_state = nl_execute(nl_execute_payload) 

        if final_agent_state.get("error"):
            error_output = final_agent_state.get("output", f"An error occurred: {final_agent_state['error']}")
            logger.error(f"NL_VIEW (Session: {session_id}): Agent execution failed: {final_agent_state['error']}, Output: {error_output}")
            return JsonResponse({
                "status": "error",
                "message": str(error_output),
                "tool_name": final_agent_state.get("tool_name"),
            }, status=400)

        # If output is a path, it should be a session_filename. Convert to downloadable link if needed.
        output_data = final_agent_state.get("output", "")
        # Initialize processed_session_files_for_response with the files that were available *before* the tool ran
        processed_session_files_for_response = list(available_files_for_llm) # Make a copy

        if isinstance(output_data, str) and output_data: # If there is a string output
            # Check if this output_data is a new file created in the session directory
            potential_new_session_file_path = session_upload_dir / output_data
            if potential_new_session_file_path.exists() and potential_new_session_file_path.is_file():
                # It's a new file in the session. Add it to the list for the response.
                # Ensure it's not already in the list (e.g., if tool overwrote an existing input file and returned its name)
                is_already_listed = any(
                    f['session_filename'] == output_data for f in processed_session_files_for_response
                )
                if not is_already_listed:
                    processed_session_files_for_response.append({
                        'user_label': output_data, # For new files, user_label and session_filename can be the same
                        'session_filename': output_data,
                        'isPublic': False  # Explicitly mark new session files as not public
                    })
                    logger.info(f"NL_VIEW (Session: {session_id}): Added new output file '{output_data}' to processed_session_files for response.")

        response_data = {
            "status": "ok",
            "data": output_data, # This is the direct output of the tool
            "tool_name": final_agent_state.get("tool_name"),
            "log": final_agent_state.get("log_entries", []),
            "session_id": session_id, # Added session_id to the response
            "processed_session_files": processed_session_files_for_response # Use the updated list
        }
        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "無效的 JSON 格式。"}, status=400)
    except Exception as e:
        error_message = f"處理自然語言請求時發生嚴重錯誤 (Session: {session_id}): {str(e)}"
        logger.error(error_message, exc_info=True)
        notify_slack(f"❌ PDFShell NL Flow 失敗 (Session: {session_id}): {error_message}")
        return JsonResponse({"status":"error","message":f"處理請求時發生內部錯誤: {str(e)}"}, status=500)
    # No finally block to clean temp files, as we are now using session-specific persistent storage for uploads.
    # Cleanup of these session directories will be handled by a separate mechanism (Phase 6).

@csrf_exempt # Or handle CSRF appropriately if this is part of a web form
def download_file_view(request, session_id: str, session_filename: str):
    if request.method != 'GET':
        return JsonResponse({"status": "error", "message": "只允許 GET 請求。"}, status=405)

    # Validate session_id and session_filename to prevent path traversal
    # A simple check: ensure session_id and session_filename do not contain '..' or '/' or '\'
    if ".." in session_id or "/" in session_id or "\\\\" in session_id or \
       ".." in session_filename or "/" in session_filename or "\\\\" in session_filename:
        logger.warning(f"DOWNLOAD_VIEW: Invalid session_id or session_filename detected. Session: {session_id}, Filename: {session_filename}")
        return HttpResponseBadRequest("無效的檔案請求參數。")

    file_path = settings.PDF_UPLOADS_ROOT / session_id / session_filename
    
    logger.info(f"DOWNLOAD_VIEW: Attempting to download {file_path} for session {session_id}")

    if not file_path.exists() or not file_path.is_file():
        logger.warning(f"DOWNLOAD_VIEW: File not found or is not a file: {file_path}")
        raise Http404("找不到指定的檔案。")
    
    # Optional: Add more security checks here, e.g., checking if the current user
    # (if authentication is implemented) owns this session_id.

    try:
        # Re-validate using secure.validate to be absolutely sure,
        # expected_root should be the specific session's upload directory
        # from core.secure import validate as secure_validate_path # Avoid circular import if secure calls views
        # secure_validate_path(str(file_path), expected_root=(settings.PDF_UPLOADS_ROOT / session_id), session_id=session_id)
        # For now, the path construction and initial check is deemed sufficient for this PoC stage.
        # A full call to secure.validate might be good for production hardening.

        response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=session_filename)
        response['X-Frame-Options'] = 'SAMEORIGIN' # Allow embedding in same origin iframes
        response['Content-Disposition'] = f'inline; filename="{session_filename}"' # Suggest inline display
        return response
    except ValueError as e: # From potential secure_validate_path
        logger.error(f"DOWNLOAD_VIEW: Validation error for {file_path}: {e}")
        raise Http404("檔案驗證失敗。")
    except Exception as e:
        logger.error(f"DOWNLOAD_VIEW: Error serving file {file_path}: {e}", exc_info=True)
        return HttpResponseServerError("下載檔案時發生錯誤。")

# Make sure to add this new view to your urls.py
# Example for pdfshell_srv/urls.py:
# from coreapi import views as coreapi_views
# path('api/v1/download/<str:session_id>/<str:session_filename>/', coreapi_views.download_file_view, name='download_file'),

def public_files_view(request):
    if request.method != 'GET':
        return JsonResponse({"status": "error", "message": "只允許 GET 請求。"}, status=405)

    public_files_list = []
    
    # 使用 settings.PDF_FILES_ROOT 作為公開檔案的來源目錄
    # 這個設定需要在您的 Django settings.py 中定義，例如：
    # PDF_FILES_ROOT = BASE_DIR / 'PDFShell' / 'files' # 或您的實際路徑
    
    if not hasattr(settings, 'PDF_FILES_ROOT'):
        logger.error("public_files_view: settings.PDF_FILES_ROOT 未設定。")
        return JsonResponse({"status": "error", "message": "伺服器未設定公開檔案目錄。"}, status=500)

    pdf_files_root_path = Path(settings.PDF_FILES_ROOT)

    if not pdf_files_root_path.exists() or not pdf_files_root_path.is_dir():
        logger.error(f"public_files_view: PDF_FILES_ROOT '{pdf_files_root_path}' 不存在或不是一個目錄。")
        return JsonResponse({"status": "error", "message": "配置的公開檔案目錄無效。"}, status=500)

    try:
        for filename in os.listdir(pdf_files_root_path):
            file_path = pdf_files_root_path / filename
            if file_path.is_file(): # 只列出檔案，不列出子目錄
                # 您可以在這裡加入檔案類型過濾，例如只顯示 PDF
                # if filename.lower().endswith('.pdf'):
                public_files_list.append({
                    'user_label': filename,
                    'session_filename': filename, # 對於這些公開檔案，兩者可以相同
                })
        
        return JsonResponse({'public_files': public_files_list})
        
    except Exception as e:
        logger.error(f"public_files_view: 讀取公開檔案時發生錯誤於 '{pdf_files_root_path}': {e}", exc_info=True)
        return JsonResponse({"status": "error", "message": "讀取公開檔案列表時發生內部錯誤。"}, status=500)

@csrf_exempt # Or handle CSRF appropriately if this is part of a web form
def download_public_file_view(request, filename: str):
    if request.method != 'GET':
        return JsonResponse({"status": "error", "message": "只允許 GET 請求。"}, status=405)

    # Validate filename to prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        logger.warning(f"DOWNLOAD_PUBLIC_FILE_VIEW: Invalid filename detected: {filename}")
        return HttpResponseBadRequest("無效的檔案名稱參數。")

    if not hasattr(settings, 'PDF_FILES_ROOT'):
        logger.error("download_public_file_view: settings.PDF_FILES_ROOT 未設定。")
        return JsonResponse({"status": "error", "message": "伺服器未設定公開檔案目錄。"}, status=500)

    file_path = Path(settings.PDF_FILES_ROOT) / filename
    
    logger.info(f"DOWNLOAD_PUBLIC_FILE_VIEW: Attempting to download {file_path}")

    if not file_path.exists() or not file_path.is_file():
        logger.warning(f"DOWNLOAD_PUBLIC_FILE_VIEW: File not found or is not a file: {file_path}")
        raise Http404("找不到指定的檔案。")
    
    try:
        response = FileResponse(open(file_path, 'rb'), as_attachment=False, filename=filename) # as_attachment=False for inline preview
        response['X-Frame-Options'] = 'SAMEORIGIN' # Allow embedding in same origin iframes
        response['Content-Disposition'] = f'inline; filename="{filename}"' # Suggest inline display for public files too
        return response
    except Exception as e:
        logger.error(f"DOWNLOAD_PUBLIC_FILE_VIEW: Error serving file {file_path}: {e}", exc_info=True)
        return HttpResponseServerError("下載檔案時發生錯誤。")
