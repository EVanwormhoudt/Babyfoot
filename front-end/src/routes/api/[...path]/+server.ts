import { proxyApiRequest } from '$lib/server/api-proxy';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = proxyApiRequest;
export const HEAD: RequestHandler = proxyApiRequest;
export const POST: RequestHandler = proxyApiRequest;
export const PUT: RequestHandler = proxyApiRequest;
export const PATCH: RequestHandler = proxyApiRequest;
export const DELETE: RequestHandler = proxyApiRequest;
export const OPTIONS: RequestHandler = proxyApiRequest;
