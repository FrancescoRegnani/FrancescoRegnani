// Jarvis - assistente personale vocale.
// Riceve una domanda (dal Comando Rapido di Siri), interroga Claude
// e restituisce una risposta breve in testo semplice, pronta da leggere a voce.
//
// Segreti richiesti (Supabase > Edge Functions > Secrets):
//   ANTHROPIC_API_KEY  chiave API di Claude
//   JARVIS_TOKEN       password lunga e casuale che solo il tuo Comando Rapido conosce
// Opzionali:
//   JARVIS_MODEL       modello Claude (predefinito: claude-haiku-5-5, veloce ed economico;
//                      claude-opus-5-5 per risposte più ragionate)
//   JARVIS_EFFORT      low | medium | high (predefinito: low, per risposte veloci)
// SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY sono forniti automaticamente da Supabase.

import Anthropic from "npm:@anthropic-ai/sdk@1.8.0";
import { createClient } from "npm:@supabase/supabase-js@2.119.0";

const MODEL = Deno.env.get("JARVIS_MODEL") ?? "claude-haiku-5-5";
// Haiku usa la ricerca web di base e non ha il "paracadute" lato server per i rifiuti.
const IS_HAIKU = MODEL.startsWith("claude-haiku");
const EFFORT = (Deno.env.get("JARVIS_EFFORT") ?? "low") as "low" | "medium" | "high";
const JARVIS_TOKEN = Deno.env.get("JARVIS_TOKEN") ?? "";
const TIME_ZONE = "Europe/Rome";

// Quanto indietro guardare per dare continuità alla conversazione.
const HISTORY_WINDOW_MINUTES = 20;
const HISTORY_MAX_MESSAGES = 12;
const MAX_LOOP_ITERATIONS = 6;
const MAX_INPUT_CHARS = 4000;

// Creato al primo uso, così la funzione parte anche prima che la chiave sia impostata.
let anthropicClient: Anthropic | null = null;
const claude = () => (anthropicClient ??= new Anthropic()); // legge ANTHROPIC_API_KEY
const db = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  { auth: { persistSession: false } },
);

const SYSTEM_PROMPT = `Sei Jarvis, l'assistente personale del tuo utente. Parli in italiano.

Il tuo utente ti usa soprattutto a voce, tramite Siri su Apple Watch, iPhone o AirPods: la tua risposta verrà letta ad alta voce.
Quindi:
- Rispondi in modo breve e diretto: di norma una-tre frasi. Vai più a fondo solo se te lo chiede.
- Scrivi testo semplice, pronto da pronunciare: niente markdown, elenchi puntati, emoji, tabelle o link.
- Scrivi numeri, date e importi come si dicono a voce quando aiuta la comprensione.
- Se la richiesta è ambigua, fai una sola domanda breve per chiarire.

Memoria:
- Nella sezione "Cose che sai sull'utente" trovi i ricordi salvati in passato. Usali per personalizzare le risposte.
- Quando l'utente ti chiede di ricordare qualcosa, o ti dice un fatto stabile e utile su di sé (lavoro, preferenze, persone importanti, abitudini), salvalo con lo strumento salva_ricordo e conferma in poche parole.
- Se ti chiede di dimenticare qualcosa, usa elimina_ricordo.
- Non salvare password, codici, dati bancari o dati sanitari.

Informazioni aggiornate:
- Per fatti recenti, notizie, meteo, orari o qualsiasi cosa che può essere cambiata, usa la ricerca web invece di andare a memoria.

Su questioni fiscali, legali o di lavoro sii prudente: dai l'indicazione essenziale e, se la risposta richiede verifica su fonti ufficiali, dillo chiaramente.`;

