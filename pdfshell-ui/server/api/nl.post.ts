// server/api/nl.post.ts
export default defineEventHandler(async (event) => {
  const rawText = await readRawBody(event);

  if (typeof rawText !== 'string' || !rawText.trim()) {
    // Nuxt 3 建議使用 createError 拋出錯誤
    throw createError({ statusCode: 400, statusMessage: 'Input text cannot be empty.' });
  }

  // 從環境變數讀取後端 API URL，並提供預設值
  // 請確保在 .env 檔案中設定 PDFSHELL_BACKEND_URL，例如: PDFSHELL_BACKEND_URL=http://localhost:8000
  const backendUrl = process.env.PDFSHELL_BACKEND_URL || 'http://localhost:8000';
  const nlEndpoint = `${backendUrl}/api/v1/nl/`; // 根據 Day 4 後端 API 路徑

  try {
    // 向後端 Django API 發送請求
    // 後端期望的 body 格式是 {"text": "user command"}
    const backendResponse = await $fetch(nlEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: { text: rawText }, // 將純文字封裝到 JSON 物件中
    });
    return backendResponse; // 直接回傳後端的響應
  } catch (error: any) {
    console.error(`Error proxying to backend NL service (${nlEndpoint}):`, error.data?.message || error.message);
    // 將後端錯誤或網路錯誤傳遞給前端
    throw createError({
      statusCode: error.response?.status || error.statusCode || 500,
      statusMessage: error.data?.detail || error.data?.hint || error.data?.message || error.statusMessage || 'Error communicating with the backend NL service.',
      data: error.data // 包含後端可能提供的額外錯誤資訊
    });
  }
}); 