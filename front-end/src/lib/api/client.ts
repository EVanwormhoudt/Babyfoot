export type Fetcher = typeof fetch;

export function apiUrl(path: string): string {
	const normalizedPath = path.startsWith('/') ? path : `/${path}`;
	const apiPath = normalizedPath === '/api' || normalizedPath.startsWith('/api/')
		? normalizedPath
		: `/api${normalizedPath}`;

	return apiPath;
}

export function apiFetch(path: string, init: RequestInit = {}, fetcher?: Fetcher): Promise<Response> {
	const f = fetcher ?? fetch;
	return f(apiUrl(path), {
		...init,
		credentials: init.credentials ?? 'include'
	});
}
