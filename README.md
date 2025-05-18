![d326bcf4-89da-4ad4-b3cd-f2e643615180](https://github.com/user-attachments/assets/07b50125-b1ea-4bd7-b5dc-37ec22e9ec5d)

## 📄 PDFShell - 對話式 PDF 自動化平台

用自然語言聊天，就能處理 PDF！ PDFShell 是一款結合 LLM 的 PDF 工具，支援互動式 Shell 與 Web UI 操作，讓你以人類語言快速完成合併、分割、加章等任務。

___

## 🚀 快速使用指南

### 🖥️ 模式一：互動式 Shell 操作

啟動方式：

```shell
poetry run python -m pdfshell.shell.app
```

進入後可輸入以下常用指令（像操作 Linux 一樣）：

```shell
# 合併 PDF (若要合併多個檔案，需重複 --files 選項)
merge --files sample1.pdf --files sample2.pdf --output merged.pdf

# 分割指定頁數，並指定輸出資料夾
split --file merged.pdf --pages "1,3" --output_dir out/

# 分割（未指定輸出資料夾時，預設輸出至 output/）
split --file merged.pdf --pages "1,3"

# 加印章（印在第1頁左上）
add_stamp --file sample1.pdf --stamp_path logo.png --page 1

# 遮蔽內容，例如遮住文字"Henry"
redact --file sample1.pdf --patterns "Henry"

# 查詢操作紀錄
history --limit 5

# 離開
exit
```

📘 **查看完整指令說明：[命令範例](https://github.com/fagemx/PDFShell/blob/main/COMMAND_REFERENCE.md)** 
- 📎 附註：未指定輸出時，預設輸出至 `output/` 資料夾。

___

### 💬 模式二：Web 對話式操作（LLM 自然語言）

啟動後端與前端：

```shell
#第一次運行，建立鏡像
docker compose up --build -d
#後台運行
docker compose up -d
# 啟動 Nuxt 開發伺服器，預設 http://localhost:3000
pnpm dev          
```

開啟瀏覽器：

-   Django + 前端整合： [http://localhost:8000](http://localhost:8000/)
-   Nuxt 開發伺服器： [http://localhost:3000](http://localhost:3000/) （需另啟）
  


https://github.com/user-attachments/assets/a4cce640-be39-4a37-b40c-4608b5e874c9



#### 🧪 操作範例對話：

```cpp
你：嗨，你好！
AI：你好！今天想幫你處理哪一份 PDF 呢？

你：請幫我合併 sample1.pdf 和 sample2.pdf，命名為 final.pdf。
AI：已合併完成，輸出檔案為 final.pdf。

你：幫我從 final.pdf 擷取第 2 到 5 頁。
AI：已擷取完成，新檔案為 final_pages_2_to_5.pdf。

你：謝啦！
AI：不客氣！有需要再找我幫忙喔。
```
- 📎 附註：本系統依賴 OpenAI 進行文件內容解析與對話生成，未提供此金鑰將導致 AI 功能無法啟用。

___

## 🧩 支援功能

|    功能     |        說明         |
|-----------|-------------------|
|   `merge`   |    合併多個 PDF 檔案    |
|   `split`   |     擷取或分割指定頁數     |
| `add_stamp` |   在 PDF 上加上圖片章    |
|  `redact`   |   遮蔽敏感關鍵字（字元替代）   |
|  `history`  |      查詢操作紀錄       |
|    `nl`     | 用自然語言指令操作（LLM 模式） |

___

## 🧪 本地開發模式（Poetry）

```shell
git clone https://github.com/fagemx/PDFShell.git
cd PDFShell
cp .env.sample .env
poetry install
```

啟動互動式 Shell：

```shell
poetry run python -m pdfshell.shell.app
```

___

## 🌐 前端啟動（Nuxt + pnpm）

前端使用 [Nuxt 3](https://nuxt.com) 框架搭配 `pnpm` 作為套件管理工具。請先安裝 [pnpm](https://pnpm.io/installation)，再依以下步驟啟動前端開發伺服器：

```bash
cd pdfshell-ui
pnpm install      # 安裝前端依賴
pnpm dev          # 啟動 Nuxt 開發伺服器，預設 http://localhost:3000
```

* 📎 如果你尚未安裝 `pnpm`，可使用下列指令：

```bash
npm install -g pnpm
```

* 前端提供與 LLM 對話式的 UI 操作介面，需搭配後端 API 一起啟動才能完整體驗。

___

## 🐳 Docker 一鍵啟動（推薦）

```shell
docker compose up --build -d
docker compose exec web python manage.py migrate
```

測試 API：

```shell
curl -X POST -H "Content-Type: application/json" \
  -d '{"files": ["a.pdf", "b.pdf"], "output": "merged.pdf"}' \
  http://localhost:8000/api/v1/merge/
```

___

## 📁 專案結構

```bash
PDFShell/
├── cli/                # CLI 工具
├── pdfshell.shell/     # Shell 模組
├── pdfshell-ui/        # Nuxt 前端
├── core/               # 核心處理邏輯
├── agent/              # 自然語言 LLM 模組
├── tools/              # 各種工具實作
├── trace/              # 操作歷史紀錄
└── docker-compose.yml  # Docker 配置
```

___

## 🗺️ 後續規劃
-   語音操作
-   插件市場（YAML + Python 工具擴展）
-   OCR 與圖像轉 PDF 支援
-   文件理解 + 查詢（RAG 模型）
-   SaaS 版權限管理與日誌審計

___

##  **讓人人都能用自然語言，操作複雜 PDF 任務。**



