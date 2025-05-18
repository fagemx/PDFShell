# -*- coding: utf-8 -*-
# PDFShell 趣味範本（兩種樣式，各三頁）Python 單檔版
# 需已安裝 reportlab，Windows 系統有 C:/Windows/Fonts/msjh.ttc

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import Color, HexColor, black, white
from datetime import datetime
import os, random, string

# 註冊微軟正黑體
pdfmetrics.registerFont(TTFont('MSJH', 'C:/Windows/Fonts/msjh.ttc'))

# ===== 顏色定義 =====
BLUE   = Color(0.25, 0.5, 0.93, 1)
ORANGE = Color(1, 0.6, 0.13, 1)
LIGHT  = Color(0.85, 0.95, 1, 1)
GREY   = Color(0.97, 0.97, 0.97, 1)
GREEN  = Color(0.18, 0.8, 0.55, 1)
ORG2   = Color(1, 0.7, 0.2, 1)
BG     = HexColor("#f5f9fa")
CARD   = HexColor("#ffffff")

# ===== 工具函數 =====
def rand_junk():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def draw_footer(c, width, page, style="fun"):
    c.setFont("MSJH", 10)
    if style == "fun":
        c.setFillColor(BLUE)
        c.drawRightString(width-40, 30, f"第 {page} 頁 / 共 3 頁  |  PDFShell 趣味報告")
        c.setFillColor(ORANGE)
        c.drawString(40, 30, "🦄 Powered by Python x ReportLab")
    else:
        c.setFillColor(GREEN)
        c.drawRightString(width-40, 30, f"Page {page} / 3  |  PDFShell 任務清單")
        c.setFillColor(ORG2)
        c.drawString(40, 30, "💼 Let's get things done!")

# ===== 趣味報告範本 =====
def generate_fun_report(path):
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    sections = [
        ("💡 簡介 Introduction", "這是一份很酷的報告範本！可自訂章節與內容，支持插圖、emoji、亂碼、靈感記錄..."),
        ("🧩 系統架構 Architecture", "左側大藍條與橘色塊分明區分內容區，每頁設計微差異，體現數位時代的多元美學。"),
        ("🎲 附錄 Appendix", "可以寫實驗數據、或是亂碼示意，如："),
    ]
    tips = ["✨ 你可以自訂任何內容", "😎 記得多用 emoji 提升可讀性", "🚀 報告不是只有枯燥數據"]
    for i in range(3):
        # 背景區塊
        c.setFillColor(LIGHT if i != 1 else GREY)
        c.rect(0, 0, width, height, fill=1, stroke=0)
        c.setFillColor(BLUE)
        c.rect(0, height-90, width, 90, fill=1, stroke=0)  # 頁首
        c.setFillColor(ORANGE)
        c.rect(0, 0, 28, height, fill=1, stroke=0)         # 左側欄

        # 標題
        c.setFont("MSJH", 23)
        c.setFillColor(white)
        c.drawString(50, height-60, f"📄 PDFShell 報告樣板 - {sections[i][0]}")

        # 日期 & 亂碼
        c.setFont("MSJH", 12)
        c.setFillColor(BLUE)
        c.drawString(50, height-115, f"產出日期：{datetime.now().strftime('%Y-%m-%d')}")
        c.drawRightString(width-50, height-115, f"亂碼: {rand_junk()}")

        # 內容主區
        c.setFont("MSJH", 15)
        c.setFillColor(black)
        c.drawString(70, height-170, sections[i][1])
        c.setFont("MSJH", 12)
        c.drawString(70, height-200, "範例內容：")
        c.setFont("MSJH", 11)
        for j in range(5):
            c.drawString(90, height-230-j*22, f"・{rand_junk()}　這是一行亂碼行，也可放表格內容")
        # 趣味提示
        c.setFont("MSJH", 10)
        c.setFillColor(ORANGE)
        c.drawString(50, 100, f"💡 小技巧：{tips[i]}")

        # 頁腳
        draw_footer(c, width, i+1, style="fun")
        c.showPage()
    c.save()

# ===== 卡片任務清單範本 =====
def generate_fun_tasks(path):
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    for page in range(1, 4):
        # 大背景
        c.setFillColor(BG)
        c.rect(0, 0, width, height, fill=1, stroke=0)
        # 頁首裝飾
        c.setFillColor(GREEN)
        c.rect(0, height-65, width, 65, fill=1, stroke=0)
        c.setFillColor(ORG2)
        c.rect(0, height-65, 120, 65, fill=1, stroke=0)
        # 標題
        c.setFont("MSJH", 20)
        c.setFillColor(white)
        c.drawString(36, height-44, f"✅ PDFShell 代辦清單 - Page {page}")
        # 日期
        c.setFont("MSJH", 11)
        c.setFillColor(GREEN)
        c.drawRightString(width-40, height-44, f"建立: {datetime.now().strftime('%Y-%m-%d')}")

        # 卡片區塊
        card_y = height-120
        for i in range(6):
            c.setFillColor(CARD)
            c.roundRect(50, card_y-40, width-100, 34, 8, fill=1, stroke=0)
            c.setFillColor(GREEN if i%2==0 else ORG2)
            c.setFont("MSJH", 15)
            c.drawString(70, card_y-25, f"☐ 工作項目 #{i+1} — {rand_junk()}")
            c.setFont("MSJH", 11)
            c.setFillColor(black)
            c.drawString(270, card_y-25, f"狀態: {'✔️ 完成' if i%3==0 else '🕒 進行中'}")
            card_y -= 48
        # 趣味提示
        c.setFont("MSJH", 10)
        c.setFillColor(ORG2)
        c.drawString(60, 80, "小提醒：用清單推動生產力！")
        # 頁腳
        draw_footer(c, width, page, style="tasks")
        c.showPage()
    c.save()

# ===== 主程式產生PDF =====
if __name__ == "__main__":
    os.makedirs("output_pdfs", exist_ok=True)
    generate_fun_report("output_pdfs/fun_template_report.pdf")
    generate_fun_tasks("output_pdfs/fun_template_tasks.pdf")
    print("✅ 已生成全新設計兩份 PDF 樣板！各三頁，位於 output_pdfs/ 目錄。")
