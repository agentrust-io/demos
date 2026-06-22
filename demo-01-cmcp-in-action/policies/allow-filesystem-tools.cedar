// Allow write_file and read_file for any principal
permit (
  principal,
  action == cMCP::Action::"call_tool",
  resource
) when {
  resource.tool_name == "write_file" ||
  resource.tool_name == "read_file"
};
