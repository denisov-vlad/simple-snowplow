type SnowplowQ = {
  (...args: unknown[]): void;
  q?: unknown[];
};

function ensureLoader(scriptUrl: string): SnowplowQ {
  if (typeof window === "undefined") {
    throw new Error("snowplow loader requires a browser window");
  }
  if (window.snowplow) return window.snowplow;

  window.GlobalSnowplowNamespace = window.GlobalSnowplowNamespace ?? [];
  window.GlobalSnowplowNamespace.push("snowplow");

  const queue: SnowplowQ = function (...args: unknown[]) {
    (queue.q = queue.q ?? []).push(args);
  };
  queue.q = [];
  window.snowplow = queue;

  const script = document.createElement("script");
  script.async = true;
  script.src = scriptUrl;
  const first = document.getElementsByTagName("script")[0];
  if (first?.parentNode) {
    first.parentNode.insertBefore(script, first);
  } else {
    document.head.appendChild(script);
  }
  return queue;
}

export interface SnowplowInitOptions {
  appId?: string;
  collectorOrigin?: string;
  scriptUrl?: string;
  userId?: string;
}

export function initSnowplow(options: SnowplowInitOptions = {}): void {
  const collectorOrigin = options.collectorOrigin ?? window.location.origin;
  const scriptUrl =
    options.scriptUrl ?? new URL("/static/sp.js", collectorOrigin).toString();
  const sp = ensureLoader(scriptUrl);

  sp("newTracker", "sp1", collectorOrigin, {
    appId: options.appId ?? "evnt-demo",
    postPath: "/tracker",
    encodeBase64: false,
    discoverRootDomain: true,
    contexts: {
      webPage: true,
      session: true,
      browser: true,
      performanceNavigationTiming: true,
      performanceTiming: true,
      gaCookies: true,
      geolocation: false,
      clientHints: true,
    },
  });

  if (options.userId) {
    sp("setUserId", options.userId);
  }

  sp("enableActivityTracking", { minimumVisitLength: 5, heartbeatDelay: 5 });
  sp("enableLinkClickTracking", { pseudoClicks: true, trackContent: true });

  sp("addGlobalContexts", [
    {
      schema: "iglu:dev.snowplow.simple/page_data",
      data: { id: "qwe123", type: "main", section: null },
    },
    {
      schema: "iglu:dev.snowplow.simple/user_data",
      data: { name: "John", type: "contributor" },
    },
  ]);
}

export function trackPageView(): void {
  window.snowplow?.("trackPageView");
}

export function trackTestStructEvent(): void {
  window.snowplow?.(
    "trackStructEvent",
    "User Actions",
    "Button Click",
    "Track Event Button",
    null,
    null,
  );
}
