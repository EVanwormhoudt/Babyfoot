import {error} from '@sveltejs/kit';
import type {PageLoad} from './$types';
import {ApiError, getGame} from '$lib/api/matches';

export const load: PageLoad = async ({params, fetch}) => {
    const id = Number(params.id);
    if (!Number.isInteger(id) || id <= 0) {
        throw error(404, 'Match introuvable');
    }

    try {
        const game = await getGame(id, fetch);
        return {game};
    } catch (err) {
        if (err instanceof ApiError) {
            if (err.status === 404) {
                throw error(404, 'Match introuvable');
            }
            throw error(err.status, err.message);
        }
        throw error(500, 'Impossible de charger le match');
    }
};
