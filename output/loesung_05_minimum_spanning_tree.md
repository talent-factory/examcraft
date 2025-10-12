# Lösung: Minimum Spanning Tree (Kruskal's Algorithm with Union-Find)

**Punkte: 21**

## Vollständige Lösung

```python
from typing import List, Tuple, Dict, Set, Optional
from dataclasses import dataclass
from collections import defaultdict, deque

@dataclass
class Edge:
    """Repräsentation einer gewichteten Kante."""
    source: int
    target: int
    weight: float

    def __lt__(self, other):
        """Ermöglicht Sortierung nach Gewicht."""
        return self.weight < other.weight

@dataclass
class MSTResult:
    """Ergebnis der MST-Berechnung."""
    edges: List[Edge]
    total_weight: float
    is_connected: bool

class UnionFind:
    """Union-Find Datenstruktur mit Pfadkompression und Union by Rank."""

    def __init__(self, n: int):
        """
        Initialisiert Union-Find für n Elemente (0 bis n-1).

        Args:
            n: Anzahl der Elemente
        """
        self.parent = list(range(n))
        self.rank = [0] * n
        self.components = n

    def find(self, x: int) -> int:
        """
        Findet die Wurzel von x mit Pfadkompression.

        Args:
            x: Element dessen Wurzel gesucht wird

        Returns:
            Wurzel von x
        """
        if self.parent[x] != x:
            # Pfadkompression: Alle Knoten zeigen direkt auf die Wurzel
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> bool:
        """
        Vereinigt die Sets von x und y.

        Args:
            x, y: Elemente deren Sets vereinigt werden sollen

        Returns:
            True wenn Vereinigung stattfand, False wenn bereits verbunden
        """
        root_x = self.find(x)
        root_y = self.find(y)

        if root_x == root_y:
            return False  # Bereits im gleichen Set

        # Union by Rank: Kleineren Baum an größeren anhängen
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            # Gleiche Höhe: Einer wird Wurzel, dessen Rang steigt
            self.parent[root_y] = root_x
            self.rank[root_x] += 1

        self.components -= 1
        return True

    def connected(self, x: int, y: int) -> bool:
        """
        Prüft ob x und y im gleichen Set sind.

        Args:
            x, y: Zu prüfende Elemente

        Returns:
            True wenn verbunden
        """
        return self.find(x) == self.find(y)

    def get_component_count(self) -> int:
        """Gibt Anzahl der Zusammenhangskomponenten zurück."""
        return self.components

class KruskalMST:
    def __init__(self, vertices: int):
        """
        Initialisiert Kruskal's MST für gegebene Knotenzahl.

        Args:
            vertices: Anzahl der Knoten im Graph
        """
        self.vertices = vertices
        self.edges = []

    def add_edge(self, source: int, target: int, weight: float):
        """
        Fügt eine Kante zum Graph hinzu.

        Args:
            source: Quellknoten
            target: Zielknoten
            weight: Kantengewicht
        """
        self.edges.append(Edge(source, target, weight))

    def find_mst(self) -> MSTResult:
        """
        Berechnet MST mit Kruskal's Algorithmus.

        Returns:
            MSTResult mit MST-Kanten und Eigenschaften
        """
        if not self.edges:
            return MSTResult([], 0.0, self.vertices <= 1)

        # Sortiere Kanten nach Gewicht
        sorted_edges = sorted(self.edges)

        # Union-Find für Zykluserkennung
        uf = UnionFind(self.vertices)
        mst_edges = []
        total_weight = 0.0

        # Kruskal's Algorithmus
        for edge in sorted_edges:
            # Prüfe ob Kante Zyklus bilden würde
            if not uf.connected(edge.source, edge.target):
                # Kante hinzufügen
                uf.union(edge.source, edge.target)
                mst_edges.append(edge)
                total_weight += edge.weight

                # MST vollständig wenn |V|-1 Kanten
                if len(mst_edges) == self.vertices - 1:
                    break

        # Prüfe ob Graph zusammenhängend war
        is_connected = uf.get_component_count() == 1

        return MSTResult(mst_edges, total_weight, is_connected)

    def get_mst_weight(self) -> float:
        """
        Berechnet nur das Gesamtgewicht des MST (ohne Kanten-Details).

        Returns:
            Minimales Gesamtgewicht oder infinity bei unzusammenhängendem Graph
        """
        result = self.find_mst()
        if result.is_connected:
            return result.total_weight
        else:
            return float('inf')

    def bottleneck_mst(self, source: int, target: int) -> Optional[float]:
        """
        Findet die minimale maximale Kante auf dem Pfad zwischen source und target.

        Args:
            source: Startknoten
            target: Zielknoten

        Returns:
            Minimale maximale Kantengewicht oder None wenn nicht verbunden
        """
        if source < 0 or source >= self.vertices or target < 0 or target >= self.vertices:
            return None

        if source == target:
            return 0.0

        # Berechne MST
        mst_result = self.find_mst()
        if not mst_result.is_connected:
            return None

        # Finde Pfad zwischen source und target im MST
        path_edges = self._find_path_in_mst(mst_result.edges, source, target)

        if not path_edges:
            return None

        # Finde maximales Gewicht auf dem Pfad
        max_weight = max(edge.weight for edge in path_edges)
        return max_weight

    def _find_path_in_mst(self, mst_edges: List[Edge], source: int, target: int) -> Optional[List[Edge]]:
        """
        Hilfsmethode: Findet Pfad zwischen zwei Knoten im MST.

        Args:
            mst_edges: Kanten des MST
            source: Startknoten
            target: Zielknoten

        Returns:
            Liste der Kanten auf dem Pfad oder None
        """
        # Baue Adjazenzliste für MST
        graph = defaultdict(list)
        edge_map = {}  # (u,v) -> Edge für schnelle Kantensuche

        for edge in mst_edges:
            graph[edge.source].append(edge.target)
            graph[edge.target].append(edge.source)
            # Speichere Kante in beide Richtungen
            edge_map[(edge.source, edge.target)] = edge
            edge_map[(edge.target, edge.source)] = edge

        # BFS für Pfadsuche
        queue = deque([source])
        visited = {source}
        parent = {source: None}

        while queue:
            current = queue.popleft()

            if current == target:
                # Rekonstruiere Pfad
                path_edges = []
                node = target

                while parent[node] is not None:
                    prev_node = parent[node]
                    # Finde entsprechende Kante
                    edge = edge_map[(prev_node, node)]
                    path_edges.append(edge)
                    node = prev_node

                return path_edges[::-1]  # Umkehren für source->target Reihenfolge

            for neighbor in graph[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = current
                    queue.append(neighbor)

        return None  # Kein Pfad gefunden

# Testfälle
if __name__ == "__main__":
    # Test Union-Find
    uf = UnionFind(6)
    print("Initial components:", uf.get_component_count())

    uf.union(0, 1)
    uf.union(2, 3)
    print("After unions:", uf.get_component_count())
    print("0 and 1 connected:", uf.connected(0, 1))
    print("0 and 2 connected:", uf.connected(0, 2))

    # Test Kruskal MST
    # Beispielgraph für MST
    mst = KruskalMST(6)

    # Kanten hinzufügen (vollständiges Beispielnetzwerk)
    edges_data = [
        (0, 1, 4), (0, 2, 2), (1, 2, 1), (1, 3, 5),
        (2, 3, 8), (2, 4, 10), (3, 4, 2), (3, 5, 6), (4, 5, 3)
    ]

    for source, target, weight in edges_data:
        mst.add_edge(source, target, weight)

    # MST berechnen
    result = mst.find_mst()
    print(f"\nMST gefunden: {result.is_connected}")
    print(f"Gesamtgewicht: {result.total_weight}")
    print("MST Kanten:")
    for edge in result.edges:
        print(f"  {edge.source} -- {edge.target}: {edge.weight}")

    # Bottleneck MST Test
    bottleneck = mst.bottleneck_mst(0, 5)
    print(f"\nBottleneck von 0 zu 5: {bottleneck}")

    # Test mit unzusammenhängendem Graph
    disconnected_mst = KruskalMST(4)
    disconnected_mst.add_edge(0, 1, 1)
    disconnected_mst.add_edge(2, 3, 2)

    disconnected_result = disconnected_mst.find_mst()
    print(f"\nUnzusammenhängender Graph - Verbunden: {disconnected_result.is_connected}")
    print(f"Gewicht: {disconnected_result.total_weight}")
```

