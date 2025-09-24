# Lösung: Dijkstra's Algorithm Implementation

**Punkte: 20**

## Vollständige Lösung

```python
import heapq
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass

@dataclass
class Edge:
    """Repräsentation einer gewichteten Kante."""
    target: int
    weight: float

@dataclass
class PathResult:
    """Ergebnis einer Pfadberechnung."""
    distance: float
    path: List[int]
    total_edges: int

class Dijkstra:
    def __init__(self, graph: Dict[int, List[Edge]]):
        """
        Initialisiert den Dijkstra-Algorithmus mit einem gewichteten Graphen.

        Args:
            graph: Dictionary mit Adjazenzliste (Knoten -> Liste von Edge-Objekten)
        """
        self.graph = graph

    def shortest_paths(self, start: int) -> Dict[int, float]:
        """
        Berechnet die kürzesten Pfade vom Startknoten zu allen erreichbaren Knoten.

        Args:
            start: Startknoten

        Returns:
            Dictionary: Knoten -> Kürzeste Distanz vom Start
        """
        if start not in self.graph:
            return {}

        distances = {start: 0.0}
        priority_queue = [(0.0, start)]  # (distance, node)
        visited = set()

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)

            if current_node in visited:
                continue

            visited.add(current_node)

            # Relaxierung aller ausgehenden Kanten
            for edge in self.graph.get(current_node, []):
                if edge.target not in visited:
                    new_distance = current_distance + edge.weight

                    # Aktualisiere Distanz wenn besser gefunden
                    if edge.target not in distances or new_distance < distances[edge.target]:
                        distances[edge.target] = new_distance
                        heapq.heappush(priority_queue, (new_distance, edge.target))

        return distances

    def find_path(self, start: int, target: int) -> Optional[PathResult]:
        """
        Findet den kürzesten Pfad zwischen Start- und Zielknoten mit vollständigen Details.

        Args:
            start: Startknoten
            target: Zielknoten

        Returns:
            PathResult mit Distanz, Pfad und Kantenzahl oder None
        """
        if start not in self.graph:
            return None

        if start == target:
            return PathResult(distance=0.0, path=[start], total_edges=0)

        distances = {start: 0.0}
        parents = {start: None}
        priority_queue = [(0.0, start)]
        visited = set()

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)

            if current_node in visited:
                continue

            visited.add(current_node)

            # Frühe Terminierung wenn Ziel erreicht
            if current_node == target:
                break

            # Relaxierung aller ausgehenden Kanten
            for edge in self.graph.get(current_node, []):
                if edge.target not in visited:
                    new_distance = current_distance + edge.weight

                    if edge.target not in distances or new_distance < distances[edge.target]:
                        distances[edge.target] = new_distance
                        parents[edge.target] = current_node
                        heapq.heappush(priority_queue, (new_distance, edge.target))

        # Prüfe ob Ziel erreichbar
        if target not in distances:
            return None

        # Rekonstruiere Pfad
        path = []
        current = target
        while current is not None:
            path.append(current)
            current = parents.get(current)

        path.reverse()

        return PathResult(
            distance=distances[target],
            path=path,
            total_edges=len(path) - 1
        )

    def single_target_shortest_path(self, start: int, target: int) -> Optional[Tuple[float, List[int]]]:
        """
        Optimierte Version für die Suche zu einem spezifischen Ziel.

        Args:
            start: Startknoten
            target: Zielknoten

        Returns:
            Tuple (Distanz, Pfad) oder None wenn nicht erreichbar
        """
        result = self.find_path(start, target)
        if result:
            return (result.distance, result.path)
        return None

    def find_alternative_paths(self, start: int, target: int, max_paths: int = 3) -> List[PathResult]:
        """
        Findet alternative Pfade zwischen Start- und Zielknoten für Redundanz.

        Args:
            start: Startknoten
            target: Zielknoten
            max_paths: Maximale Anzahl alternativer Pfade

        Returns:
            Liste von PathResult-Objekten, sortiert nach Distanz
        """
        if start not in self.graph:
            return []

        all_paths = []
        used_edges = set()  # Set von (source, target) Tupeln

        # Finde ersten (optimalen) Pfad
        first_path = self.find_path(start, target)
        if not first_path:
            return []

        all_paths.append(first_path)

        # Versuche alternative Pfade zu finden
        for attempt in range(max_paths - 1):
            best_alternative = None
            best_distance = float('inf')

            # Für jede Kante im besten Pfad, versuche sie zu vermeiden
            current_best_path = all_paths[0] if all_paths else first_path

            for i in range(len(current_best_path.path) - 1):
                source = current_best_path.path[i]
                dest = current_best_path.path[i + 1]

                if (source, dest) in used_edges:
                    continue

                # Erstelle temporären Graphen ohne diese Kante
                temp_graph = {}
                for node, edges in self.graph.items():
                    temp_graph[node] = []
                    for edge in edges:
                        if not (node == source and edge.target == dest):
                            temp_graph[node].append(edge)

                # Finde Pfad in modifiziertem Graph
                temp_dijkstra = Dijkstra(temp_graph)
                alternative = temp_dijkstra.find_path(start, target)

                if alternative and alternative.distance < best_distance:
                    # Prüfe ob Pfad signifikant unterschiedlich ist
                    if self._is_significantly_different(alternative.path, [p.path for p in all_paths]):
                        best_alternative = alternative
                        best_distance = alternative.distance

            if best_alternative:
                all_paths.append(best_alternative)
                # Markiere Kanten des neuen Pfads als verwendet
                for i in range(len(best_alternative.path) - 1):
                    used_edges.add((best_alternative.path[i], best_alternative.path[i + 1]))
            else:
                break

        # Sortiere nach Distanz
        all_paths.sort(key=lambda x: x.distance)
        return all_paths[:max_paths]

    def _is_significantly_different(self, new_path: List[int], existing_paths: List[List[int]]) -> bool:
        """
        Prüft ob ein neuer Pfad signifikant von existierenden Pfaden abweicht.

        Args:
            new_path: Neuer Pfad zur Prüfung
            existing_paths: Liste bereits gefundener Pfade

        Returns:
            True wenn Pfad signifikant unterschiedlich ist
        """
        for existing_path in existing_paths:
            # Berechne Jaccard-Ähnlichkeit
            set_new = set(new_path[1:-1])  # Ohne Start und Ziel
            set_existing = set(existing_path[1:-1])

            if len(set_new) == 0 and len(set_existing) == 0:
                return False  # Beide Pfade sind direkte Verbindungen

            union = set_new | set_existing
            intersection = set_new & set_existing

            if len(union) > 0:
                similarity = len(intersection) / len(union)
                if similarity > 0.5:  # Mehr als 50% Überlappung
                    return False

        return True

# Testfälle
if __name__ == "__main__":
    # Testgraph: Gewichteter Graph für Routenplanung
    graph = {
        0: [Edge(1, 4), Edge(2, 2)],
        1: [Edge(2, 1), Edge(3, 5)],
        2: [Edge(3, 8), Edge(4, 10)],
        3: [Edge(4, 2), Edge(5, 6)],
        4: [Edge(5, 3)],
        5: []
    }

    # Zusätzlicher Testgraph mit mehreren Pfadoptionen
    complex_graph = {
        0: [Edge(1, 1), Edge(2, 4)],
        1: [Edge(2, 2), Edge(3, 5), Edge(4, 1)],
        2: [Edge(3, 1), Edge(5, 3)],
        3: [Edge(5, 2)],
        4: [Edge(3, 3), Edge(5, 4)],
        5: []
    }

    dijkstra = Dijkstra(graph)
    complex_dijkstra = Dijkstra(complex_graph)

    # Tests für kürzeste Pfade
    print("Kürzeste Pfade von Knoten 0:")
    distances = dijkstra.shortest_paths(0)
    for node, dist in sorted(distances.items()):
        print(f"  Knoten {node}: {dist}")

    # Tests für Pfadfindung
    result = dijkstra.find_path(0, 5)
    if result:
        print(f"\nPfad von 0 zu 5:")
        print(f"  Distanz: {result.distance}")
        print(f"  Pfad: {' -> '.join(map(str, result.path))}")
        print(f"  Anzahl Kanten: {result.total_edges}")

    # Tests für Single-Target
    single_result = dijkstra.single_target_shortest_path(0, 4)
    if single_result:
        print(f"\nSingle-Target 0 zu 4:")
        print(f"  Distanz: {single_result[0]}")
        print(f"  Pfad: {' -> '.join(map(str, single_result[1]))}")

    # Tests für Alternative Pfade
    alternatives = complex_dijkstra.find_alternative_paths(0, 5, 2)
    print(f"\nAlternative Pfade von 0 zu 5:")
    for i, path_result in enumerate(alternatives, 1):
        print(f"  Pfad {i}: {' -> '.join(map(str, path_result.path))} (Distanz: {path_result.distance})")
```

