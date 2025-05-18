# PDFShell 指令參考

本文檔提供了 PDFShell 中可用的核心指令的詳細參考。

## 通用概念

-   **檔案路徑**：除非特別說明，所有 `--file`、`--output`、`--stamp-path` 等接受檔案或目錄路徑的參數，都期望是相對於 PDFShell 專案根目錄下 `files/` 資料夾的路徑。如果指令產生輸出檔案但未指定明確的輸出路徑，則輸出通常會儲存在專案根目錄下的 `output/` 資料夾中，並帶有根據輸入檔案名衍生的檔名。
-   **頁碼**：許多指令接受頁碼或頁碼範圍。頁碼通常是 1-indexed (即文件的第一頁是 1)。特殊值 `-1` 可以用來代表文件的最後一頁。

## 指令列表

### 1. 歷史記錄 (history)

顯示最近在 PDFShell 中執行的操作歷史。

**指令格式：**

```
history [--limit <number>]
```

**參數：**

-   `--limit <number>` (可選):
    -   指定要顯示的最近操作記錄的數量。
    -   如果省略，預設顯示 10 條記錄。
    -   範例：`--limit 5` (顯示最近 5 條)

**使用範例：**

1.  顯示預設數量的歷史記錄 (最近 10 條)：
    ```
history
    ```

2.  顯示最近 3 條操作歷史記錄：
    ```
history --limit 3
    ```

**輸出欄位說明 (每條記錄)：**

-   **時間戳**：操作執行的日期和時間。
-   **工具 (Tool)**：執行的工具名稱 (例如 `merge`, `split`)。
-   **輸入雜湊 (In Hash)**：輸入參數的雜湊值 (截斷顯示)，用於追蹤。
-   **輸出雜湊 (Out Hash)**：輸出結果的雜湊值 (截斷顯示)，用於追蹤。
-   **狀態 (Status)**：操作的執行狀態 (例如 `success`, `error`)。
-   **錯誤訊息 (Error)**：如果狀態是 `error`，則顯示相關的錯誤訊息摘要。

### 2. 合併 (merge)

將多個 PDF 檔案合併成一個單一的 PDF 檔案。

**指令格式：**

```
merge --files <file1.pdf> --files <file2.pdf> [--files <file3.pdf> ...] [--output <output_merged.pdf>]
```

**參數：**

-   `--files <filepath>` (必要, 可多次指定):
    -   要合併的 PDF 檔案路徑。
    -   您必須至少指定兩個 `--files` 參數。
    -   範例：`--files documentA.pdf --files documentB.pdf`
-   `--output <filepath>` (可選):
    -   合併後輸出的 PDF 檔案的路徑和檔名。
    -   如果省略，輸出檔案將儲存在 `output/` 資料夾中，並根據第一個輸入檔名產生 (例如 `input1_merged.pdf`)。
    -   範例：`--output combined_report.pdf`

**使用範例：**

1.  合併 `report_part1.pdf` 和 `report_part2.pdf` 到預設輸出位置：
    ```
    merge --files report_part1.pdf --files report_part2.pdf
    ```
    (假設 `report_part1.pdf` 和 `report_part2.pdf` 位於 `files/` 資料夾中。輸出將類似 `output/report_part1_merged.pdf`)

2.  合併三個檔案並指定輸出檔名和位置：
    ```
    merge --files intro.pdf --files chapter1.pdf --files appendix.pdf --output final_document.pdf
    ```
    (輸出將是 `files/final_document.pdf`，如果 `final_document.pdf` 不包含路徑；或者您可以指定完整路徑，但仍建議在 `files/` 或 `output/` 下操作以保持一致性。引擎通常會將相對路徑解析到 `files/` 或 `output/` 下。)


## 2. 分割 (split)

從一個 PDF 檔案中提取指定的頁面或頁碼範圍，並將它們儲存為一個新的 PDF 檔案。

**指令格式：**

```
split --file <input.pdf> --pages "<page_ranges>" [--output-dir <directory_path>]
```

**參數：**

-   `--file <filepath>` (必要):
    -   要進行分割的來源 PDF 檔案路徑。
    -   範例：`--file annual_report.pdf`