const TOOLS: Anthropic.Beta.BetaToolUnion[] = [
  {
    name: "salva_ricordo",
    description:
      "Salva nella memoria a lungo termine un fatto utile sull'utente (preferenze, lavoro, persone, abitudini). Scrivi il fatto come una frase breve e autonoma, in terza persona.",
    input_schema: {
      type: "object",
      properties: {
        contenuto: { type: "string", description: "Il fatto da ricordare, massimo 300 caratteri." },
      },
      required: ["contenuto"],
      additionalProperties: false,
    },
    strict: true,
  },
  {
    name: "elimina_ricordo",
    description: "Elimina dalla memoria un ricordo, indicato dal suo numero (id) nella sezione dei ricordi.",
    input_schema: {
      type: "object",
      properties: {
        id: { type: "integer", description: "Il numero del ricordo da eliminare." },
      },
      required: ["id"],
      additionalProperties: false,
    },
    strict: true,
  },
  {
    type: IS_HAIKU ? "web_search_20250305" : "web_search_20260209",
    name: "web_search",
    max_uses: 3,
    user_location: { type: "approximate", country: "IT", timezone: TIME_ZONE },
  },
];

function textResponse(body: string, status = 200): Response {
  return new Response(body, {
    status,
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}

// Confronto a tempo costante, per non rivelare il token tramite i tempi di risposta.
function safeEqual(a: string, b: string): boolean {
  const enc = new TextEncoder();
  const x = enc.encode(a);
  const y = enc.encode(b);
  let diff = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) {
    diff |= (x[i] ?? 0) ^ (y[i] ?? 0);
  }
  return diff === 0;
}

async function readQuestion(req: Request): Promise<string> {
  const raw = await req.text();
  const contentType = req.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    try {
      const body = JSON.parse(raw);
      return String(body.testo ?? body.text ?? body.domanda ?? "").trim();
    } catch {
      return "";
    }
  }
  return raw.trim();
}

async function loadMemories(): Promise<string> {
  const { data, error } = await db
    .from("jarvis_memories")
    .select("id, content")
    .order("id", { ascending: true });
  if (error) throw new Error(`Lettura ricordi: ${error.message}`);
  if (!data || data.length === 0) return "Nessun ricordo salvato finora.";
  return data.map((m) => `[${m.id}] ${m.content}`).join("\n");
}

async function loadRecentHistory(): Promise<Anthropic.Beta.BetaMessageParam[]> {
  const since = new Date(Date.now() - HISTORY_WINDOW_MINUTES * 60_000).toISOString();
  const { data, error } = await db
    .from("jarvis_messages")
    .select("role, content")
    .gte("created_at", since)
    .order("id", { ascending: false })
    .limit(HISTORY_MAX_MESSAGES);
  if (error) throw new Error(`Lettura cronologia: ${error.message}`);
  const rows = (data ?? []).reverse();
  // La cronologia deve iniziare con un messaggio dell'utente e alternare i ruoli.
  const history: Anthropic.Beta.BetaMessageParam[] = [];
  for (const row of rows) {
    const role = row.role as "user" | "assistant";
    if (history.length === 0 && role !== "user") continue;
    if (history.length > 0 && history[history.length - 1].role === role) continue;
    history.push({ role, content: row.content });
  }
  if (history.length > 0 && history[history.length - 1].role === "user") history.pop();
  return history;
}

async function saveExchange(question: string, answer: string): Promise<void> {
  const { error } = await db.from("jarvis_messages").insert([
    { role: "user", content: question },
    { role: "assistant", content: answer },
  ]);
  if (error) console.error("Salvataggio cronologia:", error.message);
}

async function runTool(name: string, input: unknown): Promise<{ content: string; isError: boolean }> {
  const args = (input ?? {}) as Record<string, unknown>;
  if (name === "salva_ricordo") {
    const contenuto = typeof args.contenuto === "string" ? args.contenuto.trim().slice(0, 300) : "";
    if (!contenuto) return { content: "Contenuto mancante.", isError: true };
    const { data, error } = await db.from("jarvis_memories").insert({ content: contenuto }).select("id").single();
    if (error) return { content: `Errore nel salvataggio: ${error.message}`, isError: true };
    return { content: `Ricordo salvato con id ${data.id}.`, isError: false };
  }
  if (name === "elimina_ricordo") {
    const id = Number(args.id);
    if (!Number.isInteger(id)) return { content: "Id non valido.", isError: true };
    const { data, error } = await db.from("jarvis_memories").delete().eq("id", id).select("id");
    if (error) return { content: `Errore nell'eliminazione: ${error.message}`, isError: true };
    if (!data || data.length === 0) return { content: `Nessun ricordo con id ${id}.`, isError: true };
    return { content: `Ricordo ${id} eliminato.`, isError: false };
  }
  return { content: `Strumento sconosciuto: ${name}`, isError: true };
}

