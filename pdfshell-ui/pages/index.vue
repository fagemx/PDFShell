<template>
  <div class="container mx-auto p-4 pt-8 md:pt-12 max-w-5xl">
    <!-- Header/Logo can be part of the default layout -->
    <!-- <h1 class="text-4xl font-bold mb-8 text-center text-gray-700">PDFShell AI Assistant</h1> -->

    <div class="flex space-x-4">
      
      <!-- Use the new SessionFilesSidebar component -->
      <SessionFilesSidebar 
        :files="uploadedSessionFiles" 
        :session-id="currentSessionId"
        @file-selected="handleFileSelectedFromSidebar"
        @preview-file="handlePreviewFile"
        class="w-1/3 bg-gray-100 p-4 rounded-lg shadow-lg sticky top-4 self-start" 
        style="max-height: calc(100vh - 2rem);"
      />

      <!-- Main Chat Panel -->
      <div class="w-2/3 bg-white shadow-xl rounded-lg">
        <!-- Message display area -->
        <div class="h-80 md:h-96 overflow-y-auto p-4 space-y-3 border-b border-gray-200 bg-gray-50 rounded-t-lg">
          <div v-for="(msg, index) in messages" :key="index" 
               :class="['flex', msg.isUser ? 'justify-end' : 'justify-start']">
            <div :class="['p-3 rounded-xl max-w-lg shadow', msg.isUser ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-800']">
              <template v-if="msg.isThinking">
                <div class="flex items-center space-x-1.5">
                  <div class="w-2 h-2 bg-current rounded-full animate-pulse" style="animation-delay: 0.0s;"></div>
                  <div class="w-2 h-2 bg-current rounded-full animate-pulse" style="animation-delay: 0.2s;"></div>
                  <div class="w-2 h-2 bg-current rounded-full animate-pulse" style="animation-delay: 0.4s;"></div>
                </div>
              </template>
              <template v-else-if="msg.isError">
                 <p class="font-medium text-red-700 dark:text-red-400">錯誤:</p>
                 <p class="text-sm">{{ msg.text }}</p>
              </template>
              <template v-else>
                <!-- Handle object type messages by stringifying them -->
                <pre v-if="typeof msg.text === 'object'" class="whitespace-pre-wrap text-sm font-mono">{{ JSON.stringify(msg.text, null, 2) }}</pre>
                <p v-else class="whitespace-pre-wrap text-sm leading-relaxed">{{ msg.text }}</p>
                <!-- Download button/link integration -->
                <a v-if="!msg.isUser && msg.downloadLink" :href="msg.downloadLink" target="_blank" class="download-button mt-2">
                  下載 {{ msg.text.startsWith('操作完成。輸出檔案: ') ? msg.text.substring('操作完成。輸出檔案: '.length) : '檔案' }}
                </a>
              </template>
              <!-- Display logs if available from bot -->
              <div v-if="!msg.isUser && msg.log && msg.log.length > 0" class="mt-2 text-xs opacity-80 border-t border-gray-300 dark:border-gray-600 pt-2">
                <strong class="font-semibold">處理日誌:</strong>
                <ul class="list-disc list-inside pl-1 mt-1">
                  <li v-for="(logEntry, lIndex) in msg.log" :key="lIndex" class="truncate" :title="logEntry">{{ logEntry }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <!-- File Upload Section -->
        <div class="p-4 border-t border-gray-200 bg-white">
          <label class="block text-sm font-medium text-gray-700 mb-1">上傳新 PDF 檔案 (最多2個):</label>
          <input 
            type="file" 
            accept="application/pdf" 
            multiple 
            @change="onFilesSelected"
            class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
            :disabled="nlpApi.pending.value || pdfFiles.length >= 2"
          />
          <div v-if="pdfFiles.length > 0" class="mt-2 space-y-1">
            <p class="text-xs text-gray-600">待上傳檔案 (本次操作將包含這些新檔案)：</p>
            <div v-for="(file, index) in pdfFiles" :key="index" class="flex items-center justify-between text-sm p-2 bg-gray-100 rounded">
              <span class="text-gray-700 truncate pr-2">{{ file.name }} ({{ (file.size / 1024).toFixed(1) }} KB)</span>
              <button @click="removeFile(index)" class="text-red-500 hover:text-red-700 text-xs font-semibold" :disabled="nlpApi.pending.value">
                移除
              </button>
            </div>
          </div>
        </div>

        <!-- Input area (MOVED HERE) -->
        <div class="p-4 border-t border-gray-200 bg-white rounded-b-lg">
          <div class="flex items-end space-x-2">
            <textarea
              v-model="userInput"
              @keypress.enter.prevent.exact="sendMessage"
              placeholder="輸入您的 PDF 操作指令 (例如：合併 a.pdf 和 b.pdf 輸出為 c.pdf)"
              class="flex-grow p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none shadow-sm text-sm"
              rows="1" 
              ref="textareaRef"
              :disabled="nlpApi.pending.value"
              @input="autoGrowTextarea"
            ></textarea>
            <button
              @click="sendMessage"
              :disabled="nlpApi.pending.value || (!userInput.trim() && pdfFiles.length === 0)"
              class="bg-blue-600 text-white px-5 py-3 rounded-md hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors duration-150 shadow-sm h-full"
              style="min-height: 46px;" 
            >
              <svg v-if="nlpApi.pending.value" class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span v-else>送出</span>
            </button>
          </div>
          <p v-if="nlpApi.error.value && !nlpApi.pending.value" class="text-red-600 text-xs mt-2">
            處理您的請求時發生錯誤: {{ typeof nlpApi.error.value === 'string' ? nlpApi.error.value : JSON.stringify(nlpApi.error.value) }}
          </p>
        </div>
      </div>
    </div>
    <p class="text-xs text-gray-500 text-center mt-4">Shift+Enter 換行。所有互動都將被記錄。</p>
    
    <!-- PDF Preview Modal -->
    <PdfPreviewModal 
      :show="showPdfPreviewModal" 
      :pdf-url="pdfPreviewUrl" 
      :pdf-name="pdfPreviewName" 
      @close="showPdfPreviewModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted } from 'vue';
import { useNLPApi } from '~/composables/useApi';
import SessionFilesSidebar from '~/components/SessionFilesSidebar.vue'; // Import the new component
import PdfPreviewModal from '~/components/PdfPreviewModal.vue'; // Import the modal component

interface Message {
  text: string | Record<string, any>; // Allow text to be an object for structured data like JSON
  isUser: boolean;
  isThinking?: boolean;
  isError?: boolean;
  log?: string[];
  timestamp?: Date;
  downloadLink?: string; // Added for download functionality
}

// Define a type for processed session files
interface ProcessedFile {
  user_label: string;
  session_filename: string;
  isPublic?: boolean; // Added to distinguish public files
}

const userInput = ref('');
const messages = ref<Message[]>([]);
const nlpApi = useNLPApi();
const textareaRef = ref<HTMLTextAreaElement | null>(null);
const pdfFiles = ref<File[]>([]); // Stores files selected in the input, cleared after send
const currentSessionId = ref<string | null>(null); // Will be set by API responses, not localStorage
const uploadedSessionFiles = ref<ProcessedFile[]>([]); // Will be set by new API for default files

// PDF Preview Modal State
const showPdfPreviewModal = ref(false);
const pdfPreviewUrl = ref<string | null>(null);
const pdfPreviewName = ref<string | undefined>(undefined);

const autoGrowTextarea = () => {
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'; // Reset height
    textareaRef.value.style.height = `${textareaRef.value.scrollHeight}px`;
    // Limit max height if needed
    // const maxHeight = 120; // example max height in px
    // if (textareaRef.value.scrollHeight > maxHeight) {
    //   textareaRef.value.style.height = `${maxHeight}px`;
    //   textareaRef.value.style.overflowY = 'auto';
    // } else {
    //   textareaRef.value.style.overflowY = 'hidden';
    // }
  }
};

