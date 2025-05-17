import os
import requests
import json # requests 通常會自動處理 JSON，但如果手動構造 body 則可能需要
import logging

# 初始化日誌記錄器
logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK")

def notify_slack(message: str):
    """
    Sends a notification message to a Slack channel via a webhook.

    Args:
        message: The message string to send to Slack.
    """
    if SLACK_WEBHOOK_URL:
        payload = {"text": message}
        try:
            response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5) # 設置超時以避免長時間阻塞
            response.raise_for_status() # 如果 HTTP 請求返回不成功的狀態碼，則拋出 HTTPError
            logger.info("Slack 通知已成功發送。")
        except requests.exceptions.RequestException as e:
            logger.error(f"發送 Slack 通知失敗: {e}")
        except Exception as e: # 捕獲其他潛在錯誤
            logger.error(f"發送 Slack 通知時發生未預期錯誤: {e}")
    else:
        logger.warning("SLACK_WEBHOOK 環境變數未設定，無法發送 Slack 通知。錯誤訊息: %s", message)

# 測試範例 (可選)
if __name__ == '__main__':
    # 測試前請設定 SLACK_WEBHOOK 環境變數
    # 例如: export SLACK_WEBHOOK="your_webhook_url_here"
    if SLACK_WEBHOOK_URL:
        print(f"正在測試 Slack 通知，將發送到: {SLACK_WEBHOOK_URL[:30]}...")
        notify_slack("這是一條來自 PDFShell core.alert 的測試訊息！")
        notify_slack("另一條測試訊息，包含一些 **Markdown** `code` 格式。")
    else:
        print("SLACK_WEBHOOK 環境變數未設定，無法執行 Slack 通知測試。")
        # 模擬日誌輸出
        notify_slack("這是一條在 SLACK_WEBHOOK 未設定時的測試訊息。")
