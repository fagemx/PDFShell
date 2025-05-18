![Banner](https://resv2.craft.do/user/full/b576b3bb-0dc4-6e02-a1c4-3fa5fb9e3938/doc/9b634094-24ea-4856-85a5-ca13a011dd1a/d326bcf4-89da-4ad4-b3cd-f2e643615180)

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
# 合併 PDF
merge --files sample1.pdf sample2.pdf --output merged.pdf

# 分割指定頁數，並指定輸出資料夾
split --file merged.pdf --pages "1,3" --output_dir out/

# 分割（未指定輸出資料夾時，預設輸出至 output/）
split --file merged.pdf --pages "1,3"

# 加印章（印在第1頁左上）
add_stamp --file sample1.pdf --stamp_path logo.png --page 1

# 查詢操作紀錄
history --limit 5

# 離開
exit
```

📘 **查看完整指令說明：[命令範例](https://github.com/fagemx/PDFShell/blob/main/COMMAND_REFERENCE.md)** 📎 附註：未指定輸出時，預設輸出至 `output/` 資料夾。

___

### 💬 模式二：Web 對話式操作（LLM 自然語言）

啟動後端與前端：

```shell
docker compose up --build -d
```

開啟瀏覽器：

-   Django + 前端整合： [http://localhost:8000](http://localhost:8000/)
-   Nuxt 開發伺服器： [http://localhost:3000](http://localhost:3000/) （需另啟）
  
[[![Watch the demo](https://resv2.craft.do/user/full/b576b3bb-0dc4-6e02-a1c4-3fa5fb9e3938/doc/9b634094-24ea-4856-85a5-ca13a011dd1a/498c3f28-e36d-4e2f-b7fd-70d9c2e58aac)](https://resv2.craft.do/user/full/b576b3bb-0dc4-6e02-a1c4-3fa5fb9e3938/doc/9b634094-24ea-4856-85a5-ca13a011dd1a/498c3f28-e36d-4e2f-b7fd-70d9c2e58aac)

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

___

## 🧩 支援功能

|    功能     |        說明         |
|-----------|-------------------|
|   `merge`   |    合併多個 PDF 檔案    |
|   `split`   |     擷取或分割指定頁數     |
| `add_stamp` |   在 PDF 上加上圖片章    |
|  `redact`   |   遮蔽敏感關鍵字（黑框遮罩）   |
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

```shell
cd pdfshell-ui
pnpm install
pnpm dev
```

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

-   插件市場（YAML + Python 工具擴展）
-   OCR 與圖像轉 PDF 支援
-   文件理解 + 查詢（RAG 模型）
-   SaaS 版權限管理與日誌審計

___

## 📬 聯繫作者

歡迎 PR、開 issue，或來信討論 AI 自動化與產品設計。 **讓人人都能用自然語言，操作複雜 PDF 任務。**