const scrollToBottom = () => {
  nextTick(() => {
    const container = document.querySelector('.overflow-y-auto'); // More specific selector if needed
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  });
};

// Scroll to bottom when new messages are added or when pending state changes (e.g. thinking bubble appears)
watch(messages, scrollToBottom, { deep: true });
watch(() => nlpApi.pending.value, scrollToBottom);

const formatMessagesToHistory = (msgs: Message[]): Array<[string, string]> => {
  const history: Array<[string, string]> = [];
  let i = 0;
  while (i < msgs.length) {
    // Find a user message, skipping thinking/error messages
    let userMsg: Message | null = null;
    while (i < msgs.length) {
      if (msgs[i].isUser && !msgs[i].isThinking && !msgs[i].isError) {
        userMsg = msgs[i];
        break;
      }
      i++;
    }
    if (!userMsg) break; // No more user messages

    const userText = typeof userMsg.text === 'string' ? userMsg.text : JSON.stringify(userMsg.text);
    i++; // Move to the next message index

    // Find the corresponding agent message, skipping thinking/error/user messages
    let agentMsg: Message | null = null;
    while (i < msgs.length) {
      if (!msgs[i].isUser && !msgs[i].isThinking && !msgs[i].isError) {
        agentMsg = msgs[i];
        break;
      }
      // If we encounter another user message before an agent response,
      // or if we encounter a thinking/error message that implies no valid agent response for the current userMsg,
      // then the current userMsg does not have a pair.
      if (msgs[i].isUser || msgs[i].isThinking || msgs[i].isError) {
          // This user message doesn't have a valid pair, so break to not include it.
          // We need to rewind 'i' if we overshot to a message that shouldn't consume the userMsg.
          // However, the outer loop structure will correctly find the *next* valid user message.
          // So, if agentMsg is not found, userMsg is effectively skipped for pairing.
          agentMsg = null; // Explicitly mark as no agent message found for this user message
          break; 
      }
      i++;
    }
    if (!agentMsg) break; // No corresponding agent message found or loop ended

    const agentText = typeof agentMsg.text === 'string' ? agentMsg.text : JSON.stringify(agentMsg.text);
    history.push([userText, agentText]);
    i++; // Move to the next message index for the next pair
  }
  return history;
};

