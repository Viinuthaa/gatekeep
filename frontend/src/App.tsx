import { useCallback, useEffect, useState } from "react";
import {
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleHelp,
  FlaskConical,
  KeyRound,
  LoaderCircle,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  X,
} from "lucide-react";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000";
const DEMO_API_KEY = "gk_test_demo_key";

type Page =
  | "playground"
  | "requests"
  | "documents"
  | "evaluations"
  | "credentials"
  | "gateway";

type GatewayState = "checking" | "online" | "offline";
type TraceStatus = "passed" | "failed" | "skipped" | "unknown";

type TraceStage = {
  name: string;
  status: TraceStatus;
  detail: string;
};

type ApiResponse = {
  model?: string;
  choices?: Array<{
    message?: { role?: string; content?: string };
    finish_reason?: string | null;
  }>;
  response?: string;
  content?: string;
  request_id?: string;
  tenant_id?: string;
  latency_ms?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  cache_hit?: boolean;
  routing?: {
    complexity?: string;
    reason?: string;
    selected_model?: string;
  };
  detail?: string;
  [key: string]: unknown;
};

type RequestRecord = {
  id: string;
  time: string;
  model: string;
  prompt: string;
  status: "Succeeded" | "Failed";
  latency?: number;
  response?: string;
  error?: string;
  requestId?: string;
};

function errorText(data: ApiResponse, status: number) {
  return typeof data.detail === "string"
    ? data.detail
    : `Request failed (${status}).`;
}

