<template>
  <div v-if="show" class="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4" @click.self="closeModal">
    <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl h-full max-h-[90vh] flex flex-col overflow-hidden">
      <div class="flex justify-between items-center p-3 border-b bg-gray-50">
        <h3 class="text-lg font-semibold text-gray-700 truncate" :title="pdfName">預覽: {{ pdfName }}</h3>
        <button @click="closeModal" class="text-gray-500 hover:text-gray-700 text-2xl font-bold">&times;</button>
      </div>
      <div class="flex-grow p-1 bg-gray-200">
        <iframe v-if="pdfUrl" :src="pdfUrl" width="100%" height="100%" frameborder="0"></iframe>
        <div v-else class="flex items-center justify-center h-full text-gray-500">
          無法載入 PDF 預覽。
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, defineEmits, computed } from 'vue';

const props = defineProps<{
  show: boolean;
  pdfUrl: string | null;
  pdfName?: string; // Optional: to display the name in the modal header
}>();

const emit = defineEmits(['close']);

const closeModal = () => {
  emit('close');
};

// Fallback for pdfName if not provided
const pdfName = computed(() => {
  if (props.pdfName) return props.pdfName;
  if (props.pdfUrl) {
    try {
      const urlParts = props.pdfUrl.split('/');
      return urlParts[urlParts.length - 1] || '檔案';
    } catch (e) {
      return '檔案';
    }
  }
  return '檔案';
});

</script>

<style scoped>
/* Additional styling if needed */
iframe {
  border: none; /* Ensure iframe has no border by default */
}
</style> 