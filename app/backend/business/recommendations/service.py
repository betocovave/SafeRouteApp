from backend.intelligence.risk_algorithm.engine import RULES


def recommendation(routes, tolerance):
    if not routes:
        return None, 'No se encontró una ruta disponible.'
    fastest = min(r['duration_s'] for r in routes)
    suitable = [r for r in routes if not r['evaluation']['critical'] and r['duration_s'] <= fastest * RULES['tolerance_detour_ratio'][tolerance]]
    if not suitable:
        return None, 'Riesgo crítico o desvío excesivo. Evita continuar hacia la zona afectada y detente únicamente en un lugar que puedas verificar como seguro.'
    known = [r for r in suitable if r['evaluation']['risk_index'] is not None]
    selected = min(known or suitable, key=lambda r: (r['evaluation']['risk_index'] if r['evaluation']['risk_index'] is not None else 0, r['duration_s']))
    warning = 'Información insuficiente para comparar la seguridad de todas las alternativas.' if len(known) != len(suitable) else None
    return selected['id'], warning
