<!--
  应用程序根组件
  
  这是Vue应用的最顶层组件，只包含一个router-view用于渲染路由匹配的组件。
  所有页面组件都会在这个router-view中切换显示。
  
  全局样式：
  - 重置默认边距和内边距
  - 设置box-sizing为border-box
  - 配置系统字体栈
  - 启用字体平滑渲染
-->
<template>
  <router-view />
</template>

<script setup lang="ts">
// App根组件
// 使用Vue 3 Composition API的setup语法
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

/* 全局字体和渲染优化 */
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;  /* WebKit字体平滑 */
  -moz-osx-font-smoothing: grayscale;   /* Firefox字体平滑 */
}
</style>