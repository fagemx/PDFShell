import { ref } from 'vue';

// 與後端 API 回應結構對應，參考 DAY10.md 的規劃
interface NLApiResponse {
  status: 'ok' | 'error';
  data?: any; // 成功時的資料
  log?: string[]; // 處理日誌
  message?: string; // 通用訊息
  code?: string; // 錯誤代碼
  hint?: string; // 錯誤提示
  tool_name?: string; // Added to align with backend response and check.md
}

interface NLTextPayload {
  text: string;
  history: Array<[string, string]>; // Agent 期望的歷史格式
}

export function useNLPApi() {
  const pending = ref(false);
  const error = ref<string | null>(null);
  const responseData = ref<NLApiResponse | null>(null); // 更名以區分

  const nlExecute = async (payload: NLTextPayload | FormData) => {
    pending.value = true;
    error.value = null;
    responseData.value = null;
    try {
      const headers: HeadersInit = {};
      let body: BodyInit;

      if (payload instanceof FormData) {
        body = payload;
        // Content-Type is automatically set by the browser for FormData
      } else {
        headers['Content-Type'] = 'application/json';
        body = JSON.stringify(payload);
      }

      const data = await $fetch('/api/v1/nl/', { 
        method: 'POST',
        headers: headers, // Pass headers
        body: body, // Pass processed body
      });
      responseData.value = data as NLApiResponse; 
    } catch (e: any) {
      console.error("API call failed in useNLPApi:", e);
      const errorMessage = e.data?.statusMessage || e.data?.hint || e.data?.message || e.message || 'An unexpected error occurred.';
      error.value = errorMessage;
      // 即使是 $fetch 拋出的錯誤，也嘗試填充 responseData 以便 UI 統一處理
      responseData.value = { 
        status: 'error', 
        message: errorMessage,
        hint: e.data?.hint,
        code: e.data?.code
      };
    } finally {
      pending.value = false;
    }
  };

  return {
    pending,
    error,
    response: responseData, // 導出時使用 response
    nlExecute,
  };
} 