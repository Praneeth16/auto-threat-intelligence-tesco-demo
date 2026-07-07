// Shared display labels for agent tool-loop steps and finding score components.
// Used by both the Triage Board (inline step markers) and the Finding drawer, so
// the two never drift.

export const TOOL_LABEL: Record<string, string> = {
  query_telemetry: "querying telemetry",
  check_auth_anomalies: "checking auth anomalies",
  get_user_context: "reading user context",
  get_campaign_cluster: "clustering campaign",
  get_report_context: "pulling report context",
  search_case_memory: "searching case memory",
};

// Human labels for the risk-score components emitted by the scorer
// (see app/backend/simulator.py). Unknown keys fall back to the raw key.
export const COMPONENT_LABEL: Record<string, string> = {
  brand_similarity: "brand similarity",
  users: "affected users",
  credential_entry: "credential entry seen",
  privileged: "privileged account",
  recency: "recency",
  repeat_access: "repeat access",
  report_only: "report-only",
};