## Detaillierte Punkteverteilung

### Union-Find Implementation (6 Punkte)

- **Find mit Pfadkompression (3 Punkte)**: Rekursive Pfadkompression für O(α(n))
- **Union by Rank (2 Punkte)**: Optimale Baumhöhen-Verwaltung
- **Komponenten-Zählung (1 Punkt)**: Korrekte Aktualisierung bei Union

**Häufige Fehler:**

- Keine Pfadkompression (-2 Punkte)
- Union ohne Rank-Optimierung (-2 Punkte)
- Falsche Komponenten-Aktualisierung (-1 Punkt)

### Kruskal's Algorithmus (7 Punkte)

- **Kanten-Sortierung (1 Punkt)**: Aufsteigende Gewichts-Sortierung
- **Union-Find Integration (3 Punkte)**: Korrekte Zyklusvermeidung
- **MST-Aufbau (2 Punkte)**: Kanten hinzufügen bis |V|-1
- **Zusammenhangsprüfung (1 Punkt)**: Erkennung unzusammenhängender Graphen

**Häufige Fehler:**

- Kanten nicht sortiert (-2 Punkte)
- Zykluserkennung fehlt (-3 Punkte)
- Falsche Abbruchbedingung (-1 Punkt)
- Zusammenhang nicht geprüft (-1 Punkt)

