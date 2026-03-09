<template>
  <router-view v-slot="{ Component }">
    <keep-alive include="Timeline">
      <component :is="Component" />
    </keep-alive>
  </router-view>
</template>
