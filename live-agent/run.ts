/**
 * Live skill harness for the Business Skill Kit.
 *
 * Uses the GitHub Copilot SDK (@github/copilot-sdk) to drive the REAL Microsoft
 * Dataverse MCP server against one or more Dataverse orgs. You sign in interactively
 * (MSAL browser flow) the first time each org is contacted, which is what makes
 * cross-tenant testing work where a single az token could not.
 *
 * For each org, it runs the per-skill scenarios in scenarios.json and records a
 * PASS / FAIL / NA matrix. Read scenarios only query; write scenarios create a
 * uniquely tagged test record and then delete it (writes were explicitly enabled).
 *
 * Nothing here commits real org URLs, GUIDs, tenant ids, or row data: orgs live in
 * the gitignored orgs.json, and reports/ is gitignored.
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { CopilotClient, approveAll } from "@github/copilot-sdk";

const __dirname = dirname(fileURLToPath(import.meta.url));

// The Dataverse MCP server is a remote HTTP endpoint at <org>/api/mcp (GA) or
// <org>/api/mcp_preview (preview). It uses interactive OAuth (auth-code + PKCE) and
// only accepts tokens from client apps on the environment's approved MCP client list,
// so the SDK drives a browser sign-in. Nothing is stored or committed.
const MCP_PATH = process.env.DATAVERSE_MCP_PATH || "/api/mcp";

type Org = { label: string; url: string; tenantId?: string };
type Scenario = {
  slug: string;
  domain: string;
  mode: "read" | "write" | "scaffold" | "fixture-only";
  requires: string[];
  prompt: string;
};

function loadJson<T>(p: string): T {
  return JSON.parse(readFileSync(p, "utf8")) as T;
}

function parseArgs(argv: string[]) {
  const out: { orgs?: string; only?: string; mode?: string; noWrite?: boolean; model?: string } = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--orgs") out.orgs = argv[++i];
    else if (a === "--only") out.only = argv[++i]; // comma list of slugs
    else if (a === "--mode") out.mode = argv[++i]; // read|write|all (default read)
    else if (a === "--no-write") out.noWrite = true;
    else if (a === "--model") out.model = argv[++i];
  }
  return out;
}

const RESULT_RE = /RESULT:\s*(PASS|FAIL|NA)\b/i;

function judge(text: string): { verdict: "PASS" | "FAIL" | "NA" | "?"; reason: string } {
  const m = text.match(RESULT_RE);
  if (!m) return { verdict: "?", reason: "no RESULT token in reply" };
  const verdict = m[1].toUpperCase() as "PASS" | "FAIL" | "NA";
  const after = text.slice(m.index! + m[0].length).replace(/^[\s:.-]+/, "").split("\n")[0].trim();
  return { verdict, reason: after.slice(0, 160) };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const orgsPath = args.orgs || join(__dirname, "orgs.json");
  if (!existsSync(orgsPath)) {
    console.error(`No orgs file at ${orgsPath}. Copy orgs.example.json to orgs.json and fill in your orgs.`);
    process.exit(2);
  }

  const orgs = loadJson<Org[]>(orgsPath);
  const spec = loadJson<{ tag: string; scenarios: Scenario[] }>(join(__dirname, "scenarios.json"));

  const wantMode = (args.mode || "read").toLowerCase(); // default read-only for safety
  let scenarios = spec.scenarios;
  if (args.only) {
    const set = new Set(args.only.split(",").map((s) => s.trim()));
    scenarios = scenarios.filter((s) => set.has(s.slug));
  }
  if (wantMode === "read") scenarios = scenarios.filter((s) => s.mode !== "write");
  if (args.noWrite) scenarios = scenarios.filter((s) => s.mode !== "write");

  const model = args.model || "auto";
  const results: Record<string, Record<string, { verdict: string; reason: string }>> = {};

  const client = new CopilotClient();
  await client.start();

  try {
    for (const org of orgs) {
      console.log(`\n=== Org: ${org.label} (${org.url}) ===`);
      console.log(`Connecting to Dataverse MCP at ${org.url}${MCP_PATH}. If prompted, complete the browser sign-in for this org.`);
      results[org.label] = {};

      const orgResource = org.url.replace(/\/+$/, "");
      // The Dataverse MCP endpoint uses interactive OAuth (auth-code + PKCE) as an
      // APPROVED client app; a raw az/pac token (Azure CLI app id) is rejected with 403.
      // So we let the SDK/runtime drive the browser sign-in. Advanced override: set
      // DATAVERSE_MCP_BEARER to a token minted by an approved client to skip the prompt.
      const bearer = process.env.DATAVERSE_MCP_BEARER;
      const session = await client.createSession({
        model,
        onPermissionRequest: approveAll, // writes were explicitly enabled by the user
        mcpOAuthTokenStorage: "persistent", // cache the browser sign-in per org across runs
        mcpServers: {
          dataverse: {
            type: "http",
            url: orgResource + MCP_PATH,
            ...(bearer ? { headers: { Authorization: "Bearer " + bearer } } : {}),
            tools: ["*"],
          },
        },
      });

      for (const sc of scenarios) {
        const contract =
          `\n\nRules: use ONLY the 'dataverse' MCP tools. If a required table/entity does not exist on THIS org, ` +
          `finish with a line 'RESULT: NA' and a short reason. If the scenario's operations succeed, finish with ` +
          `'RESULT: PASS' and a one-line reason. If they fail, finish with 'RESULT: FAIL' and the error. ` +
          `Any test records you create must include the tag '${spec.tag}' in a name/subject and be deleted before you finish.`;
        const prompt = `[skill: ${sc.domain}/${sc.slug} | mode: ${sc.mode}] ${sc.prompt}${contract}`;

        process.stdout.write(`  - ${sc.domain}/${sc.slug} ... `);
        try {
          const resp = await session.sendAndWait({ prompt });
          const text = (resp?.data as any)?.content ?? "";
          const j = judge(String(text));
          results[org.label][sc.slug] = j;
          console.log(j.verdict + (j.reason ? ` (${j.reason})` : ""));
        } catch (e: any) {
          results[org.label][sc.slug] = { verdict: "ERR", reason: String(e?.message || e).slice(0, 160) };
          console.log("ERR " + String(e?.message || e).slice(0, 120));
        }
      }

      await session.disconnect?.();
    }
  } finally {
    await client.stop();
  }

  // Report
  const slugs = scenarios.map((s) => s.slug);
  const labels = orgs.map((o) => o.label);
  const w = Math.max(20, ...slugs.map((s) => s.length + 2));
  let table = "skill".padEnd(w) + labels.map((l) => l.padEnd(10)).join("") + "\n";
  table += "-".repeat(w + labels.length * 10) + "\n";
  for (const sc of scenarios) {
    let row = `${sc.domain}/${sc.slug}`.padEnd(w);
    for (const l of labels) row += (results[l]?.[sc.slug]?.verdict || "-").padEnd(10);
    table += row + "\n";
  }
  console.log("\n" + table);

  mkdirSync(join(__dirname, "reports"), { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  writeFileSync(join(__dirname, "reports", `matrix-${stamp}.json`), JSON.stringify({ mode: wantMode, results }, null, 2));
  writeFileSync(join(__dirname, "reports", `matrix-${stamp}.txt`), table);
  console.log(`Saved reports/matrix-${stamp}.{json,txt}`);
  process.exit(0);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
