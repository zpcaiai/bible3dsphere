-- Cache of walking-route geometries (OpenRouteService foot-walking) so we don't
-- re-hit the routing API for the same biblical journey legs.
CREATE TABLE IF NOT EXISTS route_cache (
    cache_key  TEXT PRIMARY KEY,        -- sha1 of profile + rounded coordinates
    geometry   JSONB NOT NULL,          -- [[lng,lat], ...]
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
