// cMCP Cedar policy -- bank support agent
//
// The runtime maps each tool name to a Cedar action (PascalCase):
//   get_balance     -> Action::"GetBalance"
//   get_customer    -> Action::"GetCustomer"
//   transfer_funds  -> Action::"TransferFunds"
//   export_records  -> Action::"ExportRecords"
//
// The agent may read account and customer data.
permit (
  principal,
  action in [Action::"GetBalance", Action::"GetCustomer"],
  resource
);

// It may not move money or bulk-export records. forbid overrides permit,
// so these are denied at the gateway (HTTP 403) and never reach the tool.
forbid (
  principal,
  action in [Action::"TransferFunds", Action::"ExportRecords"],
  resource
);