-   `--pages "<page_ranges>"` (必要):
    -   一個描述要提取哪些頁面的字串。頁碼是 1-indexed。
    -   **格式說明：**
        -   單頁：`"1"` (提取第 1 頁)
        -   連續範圍：`"2-5"` (提取第 2、3、4、5 頁)
        -   多個頁面或範圍：`"1,3,7-9"` (提取第 1 頁、第 3 頁、以及第 7 到 9 頁)
        -   排除頁面：在頁碼或範圍前加上 `!`。
            -   `"!3"` (提取除了第 3 頁之外的所有頁面)
            -   `"!2-4"` (提取除了第 2 到 4 頁之外的所有頁面)
            -   `"1-10,!5"` (提取第 1 到 10 頁，但不包括第 5 頁)
        -   **最後一頁表示法 (`-1`)**:
            -   `"-1"`: 提取最後一頁。
            -   `"1--1"`: 提取從第 1 頁到最後一頁 (即整個文件)。
            -   `"5--1"`: 提取從第 5 頁到最後一頁。
            -   `"1-5,-1"`: 提取第 1 到 5 頁以及最後一頁。
            -   `"! -1"`: 提取除了最後一頁之外的所有頁面。
    -   **重要提示：** 整個頁碼範圍字串必須用引號括起來，特別是當它包含特殊字元或空格時 (儘管建議頁碼字串本身不要有空格)。
    -   範例：`--pages "1,3-5,-1"`
-   `--output-dir <directory_path>` (可選):
    -   指定分割後產生的 PDF 檔案儲存的目錄路徑。
    -   如果省略，輸出檔案將儲存在 `output/` 資料夾中。
    -   檔名將根據原始檔名產生，例如 `input_split.pdf`。
    -   範例：`--output-dir split_parts` (輸出到 `files/split_parts/` 或 `output/split_parts/`，取決於引擎的預設行為)

**使用範例：**

1.  提取 `mydoc.pdf` 的第 1 頁和第 3 頁：
    ```
    split --file mydoc.pdf --pages "1,3"
    ```
    (輸出類似 `output/mydoc_split.pdf`)

2.  提取 `long_doc.pdf` 從第 5 頁到最後一頁：
    ```
    split --file long_doc.pdf --pages "5--1"
    ```

3.  提取 `report.pdf` 的所有頁面，除了第 2 頁和最後一頁：
    ```
    split --file report.pdf --pages "!2,!-1"
    ```

4.  提取 `manual.pdf` 的第 1-5 頁，並指定輸出到 `files/manual_extracts` 資料夾：
    ```
    split --file manual.pdf --pages "1-5" --output-dir manual_extracts
    ```
    (輸出將是 `files/manual_extracts/manual_split.pdf`)


## 3. 添加圖章 (add_stamp)

在 PDF 檔案的指定頁面上添加圖像圖章。

**指令格式：**

```
add_stamp --file <input.pdf> --stamp-path <stamp_image.png> --page <page_number> [--pos <position>] [--scale <float>] [--output <output_stamped.pdf>]
```

**參數：**

-   `--file <filepath>` (必要):
    -   要添加圖章的目標 PDF 檔案路徑。
    -   範例：`--file contract.pdf`
-   `--stamp-path <image_filepath>` (必要):
    -   圖章圖像檔案的路徑 (例如 PNG, JPG 格式)。
    -   範例：`--stamp-path company_logo.png`
-   `--page <page_number>` (必要):
    -   要在其上添加圖章的頁碼 (1-indexed)。
    -   目前一次似乎只能指定一個頁面。可以使用 `-1` 代表最後一頁。
    -   範例：`--page 1` 或 `--page -1`
-   `--pos <position_code>` (可選):
    -   指定圖章在頁面上的位置。預設通常是右下角 (`br`)。
    -   **位置代碼：**
        -   `tl`: 左上 (Top-Left)
        -   `tc`: 中上 (Top-Center)
        -   `tr`: 右上 (Top-Right)
        -   `cl`: 中左 (Center-Left)
        -   `cc`: 正中 (Center-Center)
        -   `cr`: 中右 (Center-Right)
        -   `bl`: 左下 (Bottom-Left)
        -   `bc`: 中下 (Bottom-Center)
        -   `br`: 右下 (Bottom-Right) - **預設值**
    -   範例：`--pos tl`
