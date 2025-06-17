import random

# segundos por fase
TRAFFIC_LIGHT_CYCLE = 40 
ZONE_DIRECTIONS = {
    0: "east",   # Onda de este a oeste
    1: "south",  # De norte a sur
    2: "north",  # De sur a norte
}
NUM_ZONES = 3
ZONE_WIDTH = 0.01  # Longitud aproximada para dividir zonas

def initialize_traffic_lights(street_graph, traffic_lights):

    candidates = [n for n in street_graph.nodes() if len(list(street_graph.neighbors(n))) >= 4]
    selected = random.sample(candidates, min(1500, len(candidates)))

    zone_groups = {i: [] for i in range(NUM_ZONES)}

    for node in selected:
        lon = float(street_graph.nodes[node]["lon"])
        zone_index = int((lon + 0.015) / ZONE_WIDTH) % NUM_ZONES
        zone_groups[zone_index].append(node)

    for zone_index, nodes in zone_groups.items():
        direction = ZONE_DIRECTIONS.get(zone_index, "east")

        # Ordena los nodos en la dirección de la onda verde
        if direction == "east":
            nodes.sort(key=lambda nid: float(street_graph.nodes[nid]["lon"]))
        elif direction == "west":
            nodes.sort(key=lambda nid: -float(street_graph.nodes[nid]["lon"]))
        elif direction == "north":
            nodes.sort(key=lambda nid: float(street_graph.nodes[nid]["lat"]))
        elif direction == "south":
            nodes.sort(key=lambda nid: -float(street_graph.nodes[nid]["lat"]))

        for idx, node in enumerate(nodes):
            lat = float(street_graph.nodes[node]["lat"])
            lon = float(street_graph.nodes[node]["lon"])
            phase_offset = (idx * 3) % (TRAFFIC_LIGHT_CYCLE * 2)

            traffic_lights[node] = {
                "state": "green",
                "timer": phase_offset,
                "lat": lat,
                "lon": lon,
                "zone": zone_index,
                "direction": direction
            }

    print("Semáforos por zona y dirección sincronizados.")

def update_traffic_lights(traffic_lights):
    for light in traffic_lights.values():
        light["timer"] = (light["timer"] + 1) % (TRAFFIC_LIGHT_CYCLE * 2)
        if light["timer"] < TRAFFIC_LIGHT_CYCLE:
            light["state"] = "green"
        else:
            light["state"] = "red"
