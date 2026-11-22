"""Business constants. Keep in sync with frontend/src/lib/constants.js."""

ROLES = ("student", "staff", "admin")
STATUSES = ("Submitted", "Assigned", "In Progress", "Resolved")
PRIORITIES = ("Low", "Medium", "High", "Critical")

# Hours allowed to resolve a complaint, by priority.
SLA_HOURS = {"Critical": 24, "High": 48, "Medium": 96, "Low": 168}
# A Critical complaint still open after this many hours is flagged for escalation.
CRITICAL_FLAG_HOURS = 6

# Foundry gets this many seconds to answer. After that the rule-based classifier takes over.
FOUNDRY_TIMEOUT_SECONDS = 15

# Attachments (Blob Storage)
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
MAX_ATTACHMENTS_PER_COMPLAINT = 5

# Duplicate detection: only open complaints from the last N days are compared.
DUPLICATE_WINDOW_DAYS = 30
