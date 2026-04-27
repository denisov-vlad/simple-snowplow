import { defineStore } from "pinia";
import { computed, ref, watch } from "vue";

const STORAGE_KEY = "evnt-demo:settings:v1";

export interface ClickHouseSettings {
  url: string;
  user: string;
  password: string;
  database: string;
}

const DEFAULTS: ClickHouseSettings = {
  url: "http://localhost:8123",
  user: "default",
  password: "password",
  database: "evnt",
};

function loadFromStorage(): ClickHouseSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULTS };
    const parsed = JSON.parse(raw) as Partial<ClickHouseSettings>;
    return { ...DEFAULTS, ...parsed };
  } catch {
    return { ...DEFAULTS };
  }
}

export const useSettings = defineStore("settings", () => {
  const initial = loadFromStorage();
  const url = ref(initial.url);
  const user = ref(initial.user);
  const password = ref(initial.password);
  const database = ref(initial.database);

  const snapshot = computed<ClickHouseSettings>(() => ({
    url: url.value,
    user: user.value,
    password: password.value,
    database: database.value,
  }));

  watch(
    snapshot,
    (next) => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        /* ignore quota / private mode */
      }
    },
    { deep: true },
  );

  function reset() {
    url.value = DEFAULTS.url;
    user.value = DEFAULTS.user;
    password.value = DEFAULTS.password;
    database.value = DEFAULTS.database;
  }

  return { url, user, password, database, snapshot, reset };
});
