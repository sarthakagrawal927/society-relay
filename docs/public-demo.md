# Public preview deployment

Deploy the existing Dockerfile to one free Render web instance. Set `RELAY_PUBLIC_DEMO=1`, `RELAY_AUTO=1`, `RELAY_MODEL_PROVIDER=gateway`, and supply the authorized gateway key as a protected hosting environment variable. Health check: `/health`. No paid disk or database is required.

This is a synthetic, single-instance preview. Free Render instances sleep when idle and their local disk resets on restart or redeployment. Workspaces and local quota counters therefore reset with that disk. The page discloses this limitation. It is not suitable for real resident records or guaranteed deadline monitoring.

Public mode caps new workspaces at 100 and gateway request preparations at 150 per UTC day across all visitors. SQLite transactions prevent concurrent requests from exceeding the local cap. Gateway client retries are disabled. The provider's own free quota remains an independent limit; these local controls are not a durable billing cap. Only one agent workspace runs at a time. No AWS resources or paid hosting resources are provisioned by this deployment.
