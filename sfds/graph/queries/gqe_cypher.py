"""
GQL-SFDS — Named Cypher Query Library for Graph Query Engine v3.3

Each query is a SEMANTIC INTENT, not just a data retrieval operation.
The comments describe what the AI is REASONING ABOUT, not what it is fetching.

Usage:
    from graph.queries.gqe_cypher import GQL
    results = session.run(GQL.ACTIVE_LOOPS, user_id=uid, max_hops=4)

Design:
    - All queries are parameterized (never string-interpolated)
    - All queries include semantic intent comments
    - Queries are grouped by reasoning mode
    - Each query corresponds to one GQE pipeline step
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class _GQL:
    """
    GQL-SFDS Extension Cypher Query Registry.

    MODE 1 — STRUCTURAL TRAVERSAL
    MODE 2 — LOOP SIMULATION
    MODE 3 — BREAKPOINT DETECTION
    MODE 4 — PRINCIPLE ACTIVATION
    """

    # ── MODE 1: STRUCTURAL TRAVERSAL ─────────────────────────────────────────

    # SEMANTIC INTENT: "What causal structure is this user currently embedded in?"
    # Traverses up to N hops from the user's active state node.
    # Returns the full neighborhood subgraph for structural interpretation.
    STRUCTURAL_NEIGHBORHOOD: str = """
        MATCH (u:UserStateNode {user_id: $user_id})
        CALL apoc.path.subgraphNodes(u, {
            relationshipFilter: "CAUSES>|LEADS_TO>|REINFORCES>",
            maxLevel: $max_hops
        })
        YIELD node
        WITH collect(node) AS nodes
        UNWIND nodes AS n
        MATCH (n)-[r:CAUSES|LEADS_TO|REINFORCES]->(m)
        WHERE m IN nodes
        RETURN
            n.type        AS from_node,
            labels(n)[0]  AS from_label,
            type(r)        AS edge_type,
            r.pattern_id   AS pattern_id,
            m.type         AS to_node,
            labels(m)[0]  AS to_label
        ORDER BY from_label DESC
    """

    # SEMANTIC INTENT: "What is the nearest causal chain from this emotion to outcome?"
    # Traces CAUSES edges forward from a starting emotion.
    # Used in Step 2 (Causal Interpretation).
    CAUSAL_CHAIN_FROM_EMOTION: str = """
        MATCH path = (e:EmotionNode {type: $emotion_type})
                     -[:CAUSES|LEADS_TO*1..$max_hops]->
                     (o)
        WHERE NOT (o)-[:CAUSES|LEADS_TO]->()
           OR $include_loops = true
        RETURN
            [node IN nodes(path) | node.type]       AS chain,
            [rel  IN relationships(path) | type(rel)] AS edge_types,
            length(path)                              AS depth,
            last(nodes(path)).type                    AS endpoint
        ORDER BY depth ASC
        LIMIT $limit
    """

    # SEMANTIC INTENT: "Which behavioral patterns are structurally active for this user?"
    # Finds nodes that appear in multiple pattern chains — high structural centrality.
    PATTERN_CENTRALITY: str = """
        MATCH (n)
        WHERE n.category = $category
        WITH n, COUNT { (n)-[:CAUSES|LEADS_TO]->() } AS out_degree,
                COUNT { ()-[:CAUSES|LEADS_TO]->(n) } AS in_degree
        WHERE out_degree + in_degree >= $min_degree
        RETURN
            n.type              AS node_type,
            labels(n)[0]        AS node_label,
            n.category          AS category,
            out_degree,
            in_degree,
            out_degree + in_degree AS total_degree
        ORDER BY total_degree DESC
        LIMIT 8
    """

    # ── MODE 2: LOOP SIMULATION ───────────────────────────────────────────────

    # SEMANTIC INTENT: "Is this user inside a self-reinforcing loop?"
    # Finds cycles by detecting REINFORCES edges that close a causal chain.
    # This is the core loop detection query.
    ACTIVE_LOOPS: str = """
        MATCH (u:UserStateNode {user_id: $user_id})-[:HAS_STATE*0..2]->(entry)
        MATCH path = (entry)-[:CAUSES|LEADS_TO*2..$max_hops]->(closer)
        MATCH (closer)-[r:REINFORCES]->(back)
        WHERE back = entry OR back.type = entry.type
        RETURN
            [node IN nodes(path) | node.type]       AS loop_chain,
            closer.type                              AS reinforcer_node,
            back.type                                AS loop_closes_at,
            r.pattern_id                             AS pattern_id,
            r.loop_type                              AS loop_type,
            length(path) + 1                         AS loop_length
        ORDER BY loop_length ASC
        LIMIT 5
    """

    # SEMANTIC INTENT: "If no intervention occurs, where does this loop lead next?"
    # Simulates 1–3 forward steps from current position.
    # Used in Step 4 (Simulation).
    SIMULATE_FORWARD: str = """
        MATCH (current {type: $current_node_type})
        MATCH path = (current)-[:CAUSES|LEADS_TO*1..$steps]->
                     (future)
        RETURN
            current.type                                 AS start_node,
            [node IN nodes(path) | node.type]            AS forward_chain,
            [rel  IN relationships(path) | type(rel)]    AS transitions,
            last(nodes(path)).type                       AS predicted_endpoint,
            length(path)                                 AS steps_ahead
        ORDER BY steps_ahead ASC
        LIMIT $limit
    """

    # SEMANTIC INTENT: "How entrenched is this loop — how many times has it fired?"
    # Counts REINFORCES edge recurrence for this user.
    LOOP_INTENSITY: str = """
        MATCH (u:UserStateNode {user_id: $user_id})-[:HAS_STATE*0..3]->(n)
        MATCH (n)-[r:REINFORCES]->(target)
        WHERE $pattern_id = '' OR r.pattern_id = $pattern_id
        RETURN
            r.pattern_id                    AS pattern_id,
            r.loop_type                     AS loop_type,
            COUNT(r)                        AS recurrence_count,
            MIN(r.timestamp)                AS first_seen,
            MAX(r.timestamp)                AS last_seen,
            toFloat(COUNT(r)) * 0.1         AS raw_intensity
        ORDER BY recurrence_count DESC
        LIMIT 5
    """

    # ── MODE 3: BREAKPOINT DETECTION ─────────────────────────────────────────

    # SEMANTIC INTENT: "Where is the weakest link in this causal chain?"
    # Finds LEADS_TO edges with lowest strength property.
    # Low-strength edges = highest leverage intervention points.
    WEAKEST_EDGE_IN_LOOP: str = """
        MATCH (n)-[r:LEADS_TO]->(m)
        WHERE r.pattern_id = $pattern_id
          AND r.strength IS NOT NULL
        RETURN
            n.type              AS from_node,
            labels(n)[0]        AS from_label,
            r.strength          AS edge_strength,
            r.pattern_id        AS pattern_id,
            m.type              AS to_node,
            labels(m)[0]        AS to_label
        ORDER BY r.strength ASC
        LIMIT 3
    """

    # SEMANTIC INTENT: "Which node in this loop has the most incoming causal paths?"
    # High in-degree = loop convergence point = highest leverage target.
    CONVERGENCE_POINTS: str = """
        MATCH (n)<-[:CAUSES|LEADS_TO]-(upstream)
        WHERE n.pattern_id = $pattern_id
           OR upstream.pattern_id = $pattern_id
        WITH n,
             COUNT(upstream)     AS in_degree,
             labels(n)[0]        AS node_label,
             n.category          AS category
        WHERE in_degree >= 2
        RETURN
            n.type      AS node_type,
            node_label,
            category,
            in_degree,
            CASE node_label
                WHEN 'PrincipleNode' THEN 1.0
                WHEN 'EmotionNode'   THEN 0.95
                WHEN 'MotiveNode'    THEN 0.90
                WHEN 'BehaviorNode'  THEN 0.65
                WHEN 'OutcomeNode'   THEN 0.30
                ELSE 0.50
            END AS leverage_score
        ORDER BY leverage_score DESC, in_degree DESC
        LIMIT 4
    """

    # SEMANTIC INTENT: "What is the earliest node in this causal chain?"
    # The root cause — earliest point where intervention is most fundamental.
    ROOT_CAUSE: str = """
        MATCH (root)-[:CAUSES|LEADS_TO*1..6]->(target {type: $target_node})
        WHERE NOT ()-[:CAUSES|LEADS_TO]->(root)
        RETURN
            root.type           AS root_node,
            labels(root)[0]     AS root_label,
            root.category       AS root_category,
            COUNT(*)            AS path_count
        ORDER BY path_count DESC
        LIMIT 3
    """

    # ── MODE 4: PRINCIPLE ACTIVATION ─────────────────────────────────────────

    # SEMANTIC INTENT: "Which principles structurally break this behavioral loop?"
    # Traverses BREAKS edges from PrincipleNodes to loop members.
    PRINCIPLES_THAT_BREAK: str = """
        MATCH (p:PrincipleNode)-[b:BREAKS]->(target)
        WHERE b.pattern_id = $pattern_id
           OR target.type IN $loop_chain
        RETURN
            p.id                AS principle_id,
            p.label             AS principle_label,
            p.category          AS principle_category,
            p.action_type       AS action_type,
            target.type         AS breaks_node,
            labels(target)[0]   AS target_label,
            CASE labels(target)[0]
                WHEN 'MotiveNode'    THEN 0.90
                WHEN 'EmotionNode'   THEN 0.85
                WHEN 'BehaviorNode'  THEN 0.70
                ELSE 0.60
            END AS structural_effectiveness
        ORDER BY structural_effectiveness DESC
        LIMIT 5
    """

    # SEMANTIC INTENT: "Which principles are semantically relevant to this user's current state?"
    # Used when no direct BREAKS edge is found — falls back to category matching.
    PRINCIPLES_BY_CATEGORY: str = """
        MATCH (p:PrincipleNode)
        WHERE p.category IN $categories
        RETURN
            p.id            AS principle_id,
            p.label         AS principle_label,
            p.category      AS principle_category,
            p.action_type   AS action_type,
            0.60            AS structural_effectiveness
        ORDER BY p.category ASC
        LIMIT 5
    """

    # ── COMPOSITE: Full reasoning subgraph for synthesis step ────────────────

    # SEMANTIC INTENT: "Give me everything I need to reason about this user's situation."
    # Single composite query for Step 7 (Synthesis) input.
    FULL_REASONING_SUBGRAPH: str = """
        MATCH (u:UserStateNode {user_id: $user_id})

        // Active emotion + motive state
        OPTIONAL MATCH (u)-[:HAS_STATE]->(e:EmotionNode)
        OPTIONAL MATCH (u)-[:HAS_STATE]->(m:MotiveNode)

        // Immediate causal neighbors (1-hop)
        OPTIONAL MATCH (e)-[r1:CAUSES|LEADS_TO]->(b1)
        OPTIONAL MATCH (m)-[r2:CAUSES|LEADS_TO]->(b2)

        // Loop closures (REINFORCES back-edges)
        OPTIONAL MATCH (b1)-[rr:REINFORCES]->(loop_back)

        // Applicable principles
        OPTIONAL MATCH (p:PrincipleNode)-[:BREAKS]->(b1)

        RETURN
            e.type              AS active_emotion,
            e.category          AS emotion_category,
            m.type              AS active_motive,
            collect(DISTINCT b1.type)   AS immediate_behaviors,
            collect(DISTINCT b2.type)   AS motive_behaviors,
            loop_back.type              AS loop_closes_at,
            rr.pattern_id               AS active_pattern_id,
            collect(DISTINCT p.label)   AS applicable_principles,
            collect(DISTINCT p.id)      AS principle_ids
        LIMIT 1
    """


GQL = _GQL()
