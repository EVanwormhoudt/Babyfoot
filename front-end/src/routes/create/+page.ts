import type {PageLoad} from './$types';

export const load: PageLoad = async ({parent}) => {
    const {playersLite} = await parent();
    return {playersLite};
};
