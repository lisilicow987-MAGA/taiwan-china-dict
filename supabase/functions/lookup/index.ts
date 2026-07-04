// Supabase Edge Function:lookup
// 用 Google Gemini 免費 API,給一個中國/臺灣用語,回傳對應說法的「建議草稿」。
// 金鑰放 Edge Function 密鑰 GEMINI_API_KEY(伺服器端保管,不進前端、不進 git)。
// 前端以 sb.functions.invoke("lookup", { body: { term, direction } }) 呼叫。

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

// 免費層模型;可用密鑰 GEMINI_MODEL 覆寫(免改程式),預設 gemini-2.5-flash。
// 免費額度是「每個模型分開算」,撞到 429 時可換成 gemini-2.5-flash-lite / gemini-1.5-flash 等。
const MODEL = Deno.env.get("GEMINI_MODEL") || "gemini-2.5-flash";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });

  // 擋掉只用公開 anon 金鑰的呼叫,避免有人白嫖 Gemini 額度。
  // 登入者的 JWT role 為 authenticated;純 anon 金鑰 role 為 anon → 拒絕。
  try {
    const jwt = (req.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
    const role = JSON.parse(decodeJwtPayload(jwt)).role;
    if (role === "anon") return json({ error: "需登入後才能使用 AI 查詢" }, 403);
  } catch {
    return json({ error: "未授權" }, 401);
  }

  try {
    const { term, direction = "cn2tw" } = await req.json();
    if (!term || typeof term !== "string") return json({ error: "缺少 term" }, 400);

    const key = Deno.env.get("GEMINI_API_KEY");
    if (!key) return json({ error: "伺服器未設定 GEMINI_API_KEY" }, 500);

    const cn2tw = direction !== "tw2cn";
    const prompt = buildPrompt(term, cn2tw);

    const url =
      `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${key}`;
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.2,
          responseMimeType: "application/json",
          responseSchema: {
            type: "OBJECT",
            properties: {
              answer: { type: "STRING" },
              note: { type: "STRING" },
              confidence: { type: "STRING", enum: ["high", "medium", "low"] },
            },
            required: ["answer", "confidence"],
          },
        },
      }),
    });

    if (!resp.ok) {
      const t = await resp.text();
      return json({ error: `Gemini ${resp.status}: ${t.slice(0, 200)}` }, 502);
    }

    const data = await resp.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
    let parsed: { answer?: string; note?: string; confidence?: string };
    try {
      parsed = JSON.parse(text);
    } catch {
      return json({ error: "AI 回傳格式異常", raw: text.slice(0, 200) }, 502);
    }

    const out = cn2tw
      ? { tw: parsed.answer ?? "", cn: term, note: parsed.note ?? "", confidence: parsed.confidence, source: "AI（Gemini）" }
      : { tw: term, cn: parsed.answer ?? "", note: parsed.note ?? "", confidence: parsed.confidence, source: "AI（Gemini）" };
    return json(out, 200);
  } catch (e) {
    return json({ error: String(e) }, 500);
  }
});

function buildPrompt(term: string, cn2tw: boolean): string {
  if (cn2tw) {
    return `你是臺灣繁體中文的用語專家。使用者給你一個「中國大陸慣用語」,請判斷臺灣人日常習慣的對應說法。
規則:
1. 只用臺灣繁體中文,嚴禁簡體字與中國用語。
2. 若這個詞臺灣本來就通用,answer 填臺灣的說法並在 note 說明「兩岸通用」。
3. 若是同字不同義的陷阱詞(例如 土豆、質量、窩心、視頻),務必在 note 點出差異。
4. 不確定時 confidence 填 low,note 誠實說明不確定,不要編造。
5. answer 只放最主要的臺灣對應說法(可用 / 分隔 2~3 個),不要整句解釋。
中國用語:「${term}」`;
  }
  return `你是臺灣與中國用語對照專家。使用者給你一個「臺灣慣用語」,請判斷中國大陸對應的常用說法。
規則:
1. answer 放中國大陸的說法。
2. 若兩岸通用,note 說明。
3. 不確定時 confidence 填 low 並誠實說明,不要編造。
4. answer 只放主要說法(可用 / 分隔),不要整句解釋。
臺灣用語:「${term}」`;
}

// JWT payload 是 base64url(-_ 取代 +/、且省略 padding),atob 只吃標準 base64,
// 需先換回 +/ 並補足 = padding,否則含 -_ 的合法 token 會解碼失敗被誤判未授權。
function decodeJwtPayload(jwt: string): string {
  const seg = jwt.split(".")[1] ?? "";
  const b64 = seg.replace(/-/g, "+").replace(/_/g, "/")
    .padEnd(Math.ceil(seg.length / 4) * 4, "=");
  return atob(b64);
}

function json(obj: unknown, status = 200): Response {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}
