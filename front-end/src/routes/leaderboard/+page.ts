// TypeScript
import type {PageLoad} from './$types';
import {getLeaderboard} from '$lib/api/players';

export const ssr = false; // client-only to avoid eager SSR fetches

type Scope = 'monthly' | 'yearly' | 'overall';
type PlayerRow = { id: number; name: string; wins: number; losses: number; elo: number };

const DEFAULT_SCOPE: Scope = 'yearly';

export const load: PageLoad = async ({fetch, url}) => {
    const q = (url.searchParams.get('scope') ?? '').toLowerCase();
    const scope: Scope = (q === 'monthly' || q === 'yearly' || q === 'overall') ? q : DEFAULT_SCOPE;

    // Parse year/month from URL (provide sensible defaults)
    const now = new Date();
    const rawYear = url.searchParams.get('year');
    const rawMonth = url.searchParams.get('month');

    const year = scope === 'overall' ? undefined : (rawYear ? Number(rawYear) : now.getFullYear());
    const month = scope === 'monthly' ? (rawMonth ? Number(rawMonth) : (now.getMonth() + 1)) : undefined;

    // Use your imported helper
    const raw = await getLeaderboard(scope, {year, month}, fetch);

    // Expecting an array of players with { player_name, active, rating: { mu_*, sigma_* } }
    const filtered = Array.isArray(raw)
        ? raw.filter((p: any) => p?.active === true)
            .filter((p: any) => (p?.games_played > 0)) : [];
    const players: PlayerRow[] = filtered
        .map((p: any) => {
            const rating = p?.rating ?? {};
            const mu = p?.mu

            const sigma =
                scope === 'monthly' ? rating.sigma_monthly :
                    scope === 'yearly' ? rating.sigma_yearly :
                        rating.sigma_overall;

            const muNum = Number(mu) || 0;
            const sigmaNum = Number(sigma) || 0;
            return {
                id: Number(p.id) || 0,
                name: p.player_name ?? p.name ?? 'Inconnu',
                wins: p.wins,
                losses: p.games_played - p.wins,
                elo: Math.round(muNum)
            };
        })
        .sort((a, b) => b.elo - a.elo);

    return {
        scope,
        year: year ?? undefined,
        month: month ?? undefined,
        players
    };
};
