# Society Relay public hostname

https://relay.sarthakagrawal.dev

This Worker forwards to the existing public AWS Lambda URL. It preserves cookies,
validates browser Origin before translating the host, streams responses, rewrites
origin redirects, and disables shared caching. DynamoDB and AgentCore remain on AWS.

Deploy using the existing authorized Wrangler login:

```sh
node --test cloudflare/worker.test.mjs
npx --yes wrangler@4.130.0 deploy --dry-run --config cloudflare/wrangler.jsonc
npx --yes wrangler@4.130.0 deploy --config cloudflare/wrangler.jsonc
```

Custom-domain deployment manages the DNS record and HTTPS certificate. No extra
runtime package or secret is required. Live verification is recorded in
`docs/cloudflare-domain-evidence.json`.
