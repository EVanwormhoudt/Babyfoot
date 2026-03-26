export const CURRENT_PLAYER_STORAGE_KEY = "babyfoot.current_player_id";
export const CURRENT_PLAYER_EVENT = "babyfoot:current-player-changed";

function normalizePlayerId(value: unknown): number | null {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) return null;
    return Math.trunc(parsed);
}

export function getStoredCurrentPlayerId(): number | null {
    if (typeof window === "undefined") return null;
    const raw = window.localStorage.getItem(CURRENT_PLAYER_STORAGE_KEY);
    return normalizePlayerId(raw);
}

export function setStoredCurrentPlayerId(playerId: number | null) {
    if (typeof window === "undefined") return;

    const normalized = normalizePlayerId(playerId);
    if (normalized === null) {
        window.localStorage.removeItem(CURRENT_PLAYER_STORAGE_KEY);
    } else {
        window.localStorage.setItem(CURRENT_PLAYER_STORAGE_KEY, String(normalized));
    }

    window.dispatchEvent(
        new CustomEvent(CURRENT_PLAYER_EVENT, {detail: {playerId: normalized}})
    );
}

export function onCurrentPlayerChange(handler: (playerId: number | null) => void): () => void {
    if (typeof window === "undefined") return () => {};

    const listener = (event: Event) => {
        const custom = event as CustomEvent<{ playerId?: unknown }>;
        const maybePlayerId = custom?.detail?.playerId;
        if (maybePlayerId !== undefined) {
            handler(normalizePlayerId(maybePlayerId));
            return;
        }
        handler(getStoredCurrentPlayerId());
    };

    window.addEventListener(CURRENT_PLAYER_EVENT, listener as EventListener);
    return () => window.removeEventListener(CURRENT_PLAYER_EVENT, listener as EventListener);
}
