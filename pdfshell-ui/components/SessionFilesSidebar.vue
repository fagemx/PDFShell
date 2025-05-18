<template>
  <div class="session-files-sidebar">
    <h2 class="text-lg font-semibold text-gray-700 mb-3 sticky top-0 bg-gray-100 pt-1 pb-2 z-10">Session 檔案</h2>
    <div v-if="files && files.length > 0" class="space-y-2 overflow-y-auto" style="max-height: calc(100vh - 150px);">
      <div 
        v-for="file in files" 
        :key="file.session_filename" 
        class="p-2 border rounded-md bg-white flex items-center justify-between"
        :title="`檔案: ${file.user_label}`"
      >
        <span 
          class="text-sm text-gray-800 truncate cursor-pointer hover:text-blue-600 flex-grow mr-2"
          @click="onPreviewClick(file)"
          :title="`預覽 ${file.user_label}`"
        >
          {{ file.user_label }}
        </span>
        <button 
          @click.stop="onFileLabelClick(file)"
          class="p-1 hover:bg-gray-200 rounded text-lg font-semibold"
          title="將檔名加入輸入框"
        >
          +
        </button>
      </div>
    </div>
    <div v-else>
      <p class="text-sm text-gray-500">目前無可用檔案。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, defineEmits, watchEffect } from 'vue';

interface ProcessedFile {
  user_label: string;
  session_filename: string;
  isPublic?: boolean; // Keep this if still used by parent
}

const props = defineProps<{
  files: ProcessedFile[];
  sessionId: string | null;
}>();

watchEffect(() => {
  // console.log('SessionFilesSidebar: files prop updated', props.files); // Keep for debugging if needed
  // if (props.files) {
  //   console.log('SessionFilesSidebar: files length', props.files.length);
  // }
});

const emit = defineEmits(['file-selected', 'preview-file']);

// Emits 'file-selected' - used to add filename to input field in parent
function onFileLabelClick(file: ProcessedFile) { 
  console.log("Sidebar add to input icon (+) clicked:", file);
  emit('file-selected', file); 
}

// Emits 'preview-file' - used to show preview modal in parent
function onPreviewClick(file: ProcessedFile) {
  console.log("Sidebar file label (for preview) clicked:", file);
  emit('preview-file', file);
}
</script>

<style scoped>
.session-files-sidebar {
  /* Add any specific styles for the sidebar container itself if needed */
}
</style> 