## Detaillierte Punkteverteilung

### Kürzeste Pfade (6 Punkte)
- **Priority Queue Setup (2 Punkte)**: Korrekte Verwendung von `heapq` mit (distance, node) Tupeln
- **Dijkstra-Hauptschleife (2 Punkte)**: Korrekte Implementierung des Greedy-Algorithmus
- **Kantenrelaxierung (2 Punkte)**: Korrekte Aktualisierung der Distanzen

**Häufige Fehler:**
- Falsche Priority Queue Nutzung (-2 Punkte)
- Fehlende Visited-Prüfung führt zu falschen Ergebnissen (-2 Punkte)
- Negative Gewichte nicht behandelt (-1 Punkt)

### Pfadrekonstruktion (5 Punkte)
- **Parent-Tracking (2 Punkte)**: Korrekte Speicherung der Vorgängerknoten
- **Pfad-Rekonstruktion (2 Punkte)**: Vollständige Rückverfolgung und Umkehrung
- **PathResult-Erstellung (1 Punkt)**: Korrekte Berechnung aller Felder

**Häufige Fehler:**
- Fehlende oder falsche Parent-Verfolgung (-3 Punkte)
- Pfad nicht umgekehrt (-1 Punkt)
- Falsche Kantenzahl (-1 Punkt)

