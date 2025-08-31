import type {PageLoad} from './$types';
import {getLeaderboard} from '$lib/api/players';

export const ssr = false; // client-only to avoid eager SSR fetches

type Scope = 'monthly' | 'yearly' | 'overall';
type PlayerRow = { name: string; wins: number; losses: number; elo: number };

const DEFAULT_SCOPE: Scope = 'yearly';

export const load: PageLoad = async ({fetch, url}) => {
    const q = (url.searchParams.get('scope') ?? '').toLowerCase();
    const scope: Scope = (q === 'monthly' || q === 'yearly' || q === 'overall') ? q : DEFAULT_SCOPE;

    // Use your imported helper
    const raw = await getLeaderboard(scope, fetch);

    // Expecting an array of players with { player_name, active, rating: { mu_*, sigma_* } }
    const filtered = Array.isArray(raw) ? raw.filter((p: any) => p?.active === true) : [];
    console.log(raw);
    const players: PlayerRow[] = filtered
        .map((p: any) => {
            const rating = p?.rating ?? {};
            const mu =
                scope === 'monthly' ? rating.mu_monthly :
                    scope === 'yearly' ? rating.mu_yearly :
                        rating.mu_overall;

            const sigma =
                scope === 'monthly' ? rating.sigma_monthly :
                    scope === 'yearly' ? rating.sigma_yearly :
                        rating.sigma_overall;

            const muNum = Number(mu) || 0;
            const sigmaNum = Number(sigma) || 0;
            console.log(p)
            return {
                name: p.player_name ?? p.name ?? 'Unknown',
                wins: p.wins,          // placeholders as in your original
                losses: p.games_played - p.wins,  // placeholders
                elo: Math.round(muNum)
            };
        })
        .sort((a, b) => b.elo - a.elo);

    return {scope, players};
};
