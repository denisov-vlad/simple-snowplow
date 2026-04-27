/// <reference types="vite/client" />

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<{}, {}, any>;
  export default component;
}

interface SnowplowQueue {
  (...args: unknown[]): void;
  q?: unknown[];
}

declare global {
  interface Window {
    snowplow: SnowplowQueue;
    GlobalSnowplowNamespace?: string[];
  }
}

export {};
