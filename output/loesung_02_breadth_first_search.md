# Lösung: Breadth-First Search (BFS) Implementation

**Punkte: 18**

## Vollständige Lösung

```python
from collections import deque
from typing import List, Dict, Optional, Set, Tuple

class BFS:
    def __init__(self, graph: Dict[int, List[int]]):
        """
        Initialisiert die BFS-Klasse mit einem Graphen.

        Args:
            graph: Dictionary mit Adjazenzliste (Knoten -> Liste der Nachbarn)
        """
        self.graph = graph

    def traverse(self, start: int) -> List[int]:
        """
        Führt BFS-Traversierung vom Startknoten aus durch.

        Args:
            start: Startknoten für die Traversierung

        Returns:
            Liste der Knoten in der Reihenfolge ihres Besuchs
        """
        if start not in self.graph:
            return []

        visited = set()
        queue = deque([start])
        result = []

        visited.add(start)

        while queue:
            current = queue.popleft()
            result.append(current)

            # Nachbarn in sortierter Reihenfolge für deterministische Ergebnisse
            for neighbor in sorted(self.graph.get(current, [])):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return result

    def shortest_paths(self, start: int) -> Dict[int, int]:
        """
        Berechnet die kürzesten Pfade vom Startknoten zu allen erreichbaren Knoten.

        Args:
            start: Startknoten

        Returns:
            Dictionary: Knoten -> Kürzeste Distanz vom Start
        """
        if start not in self.graph:
            return {}

        distances = {start: 0}
        queue = deque([start])

        while queue:
            current = queue.popleft()
            current_distance = distances[current]

            for neighbor in self.graph.get(current, []):
                if neighbor not in distances:
                    distances[neighbor] = current_distance + 1
                    queue.append(neighbor)

        return distances

    def find_path(self, start: int, target: int) -> Optional[List[int]]:
        """
        Findet den kürzesten Pfad zwischen Start- und Zielknoten.

        Args:
            start: Startknoten
            target: Zielknoten

        Returns:
            Liste der Knoten im kürzesten Pfad (inkl. Start und Ziel)
            None wenn kein Pfad existiert
        """
        if start not in self.graph or target not in self.graph:
            return None

        if start == target:
            return [start]

        queue = deque([start])
        visited = {start}
        parent = {start: None}

        while queue:
            current = queue.popleft()

            for neighbor in self.graph.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = current
                    queue.append(neighbor)

                    if neighbor == target:
                        # Pfad rekonstruieren
                        path = []
                        node = target
                        while node is not None:
                            path.append(node)
                            node = parent[node]
                        return path[::-1]  # Umkehren für Start->Ziel Reihenfolge

        return None  # Kein Pfad gefunden

    def connected_components(self) -> List[List[int]]:
        """
        Findet alle Zusammenhangskomponenten im Graphen.

        Returns:
            Liste von Listen, wobei jede innere Liste eine Komponente darstellt
        """
        visited_global = set()
        components = []

        # Alle Knoten im Graphen berücksichtigen
        all_nodes = set(self.graph.keys())
        for neighbors in self.graph.values():
            all_nodes.update(neighbors)

        for node in sorted(all_nodes):
            if node not in visited_global:
                # Neue Komponente mit BFS erkunden
                component = []
                queue = deque([node])
                visited_local = {node}
                visited_global.add(node)

                while queue:
                    current = queue.popleft()
                    component.append(current)

                    for neighbor in self.graph.get(current, []):
                        if neighbor not in visited_local:
                            visited_local.add(neighbor)
                            visited_global.add(neighbor)
                            queue.append(neighbor)

                components.append(sorted(component))

        # Sortieren nach Größe (größte zuerst)
        components.sort(key=len, reverse=True)
        return components

# Testfälle
if __name__ == "__main__":
    # Testgraph 1: Einfacher verbundener Graph
    graph1 = {
        0: [1, 2],
        1: [0, 3, 4],
        2: [0, 5],
        3: [1],
        4: [1, 5],
        5: [2, 4]
    }

    # Testgraph 2: Graph mit mehreren Komponenten
    graph2 = {
        0: [1],
        1: [0, 2],
        2: [1],
        3: [4],
        4: [3, 5],
        5: [4],
        6: []
    }

    bfs1 = BFS(graph1)
    bfs2 = BFS(graph2)

    # Tests für Traversierung
    print("BFS Traversierung von Knoten 0:", bfs1.traverse(0))

    # Tests für kürzeste Pfade
    print("Kürzeste Pfade von Knoten 0:", bfs1.shortest_paths(0))

    # Tests für Pfadfindung
    print("Pfad von 0 zu 5:", bfs1.find_path(0, 5))
    print("Pfad von 1 zu 4:", bfs1.find_path(1, 4))

    # Tests für Zusammenhangskomponenten
    print("Komponenten in Graph 1:", bfs1.connected_components())
    print("Komponenten in Graph 2:", bfs2.connected_components())
```

