export type PlayerRead = {
    id: number;
    active: boolean;
    rating?: any | null;
    // Include fields you have in PlayerCreate as needed (name, avatar, etc.)
    player_name?: string;
};

export type TeamRead = {
    player_id: number;
    team_number: 1 | 2;
    player: PlayerRead;
};

export type GameRead = {
    id: number;
    game_timestamp: string; // ISO string
    result_team1: number;
    result_team2: number;
    teams: TeamRead[];
};
