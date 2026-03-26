import type {PageLoad} from './$types';
import {getPlayers} from "$lib/api/players";

export const load: PageLoad = async ({fetch}) => {
    const playersLite = await getPlayers(fetch);
    return {playersLite};
};
