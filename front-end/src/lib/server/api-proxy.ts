import { env } from '$env/dynamic/private';
import { error, type RequestEvent } from '@sveltejs/kit';

type Fetcher = typeof fetch;

export function normalizeBase(value: string | undefined): string | null {
	if (!value) return null;
	const trimmed = value.trim();
	if (!trimmed) return null;
	return trimmed.replace(/\/$/, '');
}

export function isSameOriginApiRequest(event: RequestEvent, request: Request): boolean {
	const requestUrl = new URL(request.url);
	return (
		requestUrl.origin === event.url.origin &&
		(requestUrl.pathname === '/api' || requestUrl.pathname.startsWith('/api/'))
	);
}

function getOriginalClientIp(event: RequestEvent): string {
	const cloudflareIp = event.request.headers.get('cf-connecting-ip')?.trim();
	if (cloudflareIp) return cloudflareIp;
	return event.getClientAddress();
}

function getOriginalProtocol(event: RequestEvent): string {
	const forwardedProto = event.request.headers.get('x-forwarded-proto')?.split(',', 1)[0]?.trim();
	if (forwardedProto) return forwardedProto;
	return event.url.protocol.replace(':', '');
}

export function buildInternalApiRequest(event: RequestEvent, request: Request): Request {
	const internalApiBase = normalizeBase(env.INTERNAL_API_BASE);
	if (!internalApiBase) {
		error(502, 'INTERNAL_API_BASE is not configured');
	}

	const requestUrl = new URL(request.url);
	const targetUrl = new URL(`${requestUrl.pathname}${requestUrl.search}`, `${internalApiBase}/`);
	const headers = new Headers(request.headers);
	const originalClientIp = getOriginalClientIp(event);

	headers.delete('connection');
	headers.delete('content-length');
	headers.delete('host');
	headers.delete('transfer-encoding');
	headers.set('x-real-ip', originalClientIp);
	headers.set('x-forwarded-for', originalClientIp);
	headers.set('x-forwarded-proto', getOriginalProtocol(event));

	return new Request(targetUrl, {
		body: request.body,
		duplex: request.body ? 'half' : undefined,
		headers,
		method: request.method,
		redirect: 'manual'
	} as RequestInit & { duplex?: 'half' });
}

export async function proxyApiRequest(event: RequestEvent, fetcher: Fetcher = event.fetch): Promise<Response> {
	return fetcher(buildInternalApiRequest(event, event.request));
}