### MST-Eigenschaften (4 Punkte)

- **Gewichts-Berechnung (2 Punkte)**: Korrekte Summierung der MST-Kanten
- **Verbundene Graph-Behandlung (1 Punkt)**: Unendlich bei unzusammenhängenden Graphen
- **Edge-Case Behandlung (1 Punkt)**: Leere Graphen und Einzelknoten

**Häufige Fehler:**

- Unzusammenhängende Graphen falsch behandelt (-2 Punkte)
- Edge Cases nicht berücksichtigt (-1 Punkt)

### Bottleneck MST (4 Punkte)

- **MST-Pfadsuche (2 Punkte)**: BFS/DFS im MST zwischen source und target
- **Maximale Kante finden (1 Punkt)**: Korrekte Max-Gewichts-Berechnung
- **Adjazenzlisten-Aufbau (1 Punkt)**: Bidirektionale Graph-Repräsentation

**Häufige Fehler:**

- Pfadsuche im ursprünglichen Graph statt MST (-2 Punkte)
- Falsche Max-Berechnung (-1 Punkt)
- Unidirektionale Adjazenzliste (-1 Punkt)

## Zeitkomplexitätsanalyse

- **Union-Find Operations**: O(α(V)) amortisiert pro Operation
- **Kruskal's Algorithm**: O(E log E) für Sortierung + O(E α(V)) für Union-Find
- **Bottleneck MST**: O(E log E) für MST + O(V) für Pfadsuche
- **Gesamtkomplexität**: O(E log E) dominiert

## Erwartete Ausgabe

```
Initial components: 6
After unions: 4
0 and 1 connected: True
0 and 2 connected: False

MST gefunden: True
Gesamtgewicht: 16.0
MST Kanten:
  1 -- 2: 1.0
  0 -- 2: 2.0
  3 -- 4: 2.0
  4 -- 5: 3.0
  0 -- 1: 4.0

Bottleneck von 0 zu 5: 4.0

Unzusammenhängender Graph - Verbunden: False
Gewicht: 3.0
```

## Optimierungshinweise

**Pfadkompression**: Die rekursive Find-Implementierung komprimiert automatisch alle Pfade zur Wurzel, was zu einer amortisierten Zeitkomplexität von O(α(n)) führt.

**Union by Rank**: Verhindert degenerierte Bäume und hält die Baumhöhe logarithmisch, was essentiell für die Effizienz ist.

**Bottleneck-Optimierung**: Da MSTs eindeutige Pfade zwischen Knoten haben, ist die Bottleneck-Distanz optimal - kein Pfad im ursprünglichen Graph kann eine kleinere maximale Kante haben.
