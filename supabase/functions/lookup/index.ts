// Supabase Edge Function:lookup
// 用 Google Gemini 免費 API,給一個中國/臺灣用語,回傳對應說法的「建議草稿」。
// 金鑰放 Edge Function 密鑰 GEMINI_API_KEY(伺服器端保管,不進前端、不進 git)。
// 前端以 sb.functions.invoke("lookup", { body: { term, direction } }) 呼叫。

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

// 免費層可用模型;若某天此名稱失效,可換成 gemini-2.5-flash 等其他免費模型
const MODEL = "gemini-2.0-flash";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });

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

function json(obj: unknown, status = 200): Response {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { ...CORS, "Content-Type": "application/json" },
  });
}
