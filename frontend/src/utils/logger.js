const BACKEND_LOG_URL = import.meta.env.VITE_BACKEND_LOG_URL || "http://127.0.0.1:8000/api/accounts/log/";

function getAuthHeaders() {
  const access = localStorage.getItem("access");
  return access
    ? { Authorization: `Bearer ${access}` }
    : {};
}

async function sendFrontendLog(level, message, context = {}) {
  try {
    await fetch(BACKEND_LOG_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        level,
        message,
        context,
      }),
    });
  } catch (error) {
    // Logging should never break the app.
    console.warn("Unable to send frontend log:", error);
  }
}

export function logInfo(message, context = {}) {
  console.info("[FRONTEND]", message, context);
  sendFrontendLog("INFO", message, context);
}

export function logWarn(message, context = {}) {
  console.warn("[FRONTEND]", message, context);
  sendFrontendLog("WARNING", message, context);
}

export function logError(message, context = {}) {
  console.error("[FRONTEND]", message, context);
  sendFrontendLog("ERROR", message, context);
}
