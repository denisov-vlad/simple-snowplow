import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "@/App.vue";
import { router } from "@/router";
import { installInterceptor } from "@/lib/interceptor";
import { initSnowplow, trackPageView } from "@/lib/snowplow";
import "@/styles/global.css";

const app = createApp(App);
app.use(createPinia());
app.use(router);

installInterceptor();
initSnowplow({ appId: "evnt-demo", userId: "test@email.com" });

app.mount("#app");

router.isReady().then(() => {
  trackPageView();
});