// Function to handle file selection
function onFilesSelected(event: Event) {
  const input = event.target as HTMLInputElement;
  if (!input.files) return;
  let files = Array.from(input.files).filter(f => f.type === "application/pdf");
  // Limit to 2 files in total (newly selected + already selected).
  // The logic here is for files *currently staged* in the input.
  // If you want to manage a session-wide limit of 2 active files,
  // you'd also need to consider uploadedSessionFiles.value.length.
  // For now, this limits each individual upload action.
  const currentFileCount = pdfFiles.value.length;
  const availableSlots = 2 - currentFileCount;
  
  if (files.length > availableSlots) {
    // Simple alert, can be replaced with a more sophisticated UI notification
    alert(`您最多只能再選擇 ${availableSlots} 個檔案。已選取前 ${availableSlots} 個。`);
    files = files.slice(0, availableSlots);
  }
  pdfFiles.value = [...pdfFiles.value, ...files];
  input.value = ''; // Clear the input to allow selecting the same file again if removed
}

// Function to remove a selected file from the staging list (pdfFiles)
function removeFile(index: number) {
  pdfFiles.value.splice(index, 1);
}

// Function to remove a file that has been processed and is part of the session
function removeUploadedSessionFile(index: number) {
  uploadedSessionFiles.value.splice(index, 1);
  // Potentially, you might want to call a backend API here to delete the file from the server's session storage
  // For now, it just removes it from the client-side list.
}

// Handler for file selection from sidebar (optional for now)
function handleFileSelectedFromSidebar(file: ProcessedFile) {
  console.log("File selected from sidebar in parent (index.vue):", file);
  // Append the selected file's user_label to the userInput
  if (userInput.value.trim() !== '' && !userInput.value.endsWith(' ')) {
    userInput.value += ' '; // Add a space if userInput is not empty and doesn't end with a space
  }
  userInput.value += file.user_label;
  // Optionally, focus the textarea after appending
  textareaRef.value?.focus();
  // Trigger autoGrowTextarea in case the new content changes the height
  autoGrowTextarea();
}

// Handler for previewing a file from the sidebar
function handlePreviewFile(file: ProcessedFile) {
  console.log("Preview file requested in parent (index.vue):", file);
  
  if (file.isPublic) {
    pdfPreviewUrl.value = `/api/v1/public-files/download/${encodeURIComponent(file.session_filename)}/`;
  } else {
    // This is a session file, requires session_id
    if (currentSessionId.value) {
      pdfPreviewUrl.value = `/api/v1/download/${currentSessionId.value}/${encodeURIComponent(file.session_filename)}`;
    } else {
      console.error("Cannot preview session file: currentSessionId is not set.");
      // Optionally, show an error message to the user
      alert("無法預覽會話檔案：會話 ID 未設定。");
      return; // Do not proceed to show modal
    }
  }
  pdfPreviewName.value = file.user_label;
  showPdfPreviewModal.value = true;
}