## Detaillierte Punkteverteilung

### BFS-Traversierung (5 Punkte)
- **Queue-Verwendung (2 Punkte)**: Korrekte Verwendung von `deque` für FIFO-Verhalten
- **Visited-Set (1 Punkt)**: Vermeidung von Zyklen durch Besuchsmarkierung
- **Korrekte Reihenfolge (2 Punkte)**: Breadth-first Besuchsreihenfolge

**Häufige Fehler:**
- Stack statt Queue verwenden (-2 Punkte)
- Fehlende Visited-Markierung (-1 Punkt)
- Falsche Initialisierung (-1 Punkt)

### Kürzeste Pfade (5 Punkte)
- **Distanz-Tracking (2 Punkte)**: Korrekte Speicherung der Distanzen
- **Incrementelle Distanzen (2 Punkte)**: `current_distance + 1` für Nachbarn
- **Einmalige Besuche (1 Punkt)**: Vermeidung von Distanz-Updates

**Häufige Fehler:**
- Mehrfache Distanz-Updates (-2 Punkte)
- Falsche Distanzberechnung (-2 Punkte)
- Fehlende Startdistanz 0 (-1 Punkt)

### Pfadrekonstruktion (4 Punkte)
- **Parent-Tracking (2 Punkte)**: Korrekte Speicherung der Vorgängerknoten
- **Pfad-Rekonstruktion (1 Punkt)**: Rückverfolgung vom Ziel zum Start
- **Pfad-Umkehrung (1 Punkt)**: Korrekte Start->Ziel Reihenfolge

**Häufige Fehler:**
- Fehlende Parent-Verfolgung (-2 Punkte)
- Falsche Pfad-Reihenfolge (-1 Punkt)
- Endlos-Schleifen bei Rekonstruktion (-2 Punkte)

### Zusammenhangskomponenten (4 Punkte)
- **Globale Visited-Verfolgung (1 Punkt)**: Vermeidung doppelter Komponenten
- **Vollständige Knotenmenge (1 Punkt)**: Berücksichtigung aller Graphknoten
- **Komponentensammlung (1 Punkt)**: Korrekte Gruppierung zusammenhängender Knoten
- **Sortierung nach Größe (1 Punkt)**: Größte Komponenten zuerst

**Häufige Fehler:**
- Nur explizite Knoten berücksichtigen (-1 Punkt)
- Fehlende Sortierung (-1 Punkt)
- Doppelte Knoten in Komponenten (-1 Punkt)

## Zeitkomplexitätsanalyse

- **BFS-Traversierung**: O(V + E)
- **Kürzeste Pfade**: O(V + E)
- **Pfadfindung**: O(V + E) im schlechtesten Fall
- **Zusammenhangskomponenten**: O(V + E) für den gesamten Graphen

Wobei V = Anzahl Knoten, E = Anzahl Kanten.

## Erwartete Ausgabe

```
BFS Traversierung von Knoten 0: [0, 1, 2, 3, 4, 5]
Kürzeste Pfade von Knoten 0: {0: 0, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2}
Pfad von 0 zu 5: [0, 2, 5]
Pfad von 1 zu 4: [1, 4]
Komponenten in Graph 1: [[0, 1, 2, 3, 4, 5]]
Komponenten in Graph 2: [[0, 1, 2], [3, 4, 5], [6]]
```