function extractText(message: Anthropic.Beta.BetaMessage): string {
  return message.content
    .filter((b): b is Anthropic.Beta.BetaTextBlock => b.type === "text")
    .map((b) => b.text)
    .join("")
    .trim();
}

async function askJarvis(question: string): Promise<string> {
  const [memories, history] = await Promise.all([loadMemories(), loadRecentHistory()]);

  const now = new Intl.DateTimeFormat("it-IT", {
    timeZone: TIME_ZONE,
    dateStyle: "full",
    timeStyle: "short",
  }).format(new Date());

  const messages: Anthropic.Beta.BetaMessageParam[] = [
    ...history,
    { role: "user", content: question },
  ];

  for (let i = 0; i < MAX_LOOP_ITERATIONS; i++) {
    const response = await claude().beta.messages.create({
      model: MODEL,
      max_tokens: 4000,
      // Se il modello principale rifiuta, Anthropic riprova con un modello alternativo.
      ...(IS_HAIKU ? {} : { betas: ["server-side-fallback-2026-07-01"], fallbacks: "default" as const }),
      output_config: { effort: EFFORT },
      system: [
        // Parte fissa: messa in cache per risparmiare su ogni richiesta.
        { type: "text", text: SYSTEM_PROMPT, cache_control: { type: "ephemeral" } },
        // Parte variabile: ricordi e data/ora correnti.
        { type: "text", text: `Cose che sai sull'utente:\n${memories}\n\nData e ora attuali (${TIME_ZONE}): ${now}.` },
      ],
      tools: TOOLS,
      messages,
    });

    switch (response.stop_reason) {
      case "refusal":
        return "Mi dispiace, su questo non posso aiutarti.";
      case "pause_turn":
        // Una ricerca web lunga si è fermata: la rimandiamo indietro perché continui.
        messages.push({ role: "assistant", content: response.content });
        continue;
      case "tool_use": {
        messages.push({ role: "assistant", content: response.content });
        const results: Anthropic.Beta.BetaToolResultBlockParam[] = [];
        for (const block of response.content) {
          if (block.type !== "tool_use") continue;
          const { content, isError } = await runTool(block.name, block.input);
          results.push({ type: "tool_result", tool_use_id: block.id, content, is_error: isError });
        }
        messages.push({ role: "user", content: results });
        continue;
      }
      default: {
        const text = extractText(response);
        return text || "Non ho una risposta, puoi riformulare?";
      }
    }
  }
  return "Ci sto mettendo troppo, riprova con una domanda più semplice.";
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return textResponse("Usa una richiesta POST.", 405);

  if (!JARVIS_TOKEN) return textResponse("Jarvis non è configurato: manca JARVIS_TOKEN.", 500);
  const token = req.headers.get("x-jarvis-token") ?? "";
  if (!safeEqual(token, JARVIS_TOKEN)) return textResponse("Non autorizzato.", 401);

  const question = (await readQuestion(req)).slice(0, MAX_INPUT_CHARS);
  if (!question) return textResponse("Non ho sentito nessuna domanda.", 400);

  if (!Deno.env.get("ANTHROPIC_API_KEY")) {
    return textResponse("Jarvis non è configurato: manca ANTHROPIC_API_KEY.", 500);
  }

  try {
    const answer = await askJarvis(question);
    await saveExchange(question, answer);
    return textResponse(answer);
  } catch (err) {
    console.error(err);
    if (err instanceof Anthropic.RateLimitError) {
      return textResponse("Sono sovraccarico in questo momento, riprova tra poco.", 503);
    }
    if (err instanceof Anthropic.AuthenticationError) {
      return textResponse("La chiave di Claude non è valida: controlla ANTHROPIC_API_KEY.", 500);
    }
    if (err instanceof Anthropic.APIConnectionError) {
      return textResponse("Non riesco a raggiungere Claude, riprova tra poco.", 503);
    }
    return textResponse("Si è verificato un errore, riprova tra poco.", 500);
  }
});
