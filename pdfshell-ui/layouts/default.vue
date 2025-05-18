<template>
  <div class="flex flex-col min-h-screen">
    <header class="bg-gray-800 text-white p-4">
      <nav class="container mx-auto flex justify-between items-center">
        <NuxtLink to="/" class="text-xl font-bold hover:text-gray-300">PDFShell</NuxtLink>
        <div>
          <!-- <NuxtLink to="/" class="px-3 py-2 hover:bg-gray-700 rounded">首頁</NuxtLink> -->
          <!-- <NuxtLink to="/history" class="px-3 py-2 hover:bg-gray-700 rounded">歷史記錄</NuxtLink> -->
          <!-- 未來可加入更多導航連結 -->
        </div>
      </nav>
    </header>

    <main class="flex-grow container mx-auto p-4">
      <slot />
    </main>

    <footer class="bg-gray-200 text-center p-4">
      © {{ new Date().getFullYear() }} PDFShell
    </footer>
  </div>
</template>

<script setup lang="ts">
// 未來可能加入的邏輯
</script>

<style scoped>
/* 未來可能加入的樣式 */
.router-link-exact-active {
  @apply bg-gray-700;
}
</style> 