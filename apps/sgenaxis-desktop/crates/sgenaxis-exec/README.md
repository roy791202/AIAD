# sgenaxis-exec (PD-EXEC-CLI + PD-EXEC-MCP + PD-EXEC-BIND-01 + PD-EXEC-CANCEL-01 + PD-EXEC-SINGLE-01)

Agent Providers **A (CLI)** and **B (local MCP)** — shared `AgentPort` + `AgentChunk`.

Authority: `docs/PRODUCT-DEVELOPMENT.md` §6.2／§6.3.

| Piece | Role |
|-------|------|
| `require_run_binding` | PD-EXEC-BIND-01: reject missing root／work item／fingerprint |
| `AgentPort` | `start_run` / `poll_chunks` / `cancel` |
| `AgentChunk` | started／chunk／progress／exited／failed |
| `ExitClassification` | Success／Failure／Cancelled／Crashed（≠ 工項綠燈）；cancel → Cancelled；crash／負碼 → Crashed |
| Host reconcile | Dispatch `cancel_run`／exit poll releases WORK lease; same fingerprint cannot blind-re-run while lease active |
| `CliAgentSettings` | Claude／cursor-agent／Codex／Antigravity path+args |
| `McpAgentSettings` | endpoint／server name／approved tools (+ optional secret, not projected) |
| `McpSettingsProjection` | UI DTO — **no** secret values |
| `AgentSettingsDocument` | CLI＋MCP partitions (PD-SET-01) |
| `AgentSettingsProjection` | Combined UI DTO — secrets omitted |
| `HostSettingsStore` | Persist via PathPort config dir + FileSystemPort；`save_as_active` rejects invalid paths |
| `CliAgentAdapter` | DryRun by default; live = `real-spawn` + `live_approved` (stdout／stderr／exit／cancel) |
| `McpAgentAdapter` | DryRun by default; optional `real-mcp` via `McpClientPort` |
| `AgentRouter` | `start_run { Cli \| Mcp }` provider switch |
| Single-agent gate | PD-EXEC-SINGLE-01: `ExecError::Busy` while a run is active／undrained; after end／cancel only |

## DryRun CLI (default, safe)

```rust
use sgenaxis_adapters::FakeProcess;
use sgenaxis_exec::{AgentPort, CliAgentAdapter, StartRunRequest};

let mut agent = CliAgentAdapter::with_defaults(Box::new(FakeProcess::new()));
// Helpers include demo binding; production must pass real root／work item／fingerprint.
let run = agent.start_run(StartRunRequest::cli_dry_run())?;
let events = agent.poll_chunks(run)?;
// Started → Chunk → Progress → Exited(Success, 0)
```

## DryRun MCP (default, safe — no network)

```rust
use sgenaxis_exec::{AgentPort, McpAgentAdapter, StartRunRequest};

let mut agent = McpAgentAdapter::dry_defaults();
let run = agent.start_run(StartRunRequest::mcp_dry_run())?;
let events = agent.poll_chunks(run)?;
```

## Provider switch

```rust
use sgenaxis_adapters::FakeProcess;
use sgenaxis_exec::{AgentPort, AgentRouter, CliAgentAdapter, McpAgentAdapter, StubMcpClient, StartRunRequest};

let mut exec = AgentRouter::new(
    CliAgentAdapter::with_defaults(Box::new(FakeProcess::new())),
    McpAgentAdapter::with_defaults(Box::new(StubMcpClient)),
);
let a = exec.start_run(StartRunRequest::cli_dry_run())?;
// …drain…
let b = exec.start_run(StartRunRequest::mcp_dry_run())?;
```

## Live CLI (PD-EXEC-LIVE-01, opt-in)

Requires **both** feature `real-spawn` **and** approved settings (`CliAgentSettings::live_approved`,
mirrored from host `agent_active` via `HostSettings::make_cli_adapter`).

```rust
use sgenaxis_adapters::FakeProcess;
use sgenaxis_exec::{AgentPort, CliAgentAdapter, CliAgentSettings, StartRunRequest};

let mut settings = CliAgentSettings::defaults();
settings.live_approved = true;
let mut agent = CliAgentAdapter::new(settings, Box::new(FakeProcess::new()));
let run = agent.start_run(StartRunRequest::cli_live())?;
// poll_chunks → Started(dry_run:false) → Chunk(stdout/stderr) → Exited(exit_code)
// DryRun still works: StartRunRequest::cli_dry_run()
```

```powershell
cargo test -p sgenaxis-exec --features real-spawn
cargo test -p sgenaxis-exec --features real-mcp

# PD-LIVE-CLI-SMOKE-01 — real PATH CLI (claude｜cursor-agent｜codex｜…) start→chunk→exit
# Uses --version only. No CLI on PATH → test returns early (NOT RUN), does not fail.
cargo test -p sgenaxis-exec --features real-spawn --test live_cli_smoke -- --nocapture
# or: pytest tests/test_pd_live_cli_smoke_01.py -q

# PD-MCP-LIVE-SMOKE-01 — env-gated local MCP Live connect／tool (or NOT RUN)
# Set SGENAXIS_MCP_LIVE_ENDPOINT to an activatable local endpoint (not :8788／:8787).
# Unset／empty／reserved → early return (NOT RUN). Never forges Live PASS from DryRun.
cargo test -p sgenaxis-exec --features real-mcp --test live_mcp_smoke -- --nocapture
# or: pytest tests/test_pd_mcp_live_smoke_01.py -q
```

Without the features, approved `dry_run: false` returns `RealSpawnDisabled`／`RealMcpDisabled`.
Unapproved live → `LiveNotApproved`.

### Live MCP (PD-MCP-LIVE-01)

```rust
use sgenaxis_exec::{AgentPort, FakeMcpClient, McpAgentAdapter, McpAgentSettings, StartRunRequest};

let mut settings = McpAgentSettings::defaults();
settings.endpoint = "http://127.0.0.1:3920/sse".into(); // not :8788／:8787
settings.approved_tools = vec!["list_tools".into()];
let mut agent = McpAgentAdapter::new(settings, Box::new(FakeMcpClient::default()));
// requires --features real-mcp
let run = agent.start_run(StartRunRequest::mcp_live("list_tools"))?;
// Started(dry_run=false) → Progress(tool) → Chunk([mcp-tool:…]) → Exited
```

Unapproved endpoint／tool → `EndpointNotApproved`／`ToolNotApproved` **before** connect／`call_tool`.
Tool／connect failures are observable (`ExecError::Mcp` or `AgentChunk::Failed`).

### MCP transport (docs／comments only — no live server required)

Prefer **stdio** or **local HTTP／SSE** to a **user-explicit** loopback／local target from settings.
Do **not** use HoneyBadger `:8788` or reserved `:8787`. Secrets must not appear in projection DTOs.

## Non-goals

- HoneyBadger / :8788 / :8787
- Multi-agent parallel runs
- Cloud MCP gateway
- Full MCP notification→chunk streaming (adjacent: `PD-LISTEN-01`)

## Test

```powershell
cd D:\AIAD\apps\sgenaxis-desktop\crates\sgenaxis-exec
cargo test
```

If `cargo`／`rustc` are missing → deliverable is source + this README; status **PARTIAL**.
