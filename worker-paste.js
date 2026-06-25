// Paste this entire file into Cloudflare Dashboard → Workers → Create → Edit code → Deploy
// Then set CLOUD_API_HOST in shinymoon_alpha.lua to your *.workers.dev URL

const BACKEND = "https://shinymoon-cloud-production.up.railway.app";

export default {
	async fetch(request, env) {
		const backend = (env && env.BACKEND) || BACKEND;
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
