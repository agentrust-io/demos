// v2 policy: read_file allowed; write_file DENIED
// This is the "swapped" policy. Its bundle hash differs from v1.
// Any verifier that pinned the v1 hash will reject TRACE claims produced
// by a cMCP instance loaded with this bundle.
permit (
  principal,
  action == cMCP::Action::"call_tool",
  resource
) when {
  resource.tool_name == "read_file"
};

forbid (
  principal,
  action == cMCP::Action::"call_tool",
  resource
) when {
  resource.tool_name == "write_file"
};
