/**
 * Cloudflare Worker reverse proxy for Neverlose clients.
 *
 * Neverlose network.get returns empty body for *.up.railway.app (TLS/SNI quirk).
 * Point CLOUD_API_HOST at this worker URL or a custom domain routed to it.
 *
 * Set BACKEND in wrangler.toml [vars] or as a Worker secret.
 */
const DEFAULT_BACKEND = "https://shinymoon-cloud-production.up.railway.app";

export default {
	async fetch(request, env) {
		const backend = (env && env.BACKEND) || DEFAULT_BACKEND;
		const incoming = new URL(request.url);
		const target = new URL(incoming.pathname + incoming.search, backend);

		const headers = new Headers(request.headers);
		headers.delete("host");

		const init = {
			method: request.method,
			headers,
			redirect: "follow",
		};
		if (request.method !== "GET" && request.method !== "HEAD") {
			init.body = request.body;
		}

		return fetch(target.toString(), init);
	},
};