-   `--scale <float_value>` (可選):
    -   圖章的縮放比例，相對於其原始大小。
    -   `1.0` 表示原始大小。`0.5` 表示縮小到 50%。`2.0` 表示放大到 200%。
    -   預設值通常是 `1.0` 或根據頁面大小自動調整的合理值。
    -   範例：`--scale 0.8`
-   `--output <filepath>` (可選):
    -   添加圖章後輸出的 PDF 檔案的路徑和檔名。
    -   如果省略，輸出檔案將儲存在 `output/` 資料夾中，檔名類似 `input_stamped.pdf`。
    -   範例：`--output signed_contract.pdf`

**使用範例：**

1.  在 `document.pdf` 的第一頁右下角添加 `draft_stamp.png` (預設位置和大小)：
    ```
    add_stamp --file document.pdf --stamp-path draft_stamp.png --page 1
    ```

2.  在 `invoice.pdf` 的最後一頁左上角添加 `paid_logo.png`，並將其縮小到 75%：
    ```
    add_stamp --file invoice.pdf --stamp-path paid_logo.png --page -1 --pos tl --scale 0.75
    ```

3.  在 `report.pdf` 的第 3 頁中央添加 `confidential.png`，並指定輸出檔名：
    ```
    add_stamp --file report.pdf --stamp-path confidential.png --page 3 --pos cc --output report_confidential.pdf
    ```

## 4. 內容遮蔽 (redact)

(注意：此工具的具體參數和行為可能仍在開發中。以下基於通用遮蔽功能的假設。)

從 PDF 檔案中移除敏感資訊，通常是通過在指定區域上放置不透明的黑色矩形來實現。**真正的內容遮蔽應該移除底層文字或圖像，而不僅僅是覆蓋。**

**指令格式 (假設性)：**

```
redact --file <input.pdf> --areas "<area_definitions>" [--output <output_redacted.pdf>]
```

或者，如果基於關鍵字：
```
redact --file <input.pdf> --keywords "<keyword1,keyword2>" [--output <output_redacted.pdf>]
```

**參數 (假設性)：**

-   `--file <filepath>` (必要):
    -   要進行內容遮蔽的來源 PDF 檔案路徑。
-   `--areas "<area_definitions_string>"` (如果基於區域):
    -   一個描述要在哪些頁面的哪些區域進行遮蔽的字串。
    -   格式可能類似：`"page=1;rect=x1,y1,x2,y2;page=2;rect=x3,y3,x4,y4"` (座標通常從左下角或左上角開始，單位可能是點)。
    -   這部分需要工具的具體實現來確定。
-   `--keywords "<comma_separated_keywords>"` (如果基於關鍵字):
    -   一個包含逗號分隔的關鍵字的字串。工具將搜索這些關鍵字並嘗試遮蔽它們。
    -   範例：`--keywords "secret,confidential,ProjectX"`
-   `--output <filepath>` (可選):
    -   內容遮蔽後輸出的 PDF 檔案的路徑和檔名。
    -   如果省略，輸出檔案將儲存在 `output/` 資料夾中，檔名類似 `input_redacted.pdf`。

**關於副檔名 / 輸出格式：**

-   內容遮蔽工具的輸出通常仍然是 PDF 檔案 (`.pdf`)。
-   重要的是確保遮蔽是永久性的，即底層的敏感資訊確實被移除了，而不僅僅是被黑色方塊覆蓋（這可以通過編輯 PDF 查看器或複製貼上文字來繞過）。

**使用範例 (假設性，基於關鍵字)：**

1.  在 `document_sensitive.pdf` 中遮蔽所有出現的 "Project Alpha" 和 "Secret Code"：
    ```
    redact --file document_sensitive.pdf --keywords "Project Alpha,Secret Code"
    ```
    (輸出類似 `output/document_sensitive_redacted.pdf`)

2.  在 `financials.pdf` 中遮蔽 "SSN" 並指定輸出檔案：
    ```
    redact --file financials.pdf --keywords "SSN" --output financials_public.pdf
    ```

**給使用者的重要提示 (針對 redact)：**
在處理高度敏感的資訊時，請務必仔細驗證遮蔽工具的效果。開啟輸出的 PDF 檔案，嘗試選取、複製遮蔽區域的文字，以確保資訊確實被移除，而不僅僅是視覺上被覆蓋。如果可能，請使用支援真實內容移除的專業 PDF 遮蔽工具或函式庫。

---

希望這份指令參考對您有所幫助！ 
