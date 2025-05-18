// store/history.ts
import { defineStore } from 'pinia'

// 模擬後端 Operation 模型的部分欄位
export interface Operation {
  id: string;
  tool: string;
  args: Record<string, any>;
  outputHash?: string;
  createdAt: Date;
  status: 'success' | 'failure';
}

interface HistoryState {
  historyItems: Operation[];
  isLoading: boolean;
  error: string | null;
}

// 模擬 API 呼叫延遲
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export const useHistoryStore = defineStore('history', {
  state: (): HistoryState => ({
    historyItems: [],
    isLoading: false,
    error: null,
  }),
  actions: {
    // 模擬從 API 獲取歷史記錄
    async fetchHistory() {
      this.isLoading = true;
      this.error = null;
      try {
        await delay(1000); // 模擬網路延遲
        // Mock 數據
        const mockData: Operation[] = [
          { id: '1', tool: 'merge', args: { files: ['a.pdf', 'b.pdf'], output: 'merged.pdf' }, outputHash: 'hash123', createdAt: new Date(Date.now() - 3600000), status: 'success' },
          { id: '2', tool: 'split', args: { file: 'c.pdf', pages: '1-2' }, outputHash: 'hash456', createdAt: new Date(Date.now() - 7200000), status: 'success' },
          { id: '3', tool: 'redact', args: { file: 'd.pdf', patterns: ['secret'] }, createdAt: new Date(Date.now() - 10800000), status: 'failure' },
        ];
        this.historyItems = mockData;
      } catch (e: any) {
        this.error = e.message || 'Failed to fetch history';
      } finally {
        this.isLoading = false;
      }
    },
    addHistoryItem(item: Operation) {
      // 實際應用中，這可能是由 WebSocket 或其他即時更新觸發
      this.historyItems.unshift(item); // 將新項目加到開頭
    }
  },
  getters: {
    totalOperations: (state) => state.historyItems.length,
    successfulOperations: (state) => state.historyItems.filter(item => item.status === 'success').length,
    failedOperations: (state) => state.historyItems.filter(item => item.status === 'failure').length,
  }
}) 