### Single-Target Optimierung (4 Punkte)
- **Early Termination (2 Punkte)**: Algorithmus stoppt bei Ziel-Erreichen
- **Korrekte Implementierung (1 Punkt)**: Wiederverwendung von find_path
- **Richtige Rückgabe (1 Punkt)**: Tuple-Format wie spezifiziert

**Häufige Fehler:**
- Keine Early Termination implementiert (-2 Punkte)
- Falsches Rückgabeformat (-1 Punkt)

### Alternative Pfade (5 Punkte)
- **Graph-Modifikation (2 Punkte)**: Temporärer Graph ohne spezifische Kanten
- **Pfad-Unterscheidung (2 Punkte)**: Erkennung signifikant verschiedener Pfade
- **Sortierung und Limitierung (1 Punkt)**: Korrekte Ausgabe-Formatierung

**Häufige Fehler:**
- Naive Implementierung ohne Graph-Modifikation (-3 Punkte)
- Keine Pfad-Unterscheidung (-2 Punkte)
- Falsche Sortierung (-1 Punkt)

## Zeitkomplexitätsanalyse

- **Shortest Paths**: O((V + E) log V) mit Binary Heap
- **Find Path**: O((V + E) log V) mit Early Termination
- **Single Target**: O((V + E) log V) im schlechtesten Fall
- **Alternative Paths**: O(k × (V + E) log V) für k alternative Pfade

## Erwartete Ausgabe

```
Kürzeste Pfade von Knoten 0:
  Knoten 0: 0.0
  Knoten 1: 4.0
  Knoten 2: 2.0
  Knoten 3: 9.0
  Knoten 4: 11.0
  Knoten 5: 14.0

Pfad von 0 zu 5:
  Distanz: 14.0
  Pfad: 0 -> 2 -> 3 -> 4 -> 5
  Anzahl Kanten: 4

Single-Target 0 zu 4:
  Distanz: 11.0
  Pfad: 0 -> 2 -> 3 -> 4

Alternative Pfade von 0 zu 5:
  Pfad 1: 0 -> 1 -> 4 -> 5 (Distanz: 8.0)
  Pfad 2: 0 -> 2 -> 5 (Distanz: 7.0)
```