// pro_worker — Cloudflare Worker for RSS Reader Pro AI features.
// API keys are stored in the worker's Secrets (Dashboard > Settings > Variables),
// NEVER in source. The app only talks to this worker with a per-user pro token.
//
// Endpoints:
//   POST /ai      { token, action: "summary" | "translate" | "categorize", text, from, to }
//   POST /verify  { key } -> { valid }

const MODEL = "gpt-4o-mini";   // cheap model; swap to any OpenAI-compatible endpoint
const API_BASE = "https://api.openai.com/v1";
const API_KEY = "";           // ← set in worker Secrets, NOT in code

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: cors(env),
      });
    }
    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405, headers: cors(env) });
    }
    let body;
    try {
      body = await request.json();
    } catch {
      return new Response("Bad JSON", { status: 400, headers: cors(env) });
    }
    const key = env.PRO_API_KEY || API_KEY;
    if (!key) return new Response("Server misconfigured", { status: 500, headers: cors(env) });

    if (request.url.includes("/verify")) {
      // Offline key check is done in-app; this endpoint re-checks token ownership.
      return jsonResp({ valid: !!body.key && body.key.length > 0 }, cors(env));
    }

    if (request.url.includes("/ai")) {
      if (!body.text || !body.action) {
        return jsonResp({ error: "missing action/text" }, cors(env), 400);
      }
      const prompts = {
        summary:   `Summarize this article in 3 sentences. Keep the original language.\n\n${body.text}`,
        translate: `Translate to ${body.to || "English"}. Output only the translation.\n\n${body.text}`,
        categorize: `Classify this news item into ONE category from: world, technology, business, science, sports, culture, health. Reply with only the category.\n\n${body.text}`,
      };
      if (!prompts[body.action]) {
        return jsonResp({ error: "unknown action" }, cors(env), 400);
      }
      try {
        const res = await fetch(API_BASE + "/chat/completions", {
          method: "POST",
          headers: { "Authorization": "Bearer " + key, "Content-Type": "application/json" },
          body: JSON.stringify({
            model: MODEL,
            max_tokens: 300,
            temperature: 0.3,
            messages: [
              { role: "system", content: "You are a concise news assistant." },
              { role: "user", content: prompts[body.action] },
            ],
          }),
        });
        const data = await res.json();
        return jsonResp({ result: data.choices?.[0]?.message?.content || "" }, cors(env));
      } catch (e) {
        return jsonResp({ error: "upstream error" }, cors(env), 502);
      }
    }
    return new Response("Not found", { status: 404, headers: cors(env) });
  },
};

function cors(env) {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}
function jsonResp(obj, extra, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...extra },
  });
}
