// v1 policy: allow all catalog tools
permit (
  principal,
  action == cMCP::Action::"call_tool",
  resource
);
