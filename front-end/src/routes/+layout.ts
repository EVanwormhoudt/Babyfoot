import type {LayoutLoad} from './$types';
import {getPlayers} from '$lib/api/players';

export type NamesPrivacySession = {
    configured: boolean;
    can_see_names: boolean;
};

async function getNamesPrivacySession(eventFetch: typeof fetch): Promise<NamesPrivacySession> {
    const res = await eventFetch('/api/privacy/names/session', {
        credentials: 'include'
    });
    if (!res.ok) {
        throw new Error('Impossible de charger la session de confidentialite');
    }
    return res.json() as Promise<NamesPrivacySession>;
}

export const load: LayoutLoad = async ({fetch}) => {
    let privacySession: NamesPrivacySession = {
        configured: false,
        can_see_names: true
    };

    try {
        privacySession = await getNamesPrivacySession(fetch);
    } catch {
        // Keep the app usable if the privacy status endpoint is unavailable.
    }

    try {
        const playersLite = await getPlayers(fetch);
        return {playersLite, privacySession};
    } catch {
        return {playersLite: [], privacySession};
    }
};
