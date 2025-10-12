# Aufgabe 3: Dijkstra's Algorithm Implementation

**Punkte: 20**

## Kontext

Der Dijkstra-Algorithmus ist ein fundamentaler Algorithmus zur Berechnung kürzester Pfade in gewichteten Graphen mit nicht-negativen Kantengewichten. Entwickelt von Edsger W. Dijkstra im Jahr 1956, gehört er zu den wichtigsten Algorithmen der Graphentheorie und findet Anwendung in Navigationssystemen, Netzwerkrouting und vielen anderen Bereichen.

Der Algorithmus arbeitet nach dem Greedy-Prinzip und garantiert optimale Lösungen durch systematische Exploration der Knoten in der Reihenfolge ihrer minimalen Distanz vom Startknoten.

## Aufgabenstellung

Implementieren Sie eine vollständige Dijkstra-Klasse mit den folgenden Funktionalitäten:

1. **Kürzeste Pfade** von einem Startknoten zu allen erreichbaren Knoten
2. **Pfadrekonstruktion** mit vollständiger Routeninformation
3. **Single-Target** Optimierung für einen spezifischen Zielknoten
4. **Alternativpfad-Analyse** für robuste Routenplanung

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

        TODO: Implementieren Sie den klassischen Dijkstra-Algorithmus
        - Verwenden Sie eine Priority Queue (heapq) für effiziente Min-Extraktion
        - Initialisieren Sie Distanzen mit unendlich (float('inf'))
        - Relaxieren Sie Kanten systematisch
        - Behandeln Sie bereits besuchte Knoten korrekt
        """
        pass

    def find_path(self, start: int, target: int) -> Optional[PathResult]:
        """
        Findet den kürzesten Pfad zwischen Start- und Zielknoten mit vollständigen Details.

        Args:
            start: Startknoten
            target: Zielknoten

        Returns:
            PathResult mit Distanz, Pfad und Kantenzahl oder None

        TODO: Implementieren Sie die Pfadfindung mit Parent-Tracking
        - Erweitern Sie shortest_paths um Vorgängerverfolgung
        - Rekonstruieren Sie den vollständigen Pfad
        - Berechnen Sie zusätzliche Statistiken (Kantenzahl)
        - Optimierung: Stoppen Sie bei Erreichen des Ziels
        """
        pass

    def single_target_shortest_path(self, start: int, target: int) -> Optional[Tuple[float, List[int]]]:
        """
        Optimierte Version für die Suche zu einem spezifischen Ziel.

        Args:
            start: Startknoten
            target: Zielknoten

        Returns:
            Tuple (Distanz, Pfad) oder None wenn nicht erreichbar

        TODO: Implementieren Sie die Early-Termination Optimierung
        - Verwenden Sie den Standard-Dijkstra als Basis
        - Stoppen Sie die Suche sobald das Ziel erreicht wird
        - Dies ist effizienter als die Berechnung aller Pfade
        """
        pass

    def find_alternative_paths(self, start: int, target: int, max_paths: int = 3) -> List[PathResult]:
        """
        Findet alternative Pfade zwischen Start- und Zielknoten für Redundanz.

        Args:
            start: Startknoten
            target: Zielknoten
            max_paths: Maximale Anzahl alternativer Pfade

        Returns:
            Liste von PathResult-Objekten, sortiert nach Distanz

        TODO: Implementieren Sie die Alternativpfad-Suche
        - Verwenden Sie eine modifizierte Version des Algorithmus
        - Vermeiden Sie bereits gefundene Pfade durch Kantenausschluss
        - Limitieren Sie die Anzahl der zurückgegebenen Pfade
        - Stellen Sie sicher, dass Pfade signifikant unterschiedlich sind

        Hinweis: Dies ist eine vereinfachte Version. Ein vollständiger Algorithmus
        würde Yen's K-shortest paths algorithm implementieren.
        """
        pass

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

## Erwartete Ergebnisse

Für den Testgraph sollten Ihre Implementierungen folgende Ergebnisse liefern:

- **Kürzeste Pfade von 0**: `{0: 0, 1: 4, 2: 2, 3: 9, 4: 11, 5: 14}`
- **Pfad von 0 zu 5**: Distanz `14`, Pfad `[0, 2, 3, 4, 5]`, 4 Kanten
- **Single-Target 0 zu 4**: Distanz `11`, Pfad `[0, 2, 3, 4]`

## Bewertungskriterien

- **Kürzeste Pfade (6 Punkte)**: Korrekte Dijkstra-Implementierung mit Priority Queue
- **Pfadrekonstruktion (5 Punkte)**: Vollständige PathResult-Erzeugung
- **Single-Target Optimierung (4 Punkte)**: Early Termination bei Ziel-Erreichen
- **Alternative Pfade (5 Punkte)**: Mehrere unterschiedliche Pfade finden

**Zeitkomplexität**: O((V + E) log V) mit Binary Heap, wobei V die Anzahl Knoten und E die Anzahl Kanten ist.
