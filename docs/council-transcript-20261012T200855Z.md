# Council Transcript — TinyFish Builder Challenge project decision

**Convened:** 2026-10-12 · **Topic:** What single project should Jay build for the Hack in Hills '26 TinyFish Builder Challenge?

---

## Step 1 — Deep Research Dossier

**What the challenge is.** A side challenge run by TinyFish (an enterprise web-agent infrastructure startup) for HIH'26. Optional, separate from the main HIH submission. Steps: sign up via a referral link for $8 free credits; connect TinyFish to a supported AI assistant (ChatGPT/Claude/Grok/Codex/Cursor/OpenCode); complete a "first successful run"; screenshot the dashboard; follow @Tiny_Fish and @HackInHills on X; post on X and LinkedIn; submit a Google Form with the screenshot and both post URLs. Stated builder goals: agents that interact with websites; automated research; browsing/workflow automation; web-connected assistants; real-world automation. Participants may explore TinyFish standalone or inside their HIH project.

**What TinyFish is** (verified against official docs): Search (free, up to 12,000 req/day), Fetch (free — a URL to clean markdown/JSON/HTML via a real browser), Agent (metered ~$0.016 per agent step — give a URL plus a natural-language "goal", it drives a real browser and returns structured JSON), Browser (metered — rent a cloud browser, drive it with your own Playwright/CDP), Monitor (~$0.005 per run — scheduled page/topic change detection with webhook/email delivery). Auth: `X-API-Key` header for REST, OAuth 2.1 for MCP. Integrations: MCP server at `https://agent.tinyfish.ai/mcp`; one-tap plugins for ChatGPT/Claude/Grok; n8n and Dify nodes; an npm CLI; a Python SDK. `output_schema` (JSON Schema) shapes results. Built-in stealth and rotating proxies at no extra cost, marketed as handling Cloudflare/DataDome-protected sites. TinyFish also runs a free Student Program and Ambassador Program with a monthly Bounty Board (pay per approved build, published work under the builder's name), and larger hackathons with real prizes ($5k–7.5k API credits, hardware, and a "Golden Ticket" to a 9-week accelerator with a path to $2M seed).

**Evidence of saturation.** TinyFish's own open-source cookbook ships ~30 examples. A large cluster are near-identical "fire N parallel browser agents at N site variants and stream prices back": pharmacy-panic (5 pharmacies), openbox-deals (8 retailers), lego-hunter, competitor-analysis (pricing), restaurant-comparison, district-rent-shark (rentals), waifu-deal-sniper (Discord anime figures), scholarship-finder, tenders-finder, stay-scout-hub (hotels), logistics-sentry, silicon-signal (semiconductor distributors), research-sentry (8 academic portals). A community TinyFish hackathon repo built "TinyPhish" (URL phishing detection). Conclusion: "parallel scraper + LLM summary" is thoroughly done.

**Jay's existing assets.** A finished main HIH'26 project, `arb-bound`: a Python engine testing whether cross-contract MCX gold spreads (GOLDGUINEA/GOLDM/GOLDPETAL/GOLDTEN) are arbitrageable. Real MCX bhavcopy data, a structural cost bound built from published contract specs, walk-forward testing with the centring scalar fitted on train only, regime-break detection with a volume signature, `analysis.attribute_break` (which leg moved and whether it moved with the complex), a live in-browser Pyodide playground, a generated PPTX deck, 73 tests, deployed on GitHub Pages and Vercel. Hard-won fact: MCX (mcxindia.com) returns HTTP 403 / Akamai Access Denied to datacenter IPs. Data was obtained only through a read-proxy (r.jina.ai), and the MCX circular-archive endpoint — a JS-driven listing — was not reachable at all; a research question was closed only by finding an alternate mirror. TinyFish markets its Fetch/Agent/Browser precisely as "works on bot-protected sites; built-in stealth and rotating proxies."

**Candidates.** A = a TinyFish layer that fetches live MCX bhavcopy and circulars behind the block and feeds the existing engine (judge supplies a date, sees real fetched data and a real verdict). B = a TinyFish Monitor watching MCX/SEBI circulars for contract-spec changes. C = a spread terminal using web search for spot/premium context plus fetches. D = a standalone unrelated idea. E = minimal compliance only (the required first run, screenshot, posts, form).

---

## Step 2 — Advisor Responses

### Advisor A — The Contrarian / Red Team

> **Verdict: do E, plus a one-day, budget-gated spike. Do not ship A, B, or C as your submission.**
>
> What's actually graded: the first successful run, the screenshot, the X/LinkedIn posts, the form. That's it. A, B, C spend real hours on an artifact the rubric barely touches. That's the first hidden cost: sunk effort with near-zero marginal grade.
>
> Where each candidate dies: **A (Live MCX)** bets the entire demo on a marketing claim you have never validated — that TinyFish's stealth beats Akamai when r.jina.ai and your own machine both failed. If MCX 403s the agent, your live demo collapses in the room, on the one thing you advertised. You also have $8 of credits and agent steps cost ~$0.016 each; a browser agent retrying a blocked page burns budget fast with nothing to show. **B (Monitor)** — its entire payoff is a change event. If no circular changes during judging there is literally nothing to demo, and the specific JS-driven circular-archive listing was the one MCX endpoint you couldn't reach at all. You're monitoring a door you've never opened. **C** — more surface area, more blocked sources, and it collapses into the exact "fire parallel fetches + LLM summary" pattern TinyFish's own ~30-example cookbook already saturates. Derivative *and* fragile. **D** discards arb-bound's only real moat. **E** is compliance-satisfying but forfeits the bounty upside for zero marginal cost saved.
>
> **The move:** hit E's requirements, then run **one** cheap spike — can TinyFish Agent actually fetch MCX bhavcopy through the block? Cap the spend. If yes, you have the room's only non-derivative story at ≤ a day's cost. If no, you still won compliance and learned the stealth claim is marketing. Never let an unverified vendor claim be load-bearing on demo day.

### Advisor B — The First Principles Thinker

> **What the challenge actually rewards.** Strip the "builder goals" list — it's aspiration, not grading. The graded artifact is: one successful run, a screenshot, posts, a form. The real payoff is credits plus a demoable first run. It does not reward a product. Any framing that treats this as a product competition is a category error.
>
> **The premise is a just-so story.** Value comes from removing a real constraint. Jay's constraint — MCX 403/Akamai — is real. But TinyFish Fetch/Browser is, mechanically, another read-proxy. He already solved this with r.jina.ai. Swapping proxies is vendor substitution, not new capability. Worse: the challenge's payoff doesn't depend on arb-bound succeeding at all, so bolting ingestion onto a finished 73-test engine risks degrading real work to win nothing.
>
> **The irreducible core.** TinyFish's differentiated primitives are exactly two: **Agent** and **Monitor**. Fetch and Search are commodity. Only Monitor produces signal arb-bound structurally *cannot* have: *temporal* data — contract-spec and circular changes over time. That's capability added, not a proxy traded.
>
> **Minimum honest work.** One Monitor wired to MCX/SEBI circulars, emitting one field into the engine, one real first run, screenshot, post. Reject E (empty compliance — wastes the $8, teaches nothing) and A (proxy substitution cosplaying as innovation).

### Advisor C — The Expansionist / Strategist

> **The move everyone underestimates: A, but reframed as a capability proof, not a scraper.**
>
> Thirty cookbooks already do "N parallel agents scrape N sites." That space is dead. What nobody in TinyFish's community has shown is the thing TinyFish's *enterprise* future depends on: **stealth Fetch/Agent defeating Akamai-class bot defence on a real, regulated, high-value source.** Jay's 403 is not an obstacle — it's the *demo*.
>
> Anchor to his existing rigor (73 tests, walk-forward) so it reads as infrastructure. Then compound: **TinyFish's own GTM needs this artifact** — a regulated-source win is exactly what they publish "under your name." That's a portfolio piece on *their* distribution. **Funnel, don't apply:** Student Program → Bounty Board → Ambassador → accelerator Golden Ticket. **Reusable wedge:** candidate A's ingestion layer becomes the substrate for B and any future blocked-source agent — a data plane, not a one-off. A+B = a vertical. **Compounds the main HIH entry** — one engine, two prize shots.
>
> Where everyone thinks too small: they're optimizing a form submission. Jay should be claiming a **position** — *the builder who unblocks regulated data with TinyFish.* That positioning outlives the hackathon and is what the accelerator funds.

### Advisor D — The Outsider / Domain Skeptic

> **The 15-second test: gold arbitrage fails, hard.** Say "arb-bound" out loud to a stranger. Then "GOLDGUINEA / GOLDM / GOLDPETAL / GOLDTEN." They are gone. Four opaque tickers, a structural cost bound, walk-forward testing, regime-break detection — that's a *resume*, not a pitch. Zero-knowledge me cannot tell whether arb-bound is a serious quant tool or a clever student exercise, and I have no reason to care.
>
> But buried in the dossier is something a stranger *does* instantly get: **"the website blocked me."** Everyone understands a site that bans robots. That is the universal, legible, human story — and it happens to be exactly what TinyFish sells. The dossier records that MCX returns 403/Akamai and Jay *could not reach the circular archive at all*. That pain is the product. The arbitrage is the excuse.
>
> So: **A is the right raw material, mis-sold.** Reframe it as "I pointed TinyFish at a site that bans robots, and it just worked — here's the live verdict." The verdict is the punchline; the *unblocking* is the pitch. **B is more legible but generic.** The non-generic, legible intersection: blocked public-interest site + "the rules quietly changed."
>
> Verdict: legible **only** if reframed around the block. Keep MCX as the arena, not the story. If TinyFish judges see 403 → unblocked → alert, they'll care in 15 seconds. If they see arbitrage, they'll scroll.

### Advisor E — The Executor / Pragmatic Engineer

> **The take: ship E as insurance, then gate everything on one Fetch call.**
>
> The make-or-break is a 30-minute test, not a project. MCX 403'd Jay because of Akamai on datacenter IPs. TinyFish's pitch is stealth + rotating proxies. So the strategy reduces to: *does TinyFish fetch a live MCX bhavcopy where curl got 403?* Test that before writing any UI.
>
> **A (Live MCX ingestion)** — Hour 0–0.5 (Jay): referral signup, X-API-Key, OAuth MCP. Hour 0.5–1.5: Fetch a bhavcopy URL + one circular PDF. Confirm 200 + clean bytes. **Use Fetch (free), not Agent ($0.016/step) — $8 is only ~500 agent steps.** Hour 1.5–3: thin adapter, fetch → parse CSV (reuse arb-bound's pandas parsing + 73 tests) → call the engine CLI. TTFWD ≈ 2h. Hour 4–5: judge-date → fetch → live verdict page. Maintenance tax: low. Live-demo probability: ~70%, gated entirely on step 2.
>
> **B (ContractSpec Monitor).** TTFWD 3h. Reliability ~85%, but low wow. Good fallback. **C.** TTFWD 4h, Tax: high. Live ~60%.
>
> **E (Minimal compliance).** 30 min: connect, one run, screenshot, posts, form. Live ~99%. Do it *first* as insurance — it guarantees the challenge is satisfied no matter what.
>
> **Failure points:** the bhavcopy is a zip/CSV, not HTML — Fetch returns markdown, so you may need Browser/Playwright; the circular *archive* may still be walled; don't fan out agents and blow the budget.
>
> **Sequence:** E (30m) → A-gate (1h) → build A if green, else B.

---

## Step 3 — Anonymous Peer Review

Reviewers saw the five responses anonymised as A–E.

### Reviewer 1

1. **Strongest — B.** It correctly separates commodity (Search/Fetch are just another read-proxy, which Jay already solved) from the only structural capability gaps: Agent and Monitor. Its irreducible core is the only proposal that adds something arb-bound lacks rather than re-skinned scraping.
2. **Fatal blind spot — C.** It assumes vendor marketing equals capability, and that TinyFish's GTM will actually surface Jay — a load-bearing dependency entirely outside his control. Equally blind: all five treat MCX archive availability as the crux but nobody verified the *artifact* — the archive was "walled" to Jay even via proxy, so a green fetch test proves nothing about Monitor's actual payload.
3. **Missing — timebox asymmetry.** Every response designs a *project*; the rubric grades a *submission*. None prices the failure mode where the MCX block stays up and the one graded run never lands inside the $8 budget, leaving Jay with no screenshot at all. Cheap pre-flight verification of the dashboard-screenshot path itself outranks all five architectures.

### Reviewer 2

1. **Strongest — B.** Its just-so-story diagnosis is mechanically verifiable rather than vibes: Fetch/Browser is another read-proxy, and Jay already solved the 403. B is also the only response that separates commodity primitives from differentiated ones, which predicts which artifact scores.
2. **Fatal blind spot — C.** Assumes TinyFish stealth defeats Akamai on MCX — the exact unverified vendor claim A warns against — and makes it load-bearing not merely for a demo but for a claimed permanent "position." Compounding it: assumes the Student/Ambassador funnel exists and is open.
3. **Missing — legality and judge optics.** None asks whether circumventing Akamai to pull a regulated exchange's data sits inside MCX's terms, or what TinyFish's own judges make of a project whose central story is "I bypassed a bank/exchange's bot defence." On a hackathon run by that vendor, the 403 could read as a killer demo or as a red flag; nobody pressure-tests which. Relatedly, no one inspects TinyFish's actual capability surface — can Fetch even ingest a zipped bhavcopy? All five plans rest on an unexamined tool.

### Reviewer 3

1. **Strongest — E.** A owns the best single line but stops at rhetoric. E is the only response that treats the central uncertainty — *can TinyFish actually get past Akamai on MCX?* — as an empirical question and resolves it with a 30-minute gate before anyone commits. A falsifiable, cheaply-tested plan beats a confident assertion.
2. **Fatal blind spot — C, secondarily B.** C makes the whole thesis load-bearing on precisely the assumption Jay already falsified once: that a fetcher can reach MCX's circular archive. C then pitches it *publicly* to TinyFish's GTM. B wires its core to the same never-reached archive. Both are demo-day grenades.
3. **Missing — packaging.** The rubric grades four artifacts that aren't the build — dashboard screenshot, X posts, LinkedIn post, Google Form. Not one advisor allocated an hour, a capture plan, or a narrative to them. That is the cheapest points on the board, at zero vendor risk. Nobody named the ToS exposure of C's public evasion claim either.

---

## Step 4 — Chairman Synthesis

### Where the Council agrees (consensus, high confidence)

1. **The graded artifact is the submission package, not the code.** All five advisors converged independently. The rubric touches: first successful run, dashboard screenshot, X post, LinkedIn post, form.
2. **No vendor capability may be load-bearing until tested.** TinyFish's stealth claim is unverified against MCX. This is a hypothesis with a cheap test, not a premise.
3. **Search and Fetch are commodity.** The differentiated primitives are Agent and Monitor. Fetch is effectively another read-proxy, and Jay already solved his access problem with r.jina.ai — so "TinyFish fixed my 403" is vendor substitution, not new capability.
4. **The compliance package must be banked first, at zero risk.** A 30-minute, ~99%-reliable step that satisfies the entire graded rubric should never be gambled behind a build.

### Where the Council clashes (contested)

- **A vs B.** Contrarian and First Principles reject A as proxy substitution cosplaying as innovation and put Monitor at the core. Expansionist and Outsider say A, reframed around the block, is the maximum leverage. Resolution: both are right about different things — B is the more *durable* capability, A is the more *legible* story — and the honest synthesis is to build A's plumbing, make B its payload, and gate both.
- **E as floor vs E as waste.** Executor and Contrarian: do it first, it's insurance. First Principles: it's empty compliance. Resolution: the Executor wins on expected value — E costs 30 minutes and removes all downside; the philosophical objection costs real points if ignored.

### Blind spots caught in peer review (the value the review round added)

1. **Optics and terms-of-service exposure.** Nobody priced what it means for a *sponsor's judges* to hear a pitch about circumventing a regulated exchange's bot defence. The 403 is a great story about *the problem*, and a poor story if framed as *the achievement*. Framing rule: MCX is the arena, not the pitch.
2. **Packaging budget.** Nobody allocated time to the screenshot, the post copy, or the form — the cheapest points on the board, at zero vendor risk. Now it is Phase 0.
3. **Artifact unverifiability.** A green fetch test on a bhavcopy proves nothing about the circular *archive*, which was the thing never reached. Hence four separate gate checks (G1–G4), each with its own pass criterion.

### The recommendation

**Complete the challenge compliance package in the first hour — it is the graded artifact. Then build a TinyFish-backed live-data plane for `arb-bound`, but only after a free, capped 30-minute gate.**

Concretely:
- **Phase 0 (60 min, zero risk, free):** every manual challenge step. Banks the rubric.
- **Phase 1 (30–45 min, free):** four gate checks G1–G4, using Fetch not Agent.
- **Phase 2 (5 min):** scope to green. Full plane if G1–G4 pass; bhavcopy-only if the archive stays walled; documented negative result if everything fails.
- **Phase 3 (2–3 h, only if green):** thin plane → existing engine → `/scan?date=` endpoint.
- **Phase 4 (30 min):** publish the gate result honestly, including failures.

The engineering invariant that makes this safe to attach to a finished project: **zero new domain logic.** The engine and its 73 tests are untouched. If the web layer fails, the project degrades to exactly what it is today and nothing breaks.

### The immediate next step

**Action:** Click the official HIH referral link, create the TinyFish account, create the API key, and store it in `arb-bound/.env`. That single step unlocks Phase 0, Phase 1, and any decision — and it is the only step that cannot be done for you.

---

## Research sources consulted

- `https://docs.tinyfish.ai/llms.txt` and the individual docs pages (Goooals, Structured Output, Search API, Fetch API, Agent API, Browser API, Monitor, MCP, CLI, Plugins, Common Patterns, Anti-Bot Guide, FAQ, Authentication)
- `https://www.tinyfish.ai/`, `https://tinyfish.hackinhills.com`, `https://agent.tinyfish.ai/examples`
- `github.com/tinyfish-io/tinyfish-cookbook` (cloned; ~30 example READMEs read)
- `github.com/JabrielHo/TinyFish-Hackathon-BigFish` (community TinyFish hackathon submission)
- `github.com/tinyfish-io/tinyfish-mcp-server`, `tinyfish-web-agent-integrations`, `bigset-oss`
- TinyFish Student Program / Ambassador Program blog posts
- YouTube survey via yt-dlp (12+ official TinyFish videos: Enterprise Web Agent, TinyFish in ChatGPT, Monitor, Live Browser Preview, Grubhub/DoorDash case studies)
- Third-party reviews: The Metaverse Guy (TinyFish vs Playwright/Firecrawl/BrowserBase), Daniel Tech & Data review, testingcatalog coverage of the community programs