function App() {
  const [page, setPage] = useState<Page>("playground");
  const [gateway, setGateway] = useState<GatewayState>("checking");
  const [checkedAt, setCheckedAt] = useState("");
  const [model, setModel] = useState("gpt-4o-mini");
  const [prompt, setPrompt] = useState("");
  const [apiKey, setApiKey] = useState(DEMO_API_KEY);
  const [showKey, setShowKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [error, setError] = useState("");
  const [trace, setTrace] = useState<TraceStage[]>([]);
  const [requests, setRequests] = useState<RequestRecord[]>([]);
  const [selectedRequest, setSelectedRequest] =
    useState<RequestRecord | null>(null);

  const [documentId, setDocumentId] = useState("");
  const [documentText, setDocumentText] = useState("");
  const [documentQuery, setDocumentQuery] = useState("");
  const [documentLimit, setDocumentLimit] = useState("5");
  const [documentResults, setDocumentResults] = useState<
    Array<Record<string, unknown>>
  >([]);
  const [documentMessage, setDocumentMessage] = useState("");
  const [documentError, setDocumentError] = useState("");
  const [documentLoading, setDocumentLoading] = useState(false);

  const [evaluationName, setEvaluationName] = useState("Basic response check");
  const [evaluationResponse, setEvaluationResponse] = useState("");
  const [expectedContains, setExpectedContains] = useState("");
  const [expectedNotContains, setExpectedNotContains] = useState("");
  const [evaluationReport, setEvaluationReport] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [evaluationError, setEvaluationError] = useState("");
  const [evaluationLoading, setEvaluationLoading] = useState(false);

  const refreshHealth = useCallback(async () => {
    setGateway("checking");

    try {
      const result = await fetch(`${API_BASE}/health`);
      if (!result.ok) throw new Error("Health check failed");

      const data = await result.json();
      setGateway(data.status === "healthy" ? "online" : "offline");
    } catch {
      setGateway("offline");
    }

    setCheckedAt(
      new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    );
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function checkHealth() {
      try {
        const result = await fetch(`${API_BASE}/health`, {
          signal: controller.signal,
        });

        if (!result.ok) throw new Error("Health check failed");

        const data = await result.json();

        if (!controller.signal.aborted) {
          setGateway(data.status === "healthy" ? "online" : "offline");
          setCheckedAt(
            new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            }),
          );
        }
      } catch {
        if (!controller.signal.aborted) {
          setGateway("offline");
          setCheckedAt(
            new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            }),
          );
        }
      }
    }

    void checkHealth();
    return () => controller.abort();
  }, []);

  async function sendRequest() {
    if (!prompt.trim()) {
      setError("Enter a message before sending the request.");
      return;
    }

    if (!apiKey.trim()) {
      setError("Enter a Gatekeep API key.");
      return;
    }

    setLoading(true);
    setError("");
    setResponse(null);
    setTrace([
      { name: "Authentication", status: "unknown", detail: "Request in progress" },
      { name: "Rate limit", status: "unknown", detail: "Awaiting backend result" },
      { name: "Routing", status: "unknown", detail: "Awaiting backend result" },
      { name: "Cache", status: "unknown", detail: "Awaiting backend result" },
      { name: "Provider", status: "unknown", detail: "Awaiting backend result" },
    ]);

    const startedAt = performance.now();
    let responseReceived = false;

    try {
      const result = await fetch(`${API_BASE}/api/v1/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey.trim()}`,
        },
        body: JSON.stringify({
          model,
          messages: [{ role: "user", content: prompt.trim() }],
        }),
      });

      responseReceived = true;
      const data = (await result.json()) as ApiResponse;

      if (!result.ok) {
        const message = errorText(data, result.status);

        setTrace([
          {
            name: "Authentication",
            status: result.status === 401 ? "failed" : "unknown",
            detail:
              result.status === 401
                ? "The backend rejected the API key"
                : "Authentication outcome was not returned separately",
          },
          {
            name: "Rate limit",
            status: result.status === 429 ? "failed" : "unknown",
            detail:
              result.status === 429
                ? "A rate limit rejected the request"
                : "Rate-limit outcome was not returned separately",
          },
          {
            name: "Routing",
            status: "unknown",
            detail: "The failure response did not expose routing details",
          },
          {
            name: "Cache",
            status: "unknown",
            detail: "The failure response did not expose cache details",
          },
          {
            name: "Provider",
            status:
              result.status === 502 || result.status === 503
                ? "failed"
                : "unknown",
            detail: message,
          },
        ]);

        throw new Error(`${result.status}: ${message}`);
      }

      setResponse(data);

      const cacheHit = data.cache_hit === true;
      const routing = data.routing;
      const answer =
        data.choices?.[0]?.message?.content ??
        data.response ??
        data.content ??
        "";

      setTrace([
        {
          name: "Authentication",
          status: "passed",
          detail: "The authenticated endpoint accepted the bearer key",
        },
        {
          name: "Rate limit",
          status: "passed",
          detail: "The request passed the rate-limit check",
        },
        {
          name: "Routing",
          status: routing ? "passed" : "unknown",
          detail: routing
            ? `${routing.selected_model ?? data.model ?? model} Â· ${routing.complexity ?? "complexity not reported"}`
            : "Routing metadata was not returned",
        },
        {
          name: "Cache",
          status:
            typeof data.cache_hit === "boolean" ? "passed" : "unknown",
          detail:
            typeof data.cache_hit !== "boolean"
              ? "Cache outcome was not reported"
              : cacheHit
                ? "Cache hit  cached response returned"
                : "Cache miss  response fetched from provider",
        },
        {
          name: "Provider",
          status: cacheHit ? "skipped" : "passed",
          detail: cacheHit
            ? "Provider call skipped because a cached response was used"
            : "A provider response was returned through the gateway",
        },
      ]);

      setRequests((current) => [
        {
          id: `${Date.now()}-${Math.random()}`,
          time: new Date().toLocaleTimeString(),
          model: data.model ?? model,
          prompt: prompt.trim(),
          status: "Succeeded",
          latency:
            typeof data.latency_ms === "number"
              ? data.latency_ms
              : performance.now() - startedAt,
          response: answer,
          requestId: data.request_id,
        },
        ...current,
      ]);
    } catch (caught) {
      const message =
        caught instanceof Error ? caught.message : "Unexpected error.";

      setError(message);

      if (!responseReceived) {
        setTrace([
          {
            name: "Authentication",
            status: "unknown",
            detail: "No HTTP response received",
          },
          {
            name: "Rate limit",
            status: "unknown",
            detail: "No HTTP response received",
          },
          {
            name: "Routing",
            status: "unknown",
            detail: "No HTTP response received",
          },
          {
            name: "Cache",
            status: "unknown",
            detail: "No HTTP response received",
          },
          {
            name: "Provider",
            status: "unknown",
            detail: "Could not determine which backend stage failed",
          },
        ]);
      }

      setRequests((current) => [
        {
          id: `${Date.now()}-${Math.random()}`,
          time: new Date().toLocaleTimeString(),
          model,
          prompt: prompt.trim(),
          status: "Failed",
          error: message,
        },
        ...current,
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function ingestDocument() {
    setDocumentError("");
    setDocumentMessage("");
    setDocumentResults([]);

    if (!documentId.trim() || !documentText.trim()) {
      setDocumentError("Enter both a document ID and document text.");
      return;
    }

    setDocumentLoading(true);

    try {
      const result = await fetch(`${API_BASE}/api/v1/documents`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey.trim()}`,
        },
        body: JSON.stringify({
          document_id: documentId.trim(),
          text: documentText.trim(),
        }),
      });

      const data = await result.json();

      if (!result.ok) {
        throw new Error(errorText(data as ApiResponse, result.status));
      }

      setDocumentMessage(
        `Document ingested. ${String(data.chunks_created ?? 0)} chunks created.`,
      );
    } catch (caught) {
      setDocumentError(
        caught instanceof Error ? caught.message : "Document ingestion failed.",
      );
    } finally {
      setDocumentLoading(false);
    }
  }

  async function searchDocuments() {
    setDocumentError("");
    setDocumentMessage("");
    setDocumentResults([]);

    if (!documentQuery.trim()) {
      setDocumentError("Enter a search query.");
      return;
    }

    setDocumentLoading(true);

    try {
      const result = await fetch(`${API_BASE}/api/v1/documents/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey.trim()}`,
        },
        body: JSON.stringify({
          query: documentQuery.trim(),
          limit: Number(documentLimit),
        }),
      });

      const data = await result.json();

      if (!result.ok) {
        throw new Error(errorText(data as ApiResponse, result.status));
      }

      setDocumentResults(
        Array.isArray(data.results)
          ? (data.results as Array<Record<string, unknown>>)
          : [],
      );

      setDocumentMessage(
        `${String(data.result_count ?? 0)} matching chunks returned.`,
      );
    } catch (caught) {
      setDocumentError(
        caught instanceof Error ? caught.message : "Document search failed.",
      );
    } finally {
      setDocumentLoading(false);
    }
  }

  async function runEvaluation() {
    setEvaluationError("");
    setEvaluationReport(null);

    if (!evaluationName.trim() || !evaluationResponse.trim()) {
      setEvaluationError("Enter a case name and response to evaluate.");
      return;
    }

    setEvaluationLoading(true);

    try {
      const result = await fetch(`${API_BASE}/api/v1/evaluations/run`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${apiKey.trim()}`,
        },
        body: JSON.stringify({
          cases: [
            {
              name: evaluationName.trim(),
              response: evaluationResponse,
              expected_contains: expectedContains
                .split("\n")
                .map((value) => value.trim())
                .filter(Boolean),
              expected_not_contains: expectedNotContains
                .split("\n")
                .map((value) => value.trim())
                .filter(Boolean),
            },
          ],
        }),
      });

      const data = await result.json();

      if (!result.ok) {
        throw new Error(errorText(data as ApiResponse, result.status));
      }

      setEvaluationReport(data as Record<string, unknown>);
    } catch (caught) {
      setEvaluationError(
        caught instanceof Error ? caught.message : "Evaluation failed.",
      );
    } finally {
      setEvaluationLoading(false);
    }
  }

  const answer =
    response?.choices?.[0]?.message?.content ??
    response?.response ??
    response?.content ??
    "";

  const navItems: Array<{ id: Page; label: string }> = [
    { id: "playground", label: "Playground" },
    { id: "requests", label: "Requests" },
    { id: "documents", label: "Documents" },
    { id: "evaluations", label: "Evaluations" },
    { id: "credentials", label: "Credentials" },
    { id: "gateway", label: "Gateway" },
  ];

  const titles: Record<
    Page,
    { title: string; intro: string; kicker: string }
  > = {
    playground: {
      title: "Send a request, see what the gate did",
      intro:
        "Send a chat completion through Gatekeep and inspect its response and available gateway metadata.",
      kicker: "LLM GATEWAY / PLAYGROUND",
    },
    requests: {
      title: "Request activity",
      intro:
        "Review requests made during this browser session. Persistent request storage is not configured yet.",
      kicker: "OBSERVABILITY / REQUESTS",
    },
    documents: {
      title: "Document search",
      intro:
        "Ingest tenant-scoped text and search the chunks returned by the backend.",
      kicker: "KNOWLEDGE / DOCUMENTS",
    },
    evaluations: {
      title: "Evaluate a response",
      intro:
        "Run expected-text checks and inspect the evaluation report returned by the API.",
      kicker: "QUALITY / EVALUATIONS",
    },
    credentials: {
      title: "Credentials",
      intro:
        "Configure the local Gatekeep bearer key used for authenticated requests.",
      kicker: "ACCESS / CREDENTIALS",
    },
    gateway: {
      title: "Gateway status",
      intro:
        "Check FastAPI connectivity. A healthy endpoint does not guarantee Redis, the database, or the provider is available.",
      kicker: "SYSTEM / GATEWAY",
    },
  };

  const currentTitle = titles[page];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button
          className="brand"
          type="button"
          onClick={() => setPage("playground")}
        >
        
          <span>Gatekeep</span>
        </button>

        <p className="brand-tagline">A gateway that guards every LLM call</p>

        <div className="nav-caption">WORKSPACE</div>

        <div className="project-chip">
          <span className="project-mark">GK</span>
          <span>
            <strong>Gatekeep Gateway</strong>
            <small>Local development</small>
          </span>
        </div>

        <div className="nav-caption nav-caption-main">TOOLS</div>

        <nav className="navigation" aria-label="Main navigation">
          {navItems.map((item) => (
            <button
              className={`nav-link ${page === item.id ? "active" : ""}`}
              key={item.id}
              type="button"
              onClick={() => setPage(item.id)}
            >
              <span>{item.label}</span>
              {page === item.id && (
                <ChevronRight className="nav-current" size={15} />
              )}
            </button>
          ))}

          <a
            className="nav-link nav-link-reference"
            href={`${API_BASE}/docs`}
            target="_blank"
            rel="noreferrer"
          >
            <span>API reference</span>
            <ArrowUpRight size={15} />
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-connection">
            <span className={`connection-dot ${gateway}`} />
            <div>
              <strong>
                {gateway === "online"
                  ? "Gateway reachable"
                  : gateway === "offline"
                    ? "Gateway unavailable"
                    : "Checking gateway"}
              </strong>
              <small>127.0.0.1:8000</small>
            </div>
            <button
              className="sidebar-refresh"
              type="button"
              onClick={() => void refreshHealth()}
              aria-label="Refresh gateway status"
            >
              <RefreshCw size={15} />
            </button>
          </div>

          <div className="sidebar-version">
            <span>GATEKEEP</span>
            <span>v0.1.0</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            <span>Gatekeep</span>
            <ChevronRight size={15} />
            <strong>{navItems.find((item) => item.id === page)?.label}</strong>
          </div>

          <div className="topbar-actions">
            <span className="environment">
              <span />
              Local environment
            </span>
            <button
              className="topbar-refresh"
              type="button"
              onClick={() => void refreshHealth()}
              aria-label="Refresh gateway health"
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </header>

        <div className="content">
          <section className="intro">
            <div className="intro-kicker">{currentTitle.kicker}</div>
            <h1>{currentTitle.title}</h1>
            <p>{currentTitle.intro}</p>
          </section>

          {page === "playground" && (
            <>
              <section className="request-path" aria-label="Request lifecycle">
                {trace.length === 0 ? (
                  ["Authentication", "Rate limit", "Routing", "Cache", "Provider"].map(
                    (name) => (
                      <div className="path-step" key={name}>
                        <div className="path-heading">
                          <span className="path-marker"><span /></span>
                          <strong>{name}</strong>
                        </div>
                        <span className="path-status">Waiting</span>
                        <p className="trace-detail">No request to inspect</p>
                      </div>
                    ),
                  )
                ) : (
                  trace.map((stage) => (
                    <div className="path-step" key={stage.name}>
                      <div className="path-heading">
                        <span className={`path-marker trace-${stage.status}`}>
                          {stage.status === "passed" ? (
                            <Check size={13} />
                          ) : stage.status === "failed" ? (
                            <X size={13} />
                          ) : (
                            <span />
                          )}
                        </span>
                        <strong>{stage.name}</strong>
                      </div>
                      <span className="path-status">
                        {stage.status === "passed"
                          ? "Passed"
                          : stage.status === "failed"
                            ? "Failed"
                            : stage.status === "skipped"
                              ? "Skipped"
                              : "Not verified"}
                      </span>
                      <p className="trace-detail">{stage.detail}</p>
                    </div>
                  ))
                )}
              </section>

              <div className="playground-grid">
                <section className="request-panel">
                  <div className="section-heading">
                    <div>
                      <span className="section-index">01 / REQUEST</span>
                      <h2>Compose request</h2>
                    </div>
                    <span className="method-badge">POST</span>
                  </div>

                  <label className="field-label" htmlFor="model">
                    Requested model
                  </label>
                  <select
                    className="text-input model-select"
                    id="model"
                    value={model}
                    onChange={(event) => setModel(event.target.value)}
                  >
                    <option value="gpt-4o-mini">gpt-4o-mini</option>
                    <option value="gpt-4o">gpt-4o</option>
                  </select>

                  <p className="field-help">
                    The current router preserves the requested model.
                  </p>

                  <div className="field-heading">
                    <label className="field-label" htmlFor="api-key">
                      Authorization
                    </label>
                    <button
                      className="text-button"
                      type="button"
                      onClick={() => setPage("credentials")}
                    >
                      Manage key
                    </button>
                  </div>

                  <div className="key-input-wrap">
                    <KeyRound size={16} />
                    <input
                      id="api-key"
                      type={showKey ? "text" : "password"}
                      value={apiKey}
                      onChange={(event) => setApiKey(event.target.value)}
                      autoComplete="off"
                      spellCheck={false}
                    />
                    <button
                      className="text-button"
                      type="button"
                      onClick={() => setShowKey((value) => !value)}
                    >
                      {showKey ? "Hide" : "Show"}
                    </button>
                  </div>

                  <p className="field-help">
                    Use the local demo key during development. Never put a
                    production secret in browser code.
                  </p>

                  <div className="field-heading">
                    <label className="field-label" htmlFor="prompt">
                      Message
                    </label>
                    <span className="character-count">
                      {prompt.length} characters
                    </span>
                  </div>

                  <textarea
                    id="prompt"
                    className="prompt-input"
                    value={prompt}
                    onChange={(event) => setPrompt(event.target.value)}
                    onKeyDown={(event) => {
                      if (
                        event.key === "Enter" &&
                        (event.ctrlKey || event.metaKey)
                      ) {
                        event.preventDefault();
                        void sendRequest();
                      }
                    }}
                    placeholder="Ask something to send through the gateway"
                    rows={7}
                  />

                  {error && (
                    <div className="error-message" role="alert">
                      <CircleHelp size={17} />
                      <span>{error}</span>
                    </div>
                  )}

                  <div className="send-row">
                    <button
                      className="send-button"
                      type="button"
                      onClick={() => void sendRequest()}
                      disabled={loading || gateway !== "online"}
                    >
                      {loading ? (
                        <LoaderCircle className="spin" size={17} />
                      ) : (
                        <Send size={16} />
                      )}
                      {loading ? "Sending request" : "Send request"}
                    </button>
                  </div>

                  {gateway !== "online" && (
                    <p className="send-note">
                      Start the FastAPI server to send requests.
                    </p>
                  )}
                </section>

                <section className="response-panel">
                  <div className="section-heading">
                    <div>
                      <span className="section-index">02 / RESPONSE</span>
                      <h2>Response</h2>
                    </div>
                    {response && <span className="result-chip">Received</span>}
                  </div>

                  {!response && !loading && (
                    <>
                      <p className="response-intro">
                        Send a request to inspect the actual response and
                        metadata returned by Gatekeep.
                      </p>
                      <pre className="request-preview">
                        <code>{`POST ${API_BASE}/api/v1/chat/completions
Content-Type: application/json

${JSON.stringify(
  {
    model,
    messages: [{ role: "user", content: prompt }],
  },
  null,
  2,
)}`}</code>
                      </pre>
                    </>
                  )}

                  {loading && (
                    <div className="response-state">
                      <LoaderCircle className="spin" size={23} />
                      <strong>Waiting for the gateway</strong>
                      <p>The backend is processing the request.</p>
                    </div>
                  )}

                  {response && (
                    <>
                      <div className="response-toolbar">
                        <span className="success-label">
                          <Check size={14} />
                          Request succeeded
                        </span>
                        <button
                          className="text-button"
                          type="button"
                          onClick={() => {
                            void navigator.clipboard?.writeText(answer);
                          }}
                        >
                          Copy answer
                        </button>
                      </div>

                      <div className="answer-content">
                        {answer || "No displayable text content was returned."}
                      </div>

                      <div className="response-metrics">
                        <div>
                          <span>LATENCY</span>
                          <strong>
                            {typeof response.latency_ms === "number"
                              ? `${response.latency_ms.toFixed(1)} ms`
                              : "Not returned"}
                          </strong>
                        </div>
                        <div>
                          <span>TOKENS</span>
                          <strong>
                            {typeof response.total_tokens === "number"
                              ? response.total_tokens
                              : typeof response.prompt_tokens === "number" ||
                                  typeof response.completion_tokens === "number"
                                ? (response.prompt_tokens ?? 0) +
                                  (response.completion_tokens ?? 0)
                                : "Not returned"}
                          </strong>
                        </div>
                        <div>
                          <span>CACHE</span>
                          <strong>
                            {typeof response.cache_hit === "boolean"
                              ? response.cache_hit
                                ? "HIT"
                                : "MISS"
                              : "Not returned"}
                          </strong>
                        </div>
                      </div>
                    </>
                  )}
                </section>
              </div>

              <section className="metadata-section">
                <div className="section-heading">
                  <div>
                    <span className="section-index">03 / INSPECTION</span>
                    <h2>Request metadata</h2>
                  </div>
                </div>

                {response ? (
                  <div className="metadata-table">
                    {[
                      ["Request ID", response.request_id ?? "Not returned"],
                      ["Tenant", response.tenant_id ?? "Not returned"],
                      ["Returned model", response.model ?? "Not returned"],
                      [
                        "Selected model",
                        response.routing?.selected_model ?? "Not returned",
                      ],
                      [
                        "Complexity",
                        response.routing?.complexity ?? "Not returned",
                      ],
                      [
                        "Routing reason",
                        response.routing?.reason ?? "Not returned",
                      ],
                    ].map(([label, value]) => (
                      <div className="metadata-row" key={label}>
                        <span>{label}</span>
                        <code>{value}</code>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="metadata-empty">
                    Metadata will appear after a successful request.
                  </p>
                )}
              </section>
            </>
          )}

          {page === "requests" && (
            <section className="page-panel">
              <div className="section-heading">
                <div>
                  <span className="section-index">SESSION / ACTIVITY</span>
                  <h2>Requests made in this session</h2>
                </div>
                <span className="result-chip">{requests.length} requests</span>
              </div>

              <p className="panel-description">
                This list is held in browser memory and clears on reload. It
                is not persistent request history.
              </p>

              {requests.length === 0 ? (
                <div className="empty-state">
                  <strong>No requests yet</strong>
                  <p>Send a request in Playground to see it here.</p>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => setPage("playground")}
                  >
                    Open Playground
                  </button>
                </div>
              ) : (
                <div className="request-list">
                  {requests.map((item) => (
                    <button
                      className={`request-list-item ${selectedRequest?.id === item.id ? "selected" : ""}`}
                      type="button"
                      key={item.id}
                      onClick={() => setSelectedRequest(item)}
                    >
                      <span
                        className={`request-status ${item.status === "Succeeded" ? "success" : "failure"}`}
                      >
                        {item.status === "Succeeded" ? (
                          <Check size={15} />
                        ) : (
                          <X size={15} />
                        )}
                      </span>
                      <span className="request-list-main">
                        <strong>{item.prompt}</strong>
                        <small>
                          {item.time} Â· {item.model}
                        </small>
                      </span>
                      <span className="request-list-result">
                        {item.latency !== undefined
                          ? `${item.latency.toFixed(1)} ms`
                          : item.status}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {selectedRequest && (
                <div className="detail-panel">
                  <div className="section-heading">
                    <h2>Selected request</h2>
                    <button
                      className="text-button"
                      type="button"
                      onClick={() => setSelectedRequest(null)}
                    >
                      Clear selection
                    </button>
                  </div>
                  <div className="metadata-table">
                    {[
                      ["Status", selectedRequest.status],
                      ["Model", selectedRequest.model],
                      ["Request ID", selectedRequest.requestId ?? "Not returned"],
                      ["Prompt", selectedRequest.prompt],
                      [
                        "Result",
                        selectedRequest.response ??
                          selectedRequest.error ??
                          "No result text",
                      ],
                    ].map(([label, value]) => (
                      <div className="metadata-row" key={label}>
                        <span>{label}</span>
                        <span>{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>
          )}

          {page === "documents" && (
            <div className="feature-grid">
              <section className="page-panel">
                <div className="section-heading">
                  <div>
                    <span className="section-index">01 / INGEST</span>
                    <h2>Add a document</h2>
                  </div>
                </div>
                <p className="panel-description">
                  Submit plain text to the tenant-isolated document store. The
                  current store is in memory and is not durable across restarts.
                </p>
                <label className="field-label" htmlFor="document-id">
                  Document ID
                </label>
                <input
                  className="text-input"
                  id="document-id"
                  value={documentId}
                  onChange={(event) => setDocumentId(event.target.value)}
                  placeholder="e.g. onboarding-guide"
                />
                <label className="field-label spaced-label" htmlFor="document-text">
                  Document text
                </label>
                <textarea
                  className="prompt-input"
                  id="document-text"
                  value={documentText}
                  onChange={(event) => setDocumentText(event.target.value)}
                  placeholder="Paste the text you want to index..."
                  rows={8}
                />
                <button
                  className="send-button"
                  type="button"
                  onClick={() => void ingestDocument()}
                  disabled={documentLoading}
                >
                  {documentLoading && <LoaderCircle className="spin" size={17} />}
                  Ingest document
                </button>
              </section>

              <section className="page-panel">
                <div className="section-heading">
                  <div>
                    <span className="section-index">02 / SEARCH</span>
                    <h2>Find relevant text</h2>
                  </div>
                  <Search size={20} />
                </div>
                <p className="panel-description">
                  Search chunks available to the authenticated tenant using
                  the current keyword-based search implementation.
                </p>
                <label className="field-label" htmlFor="document-query">
                  Search query
                </label>
                <input
                  className="text-input"
                  id="document-query"
                  value={documentQuery}
                  onChange={(event) => setDocumentQuery(event.target.value)}
                  placeholder="What are you looking for?"
                />
                <label className="field-label spaced-label" htmlFor="document-limit">
                  Maximum results
                </label>
                <select
                  className="text-input"
                  id="document-limit"
                  value={documentLimit}
                  onChange={(event) => setDocumentLimit(event.target.value)}
                >
                  <option value="3">3 results</option>
                  <option value="5">5 results</option>
                  <option value="10">10 results</option>
                  <option value="20">20 results</option>
                </select>
                <button
                  className="send-button search-button"
                  type="button"
                  onClick={() => void searchDocuments()}
                  disabled={documentLoading}
                >
                  {documentLoading && <LoaderCircle className="spin" size={17} />}
                  Search documents
                </button>
              </section>

              {(documentMessage || documentError) && (
                <div
                  className={documentError ? "error-message feature-message" : "success-message feature-message"}
                  role={documentError ? "alert" : "status"}
                >
                  {documentError ? <CircleHelp size={17} /> : <Check size={17} />}
                  <span>{documentError || documentMessage}</span>
                </div>
              )}

              {documentResults.length > 0 && (
                <section className="page-panel results-panel">
                  <div className="section-heading">
                    <div>
                      <span className="section-index">03 / RESULTS</span>
                      <h2>Matching chunks</h2>
                    </div>
                    <span className="result-chip">{documentResults.length} results</span>
                  </div>
                  {documentResults.map((item, index) => (
                    <article
                      className="document-result"
                      key={`${String(item.document_id ?? "document")}-${index}`}
                    >
                      <div className="document-result-heading">
                        <strong>{String(item.document_id ?? `Result ${index + 1}`)}</strong>
                        <span>
                          Score: {typeof item.score === "number" ? item.score.toFixed(3) : "Not returned"}
                        </span>
                      </div>
                      <p>{String(item.text ?? item.content ?? "No text returned.")}</p>
                    </article>
                  ))}
                </section>
              )}
            </div>
          )}

          {page === "evaluations" && (
            <div className="feature-grid">
              <section className="page-panel">
                <div className="section-heading">
                  <div>
                    <span className="section-index">01 / TEST CASE</span>
                    <h2>Configure text checks</h2>
                  </div>
                  
                </div>
                <p className="panel-description">
                  This evaluator checks required and forbidden text. It is
                  deterministic matching, not a semantic AI judge.
                </p>
                <label className="field-label" htmlFor="evaluation-name">
                  Case name
                </label>
                <input
                  className="text-input"
                  id="evaluation-name"
                  value={evaluationName}
                  onChange={(event) => setEvaluationName(event.target.value)}
                />
                <label className="field-label spaced-label" htmlFor="evaluation-response">
                  Response to evaluate
                </label>
                <textarea
                  className="prompt-input"
                  id="evaluation-response"
                  value={evaluationResponse}
                  onChange={(event) => setEvaluationResponse(event.target.value)}
                  placeholder="Paste a model response..."
                  rows={6}
                />
                <label className="field-label spaced-label" htmlFor="expected-contains">
                  Required phrases
                </label>
                <textarea
                  className="prompt-input compact-textarea"
                  id="expected-contains"
                  value={expectedContains}
                  onChange={(event) => setExpectedContains(event.target.value)}
                  placeholder="One phrase per line"
                  rows={3}
                />
                <p className="field-help">Each non-empty line must appear.</p>
                <label className="field-label" htmlFor="expected-not-contains">
                  Forbidden phrases
                </label>
                <textarea
                  className="prompt-input compact-textarea"
                  id="expected-not-contains"
                  value={expectedNotContains}
                  onChange={(event) => setExpectedNotContains(event.target.value)}
                  placeholder="One phrase per line"
                  rows={3}
                />
                <p className="field-help">Each non-empty line must be absent.</p>

                {evaluationError && (
                  <div className="error-message" role="alert">
                    <CircleHelp size={17} />
                    <span>{evaluationError}</span>
                  </div>
                )}

                <button
                  className="send-button"
                  type="button"
                  onClick={() => void runEvaluation()}
                  disabled={evaluationLoading}
                >
                  {evaluationLoading && <LoaderCircle className="spin" size={17} />}
                  Run evaluation
                </button>
              </section>

              <section className="page-panel">
                <div className="section-heading">
                  <div>
                    <span className="section-index">02 / REPORT</span>
                    <h2>Evaluation report</h2>
                  </div>
                </div>

                {!evaluationReport && !evaluationLoading && (
                  <div className="empty-state">
                    <strong>No evaluation run yet</strong>
                    <p>Run a test to see the actual backend report.</p>
                  </div>
                )}

                {evaluationLoading && (
                  <div className="response-state">
                    <LoaderCircle className="spin" size={23} />
                    <strong>Running evaluation</strong>
                  </div>
                )}

                {evaluationReport && (
                  <div className="evaluation-report">
                    <div className="report-summary">
                      <div>
                        <span>PASS RATE</span>
                        <strong>{String(evaluationReport.pass_rate ?? "â€”")}%</strong>
                      </div>
                      <div>
                        <span>PASSED</span>
                        <strong>{String(evaluationReport.passed_cases ?? "â€”")}</strong>
                      </div>
                      <div>
                        <span>FAILED</span>
                        <strong>{String(evaluationReport.failed_cases ?? "â€”")}</strong>
                      </div>
                    </div>

                    {Array.isArray(evaluationReport.results) &&
                      evaluationReport.results.map((item, index) => {
                        const result = item as Record<string, unknown>;

                        return (
                          <article className="evaluation-result" key={index}>
                            <div className="document-result-heading">
                              <strong>{String(result.name ?? "Evaluation case")}</strong>
                              <span className={result.passed ? "evaluation-pass" : "evaluation-fail"}>
                                {result.passed ? "Passed" : "Failed"}
                              </span>
                            </div>
                            <p>
                              Score: {String(result.score ?? "â€”")} Â· Checks:{" "}
                              {String(result.checks_passed ?? "â€”")} / {String(result.total_checks ?? "â€”")}
                            </p>
                            {Array.isArray(result.failures) && result.failures.length > 0 && (
                              <ul className="failure-list">
                                {result.failures.map((failure, failureIndex) => (
                                  <li key={failureIndex}>{String(failure)}</li>
                                ))}
                              </ul>
                            )}
                          </article>
                        );
                      })}
                  </div>
                )}
              </section>
            </div>
          )}

          {page === "credentials" && (
            <section className="page-panel narrow-panel">
              <div className="section-heading">
                <div>
                  <span className="section-index">ACCESS / LOCAL KEY</span>
                  <h2>Gatekeep API key</h2>
                </div>
               
              </div>
              <p className="panel-description">
                This key authenticates requests to the local backend. The
                current backend uses a demo key and does not support persistent
                key creation, rotation, or revocation.
              </p>
              <label className="field-label" htmlFor="credentials-key">
                Bearer token
              </label>
              <div className="key-input-wrap">
                <KeyRound size={16} />
                <input
                  id="credentials-key"
                  type={showKey ? "text" : "password"}
                  value={apiKey}
                  onChange={(event) => setApiKey(event.target.value)}
                  autoComplete="off"
                  spellCheck={false}
                />
                <button
                  className="text-button"
                  type="button"
                  onClick={() => setShowKey((value) => !value)}
                >
                  {showKey ? "Hide" : "Show"}
                </button>
              </div>
              <p className="field-help">
                The key remains in page state only and is not saved to a database.
              </p>
              <button
                className="secondary-button"
                type="button"
                onClick={() => {
                  setApiKey(DEMO_API_KEY);
                  setShowKey(false);
                }}
              >
                Reset local demo key
              </button>
              <div className="warning-message">
                This is a Gatekeep gateway key, not your OpenAI provider secret.
                Never put a production secret in browser code.
              </div>
            </section>
          )}

          {page === "gateway" && (
            <section className="page-panel narrow-panel">
              <div className="section-heading">
                <div>
                  <span className="section-index">SYSTEM / HEALTH</span>
                  <h2>Gateway connectivity</h2>
                </div>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => void refreshHealth()}
                >
                  <RefreshCw size={15} />
                  Refresh
                </button>
              </div>

              <div className="gateway-status-card">
                <span className={`connection-dot ${gateway}`} />
                <div>
                  <strong>
                    {gateway === "online"
                      ? "FastAPI is reachable"
                      : gateway === "offline"
                        ? "FastAPI is unavailable"
                        : "Checking FastAPI"}
                  </strong>
                  <p>
                    {gateway === "online"
                      ? "The health endpoint responded successfully."
                      : gateway === "offline"
                        ? "Check that the backend is running."
                        : "Waiting for the health check."}
                  </p>
                </div>
              </div>

              <div className="metadata-table">
                <div className="metadata-row">
                  <span>Backend address</span>
                  <code>{API_BASE}</code>
                </div>
                <div className="metadata-row">
                  <span>Health endpoint</span>
                  <code>/health</code>
                </div>
                <div className="metadata-row">
                  <span>API documentation</span>
                  <a href={`${API_BASE}/docs`} target="_blank" rel="noreferrer">
                    Open Swagger UI <ArrowUpRight size={14} />
                  </a>
                </div>
                <div className="metadata-row">
                  <span>Last checked</span>
                  <code>{checkedAt || "Not checked yet"}</code>
                </div>
              </div>

              <div className="warning-message">
                This check covers FastAPI only. Redis, PostgreSQL, and the
                model provider need separate health checks.
              </div>
            </section>
          )}

          <footer className="page-footer">
            <span>GATEKEEP / LOCAL CONTROL PLANE</span>
            <span>{checkedAt ? `Health checked ${checkedAt}` : "Health check pending"}</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

export default App;
