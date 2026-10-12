from functools import lru_cache
import networkx as nx
from fastapi import HTTPException
from backend.config import settings
from backend.external_services.geolocation.service import distance
from backend.intelligence.risk_algorithm.engine import line_distance_m, RULES


@lru_cache(maxsize=2)
def graph_for(transport):
    import osmnx as ox
    path = settings().osm_directory / f'salamanca_{transport}.graphml'
    if not path.exists():
        raise HTTPException(503, 'Las rutas locales todavía no están disponibles. Inténtalo más tarde.')
    return ox.load_graphml(path)


def safe_corridor(origin, destination, transport, hazards):
    """Dirigido para auto, red peatonal independiente. Nunca descargar durante una consulta."""
    graph = graph_for(transport).copy()
    nearest = lambda p: min(graph.nodes, key=lambda n: distance(p, [graph.nodes[n]['x'], graph.nodes[n]['y']]))
    start, end = nearest(origin), nearest(destination)
    if any(distance(p, [graph.nodes[n]['x'], graph.nodes[n]['y']]) > 300 for p, n in [(origin, start), (destination, end)]):
        return []
    for u, v, key, edge in list(graph.edges(keys=True, data=True)):
        shape = edge.get('geometry')
        coords = list(shape.coords) if shape is not None else [[graph.nodes[u]['x'], graph.nodes[u]['y']], [graph.nodes[v]['x'], graph.nodes[v]['y']]]
        penalties = [(h, line_distance_m(coords, [h.longitude, h.latitude]), c) for h, c in hazards]
        if any(c.critical and d <= RULES['critical_distance_m'] for h, d, c in penalties):
            graph.remove_edge(u, v, key)
        else:
            edge['safe_cost'] = float(edge['length']) * (1 + RULES['corridor_penalty'] * sum(c.severity * h.confidence * max(0, 1-d/RULES['influence_radius_m']) for h, d, c in penalties))
    try:
        path = nx.shortest_path(graph, start, end, weight='safe_cost')
    except nx.NetworkXNoPath:
        return []
    # Diez puntos intermedios como maximo, tal como permite Azure Maps.
    if len(path) <= 2:
        return []
    indices = sorted(set(round((len(path)-1)*i/11) for i in range(1, 11)))
    return [[float(graph.nodes[path[i]]['x']), float(graph.nodes[path[i]]['y'])] for i in indices if 0 < i < len(path)-1]
