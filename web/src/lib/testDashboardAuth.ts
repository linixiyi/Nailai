"use client";

const TEST_DASHBOARD_PASSWORD_KEY = "nailai:test-dashboard-password";

function canUseSessionStorage() {
  return typeof window !== "undefined" && Boolean(window.sessionStorage);
}

export function getTestDashboardPassword() {
  if (!canUseSessionStorage()) return "";
  try {
    return window.sessionStorage.getItem(TEST_DASHBOARD_PASSWORD_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setTestDashboardPassword(password: string) {
  if (!canUseSessionStorage()) return;
  try {
    if (password) {
      window.sessionStorage.setItem(TEST_DASHBOARD_PASSWORD_KEY, password);
    } else {
      window.sessionStorage.removeItem(TEST_DASHBOARD_PASSWORD_KEY);
    }
  } catch {
    // ignore storage failures
  }
}

export function buildTestDashboardHeaders() {
  const password = getTestDashboardPassword();
  const headers: Record<string, string> = {};
  if (password) {
    headers["x-test-dashboard-password"] = password;
  }
  return headers;
}

export function appendTestDashboardPassword(url: string) {
  const password = getTestDashboardPassword();
  if (!password) return url;

  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}test_dashboard_password=${encodeURIComponent(password)}`;
}
