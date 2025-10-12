# Aufgabe 5: Minimum Spanning Tree (Kruskal's Algorithm with Union-Find)

**Punkte: 21**

## Kontext

Ein Minimum Spanning Tree (MST) ist ein fundamentales Konzept der Graphentheorie, das den kostenminimalen Teilbaum eines gewichteten, zusammenhängenden Graphen beschreibt, der alle Knoten verbindet. Kruskal's Algorithmus löst dieses Problem effizient durch sortierte Kantenerweiterung und Union-Find-Datenstrukturen zur Zyklusvermeidung.

Der Algorithmus ist besonders relevant für Netzwerkdesign, Clustering-Probleme und Infrastrukturplanung, wo minimale Verbindungskosten bei vollständiger Konnektivität gefordert sind.

## Aufgabenstellung

Implementieren Sie eine vollständige MST-Klasse mit Kruskal's Algorithmus und Union-Find:

1. **Union-Find Datenstruktur** mit Pfadkompression und Union by Rank
2. **Kruskal's Algorithmus** für MST-Berechnung
3. **MST-Eigenschaften** Analyse (Gesamtgewicht, Kantenzahl)
4. **Bottleneck MST** für Min-Max-Pfadprobleme

```python
from typing import List, Tuple, Dict, Set, Optional
from dataclasses import dataclass

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

        TODO: Implementieren Sie die Find-Operation
        - Verfolgen Sie parent-Zeiger bis zur Wurzel
        - Implementieren Sie Pfadkompression für O(α(n)) Amortized
        - Alle Knoten auf dem Pfad zeigen direkt auf die Wurzel
        """
        pass

    def union(self, x: int, y: int) -> bool:
        """
        Vereinigt die Sets von x und y.

        Args:
            x, y: Elemente deren Sets vereinigt werden sollen

        Returns:
            True wenn Vereinigung stattfand, False wenn bereits verbunden

        TODO: Implementieren Sie die Union-Operation
        - Finden Sie Wurzeln von x und y
        - Wenn bereits in gleichem Set: return False
        - Implementieren Sie Union by Rank für optimale Baumhöhe
        - Aktualisieren Sie components-Zähler
        """
        pass

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

        TODO: Implementieren Sie Kruskal's Algorithmus
        - Sortieren Sie alle Kanten nach Gewicht aufsteigend
        - Verwenden Sie Union-Find zur Zyklusvermeidung
        - Fügen Sie Kanten hinzu die keine Zyklen bilden
        - Stoppen Sie bei |V|-1 Kanten (vollständiger Baum)
        - Prüfen Sie Zusammenhang des ursprünglichen Graphs
        """
        pass

    def get_mst_weight(self) -> float:
        """
        Berechnet nur das Gesamtgewicht des MST (ohne Kanten-Details).

        Returns:
            Minimales Gesamtgewicht oder infinity bei unzusammenhängendem Graph

        TODO: Optimierte Version für reine Gewichtsberechnung
        - Verwenden Sie find_mst() aber geben nur Gewicht zurück
        - Behandeln Sie unzusammenhängende Graphen korrekt
        """
        pass

    def bottleneck_mst(self, source: int, target: int) -> Optional[float]:
        """
        Findet die minimale maximale Kante auf dem Pfad zwischen source und target.

        Args:
            source: Startknoten
            target: Zielknoten

        Returns:
            Minimale maximale Kantengewicht oder None wenn nicht verbunden

        TODO: Implementieren Sie Bottleneck MST
        - Berechnen Sie MST des Graphs
        - Finden Sie Pfad von source zu target im MST
        - Geben Sie das Maximum der Kantengewichte auf diesem Pfad zurück
        - Dies löst das Min-Max-Pfadproblem optimal

        Hinweis: In einem MST ist der Pfad zwischen zwei Knoten der
        eindeutige Pfad mit minimaler Bottleneck-Distanz.
        """
        pass

    def _find_path_in_mst(self, mst_edges: List[Edge], source: int, target: int) -> Optional[List[Edge]]:
        """
        Hilfsmethode: Findet Pfad zwischen zwei Knoten im MST.

        Args:
            mst_edges: Kanten des MST
            source: Startknoten
            target: Zielknoten

        Returns:
            Liste der Kanten auf dem Pfad oder None

        TODO: Implementieren Sie die Pfadsuche im MST
        - Bauen Sie Adjazenzliste aus MST-Kanten
        - Verwenden Sie DFS oder BFS für Pfadsuche
        - MST ist ein Baum, daher existiert genau ein Pfad
        """
        pass

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

## Erwartete Ergebnisse

Für den Testgraph sollten Ihre Implementierungen folgende Ergebnisse liefern:

- **MST-Gesamtgewicht**: `16` (minimales Gewicht für Spannbaum)
- **MST-Kanten**: 5 Kanten (bei 6 Knoten)
- **Bottleneck 0→5**: Maximale Kante auf eindeutigem MST-Pfad
- **Unzusammenhängender Graph**: `is_connected = False`

## Bewertungskriterien

- **Union-Find Implementation (6 Punkte)**: Find mit Pfadkompression, Union by Rank
- **Kruskal's Algorithmus (7 Punkte)**: Korrekte MST-Berechnung mit Zyklusvermeidung
- **MST-Eigenschaften (4 Punkte)**: Gewichtsberechnung und Zusammenhangsprüfung
- **Bottleneck MST (4 Punkte)**: Min-Max-Pfadproblem in MST

**Zeitkomplexität**: O(E log E) für Kantensortierung + O(E α(V)) für Union-Find-Operationen, wobei α die inverse Ackermann-Funktion ist.
