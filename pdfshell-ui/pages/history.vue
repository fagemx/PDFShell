<template>
  <div class="container mx-auto p-4">
    <h1 class="text-3xl font-bold mb-6">操作歷史記錄</h1>

    <div v-if="historyStore.isLoading" class="text-center">
      <p>正在載入歷史記錄...</p>
      <!-- 可以加入一個 spinner 元件 -->
    </div>

    <div v-else-if="historyStore.error" class="text-red-500 bg-red-100 p-4 rounded">
      <p>載入歷史記錄失敗：{{ historyStore.error }}</p>
    </div>

    <div v-else-if="historyStore.historyItems.length === 0" class="text-gray-500">
      <p>目前沒有操作歷史記錄。</p>
    </div>

    <div v-else class="overflow-x-auto">
      <table class="min-w-full bg-white shadow-md rounded-lg">
        <thead class="bg-gray-800 text-white">
          <tr>
            <th class="py-3 px-4 uppercase font-semibold text-sm text-left">時間</th>
            <th class="py-3 px-4 uppercase font-semibold text-sm text-left">工具</th>
            <th class="py-3 px-4 uppercase font-semibold text-sm text-left">參數</th>
            <th class="py-3 px-4 uppercase font-semibold text-sm text-left">狀態</th>
            <th class="py-3 px-4 uppercase font-semibold text-sm text-left">輸出雜湊</th>
          </tr>
        </thead>
        <tbody class="text-gray-700">
          <tr v-for="item in historyStore.historyItems" :key="item.id" class="border-b hover:bg-gray-100">
            <td class="py-3 px-4">{{ formatDate(item.createdAt) }}</td>
            <td class="py-3 px-4">{{ item.tool }}</td>
            <td class="py-3 px-4 text-xs">
              <pre class="max-w-xs overflow-x-auto bg-gray-50 p-1 rounded">{{ JSON.stringify(item.args, null, 2) }}</pre>
            </td>
            <td class="py-3 px-4">
              <span :class="item.status === 'success' ? 'text-green-500' : 'text-red-500'">
                {{ item.status === 'success' ? '成功' : '失敗' }}
              </span>
            </td>
            <td class="py-3 px-4 text-xs">{{ item.outputHash ? item.outputHash.substring(0, 10) + '...' : 'N/A' }}</td>
          </tr>
        </tbody>
      </table>
      <div class="mt-4 text-sm text-gray-600">
        <p>總操作數: {{ historyStore.totalOperations }}</p>
        <p>成功: {{ historyStore.successfulOperations }} | 失敗: {{ historyStore.failedOperations }}</p>
      </div>
    </div>
     <button @click="addMockItem" class="mt-4 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
      新增模擬歷史項目
    </button>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useHistoryStore, type Operation } from '~/store/history';

const historyStore = useHistoryStore();

onMounted(() => {
  if (historyStore.historyItems.length === 0) {
    historyStore.fetchHistory();
  }
});

const formatDate = (date: Date): string => {
  return new Date(date).toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
};

// 用於測試的函數，模擬添加新的歷史項目
const addMockItem = () => {
  const newItem: Operation = {
    id: (Math.random() * 1000000).toString(),
    tool: 'test-tool',
    args: { param1: 'value1', param2: Math.random() > 0.5 },
    createdAt: new Date(),
    status: Math.random() > 0.3 ? 'success' : 'failure',
    outputHash: 'newHash' + Math.floor(Math.random() * 1000)
  };
  historyStore.addHistoryItem(newItem);
};
</script>

<style scoped>
/* 如果需要，可以添加一些特定樣式 */
pre {
  white-space: pre-wrap;       /* CSS3 */
  white-space: -moz-pre-wrap;  /* Mozilla, since 1999 */
  white-space: -pre-wrap;      /* Opera 4-6 */
  white-space: -o-pre-wrap;    /* Opera 7 */
  word-wrap: break-word;       /* Internet Explorer 5.5+ */
}
</style> 