const sendMessage = async () => {
  const text = userInput.value.trim();
  // Allow sending if there's text, or if there are newly selected files, or if there are already processed session files
  if (!text && pdfFiles.value.length === 0 && uploadedSessionFiles.value.length === 0) return;
  if (nlpApi.pending.value) return;

  const currentInput = userInput.value;
  const historyPayload = formatMessagesToHistory(messages.value);

  let messageForDisplay = currentInput;
  if (!currentInput) {
    if (pdfFiles.value.length > 0) {
      messageForDisplay = `(操作新上傳檔案: ${pdfFiles.value.map(f => f.name).join(', ')})`;
    } else if (uploadedSessionFiles.value.length > 0) {
      messageForDisplay = `(操作已上傳檔案: ${uploadedSessionFiles.value.map(f => f.user_label).join(', ')})`;
    }
  }
  
  messages.value.push({ text: messageForDisplay, isUser: true, timestamp: new Date() });
  userInput.value = '';
  autoGrowTextarea();

  const thinkingMessageIndex = messages.value.length;
  messages.value.push({ text: '...', isUser: false, isThinking: true, timestamp: new Date() });
  
  let payload: FormData | { text: string; history: Array<[string, string]>; session_files?: ProcessedFile[] };

  if (pdfFiles.value.length > 0) { // If new files are selected, always use FormData
    payload = new FormData();
    payload.append('text', currentInput);
    payload.append('history', JSON.stringify(historyPayload));
    pdfFiles.value.forEach((file, index) => {
      payload.append(`file${index + 1}`, file, file.name);
    });
    // If there are also existing session files, the backend's nl_view should ideally merge them.
    // For simplicity here, new uploads via FormData might "reset" the context to only these new files
    // unless backend explicitly handles merging FormData files with existing session_files.
    // The current backend nl_view does not explicitly merge FormData files with session_files passed in other ways.
    // It prioritizes FormData uploads for constructing available_files_for_llm.
    // To correctly use existing session files alongside new uploads, the backend would need adjustment,
    // or the frontend would need to *always* send session_files and handle new uploads by first
    // uploading them to a temp endpoint, getting their session_filename, then adding to the list
    // before calling nl_execute. This is more complex.
    // For now, if pdfFiles is not empty, we send only those.
    
  } else { // No new files selected, send as JSON
    payload = { text: currentInput, history: historyPayload };
    if (uploadedSessionFiles.value.length > 0) {
      payload.session_files = uploadedSessionFiles.value;
    }
  }
  
  await nlpApi.nlExecute(payload);
  pdfFiles.value = []; // Clear newly selected files after sending, as they are now (presumably) processed or sent

  messages.value.splice(thinkingMessageIndex, 1);

  if (nlpApi.response.value) {
    // Update session ID and processed files list from response
    if (nlpApi.response.value.session_id) {
      currentSessionId.value = nlpApi.response.value.session_id;
    }
    if (nlpApi.response.value.processed_session_files && Array.isArray(nlpApi.response.value.processed_session_files)) {
      // Backend now sends the complete list of files (public and session, including new ones with correct isPublic flag)
      // So, we can directly assign it.
      uploadedSessionFiles.value = nlpApi.response.value.processed_session_files.map(f => ({
        user_label: f.user_label,
        session_filename: f.session_filename,
        isPublic: f.isPublic === true // Ensure isPublic is strictly boolean true or false
      }));
      console.log('nlExecute response: Updated uploadedSessionFiles from backend authoritative list:', uploadedSessionFiles.value);
    }

    if (nlpApi.response.value.status === 'ok') {
      let messageText = '';
      const responseData = nlpApi.response.value.data;
      const toolName = nlpApi.response.value.tool_name;
      let downloadLink: string | undefined = undefined;

      if (toolName === 'clarify') {
        messageText = typeof responseData === 'string' && responseData.trim() !== '' 
                        ? responseData 
                        : '請問您需要什麼 PDF 協助？';
      } else {
        if (typeof responseData === 'string' && responseData.trim() !== '') {
          // Check if the responseData is a filename of a file processed in this session
          // The backend now includes new output files in processed_session_files.
          // We rely on this list to determine if a file is a session file.
          const matchedFile = uploadedSessionFiles.value.find(f => f.session_filename === responseData);

          if (matchedFile) {
            messageText = `操作完成。輸出檔案: ${responseData}`;
            if (matchedFile.isPublic) {
              downloadLink = `/api/v1/public-files/download/${encodeURIComponent(responseData)}/`;
            } else if (currentSessionId.value) {
              downloadLink = `/api/v1/download/${currentSessionId.value}/${encodeURIComponent(responseData)}`;
            } else {
               console.warn("Cannot create download link for session file without session_id", responseData);
               messageText = `操作完成。檔案 ${responseData} 已產生，但無法建立下載連結 (缺少 session ID)。`;
            }
          } else {
            // If not in uploadedSessionFiles, it's likely just a string message from the bot.
            messageText = responseData;
          }
        } else {
          messageText = '操作完成。';
        }
      }

      messages.value.push({ 
        text: messageText,
        isUser: false,
        log: nlpApi.response.value.log,
        timestamp: new Date(),
        downloadLink: downloadLink
      });
    } else {
      const errorHint = nlpApi.response.value.hint || '';
      const errorMessage = nlpApi.response.value.message || '處理請求時發生未知的應用程式錯誤。';
      const errorText = errorHint ? `${errorHint} (${errorMessage})` : errorMessage;
      messages.value.push({ text: errorText, isUser: false, isError: true, timestamp: new Date() });
    }
  } else if (nlpApi.error.value) { 
    const errorObject = nlpApi.error.value as any; // Type assertion
    const errorText = errorObject?.message || String(nlpApi.error.value);
    messages.value.push({ text: errorText, isUser: false, isError: true, timestamp: new Date() });
  }
  textareaRef.value?.focus();
};

