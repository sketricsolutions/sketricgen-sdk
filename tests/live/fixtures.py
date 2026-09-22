"""Non-secret dev fixtures for the live probe.

These are stable dev-environment identifiers, not credentials. The unified API
key is never stored here — it comes from the environment at run time.
"""

# The maintainer's dev teamspace.
TEAMSPACE_ID = "tsp_personal_a48894c80091700e96ec5af762ae9040"

# A published workflow agent in the teamspace, used by both the control-plane
# field-match check and the data-plane run_workflow probe.
TEST_AGENT_ID = "skflow_1ba99529-3107-409c-a4be-a28605bd4e63"

# A published Brand Agent with an enabled lead-capture HITL tool.
TEST_BRAND_AGENT_ID = "skbrand_ddc6a3d0-6d9d-4dcc-8d53-15945fd2c21e"

# Dev endpoint overrides (test-only; the shipped defaults target prod). The
# probe always runs against dev, so it overrides every plane's base URL rather
# than relying on the shipped default.
DEV_CHAT_BASE_URL = "https://dev-chat.sketricgen.ai"
DEV_API_BASE_URL = "https://krjavjkt27.execute-api.us-east-1.amazonaws.com/dev"
DEV_ADMIN_BASE_URL = f"{DEV_API_BASE_URL}/admin/v1"
DEV_UPLOAD_INIT_URL = f"{DEV_API_BASE_URL}/publicAssetsUploadInit"
DEV_UPLOAD_COMPLETE_URL = f"{DEV_API_BASE_URL}/publicAssetsUploadComplete"