onMounted(async () => { 
  try {
    const response = await $fetch<{ public_files: Omit<ProcessedFile, 'isPublic'>[] }>('/api/v1/public-files/');
    if (response && response.public_files && Array.isArray(response.public_files)) {
      // Mark these files as public
      uploadedSessionFiles.value = response.public_files.map(file => ({ ...file, isPublic: true }));
      console.log('onMounted: Default public files loaded from API:', uploadedSessionFiles.value);
    } else {
      console.warn('onMounted: No public files returned from API or unexpected response format.');
      uploadedSessionFiles.value = []; // Ensure it's an empty array on failure or bad format
    }
  } catch (error) {
    console.error('onMounted: Error fetching public files:', error);
    uploadedSessionFiles.value = []; // Ensure it's an empty array on error
  }

  console.log('onMounted: Initial currentSessionId (should be null):', currentSessionId.value);
  // console.log('onMounted: Initial uploadedSessionFiles (should be empty or set by new API later):', uploadedSessionFiles.value);

  messages.value.push({ text: "您好！我是 PDFShell AI 助理。請告訴我您想對 PDF 檔案做些什麼？\n例如：『將 sample1.pdf 和 sample2.pdf 合併成 final_report.pdf』，『為 final_report.pdf 的每一頁加上公司印章 stamp.png』", isUser: false, timestamp: new Date() });
  textareaRef.value?.focus();
  autoGrowTextarea(); // Adjust on load in case of initial content
});

</script>

<style scoped>
/* Tailwind's JIT mode should handle most styles. Add specific overrides here if needed. */
textarea {
  min-height: 46px; /* Match button height roughly */
  transition: height 0.2s ease-in-out;
}

/* Style for download button */
.download-button {
  display: inline-block;
  margin-top: 8px;
  padding: 6px 12px;
  background-color: #2563eb; /* bg-blue-600 */
  color: white;
  text-decoration: none;
  border-radius: 0.375rem; /* rounded-md */
  font-size: 0.875rem; /* text-sm */
  font-weight: 500; /* font-medium */
  transition: background-color 0.15s ease-in-out;
}
.download-button:hover {
  background-color: #1d4ed8; /* bg-blue-700 */
}
</style> 