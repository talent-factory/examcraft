# Aufgabe 2: Breadth-First Search (BFS) Implementation

**Punkte: 18**

## Kontext

Die Breitensuche (Breadth-First Search, BFS) ist ein fundamentaler Graphalgorithmus, der zur systematischen Exploration von Knoten in einem Graphen verwendet wird. BFS besucht alle Knoten in der Reihenfolge ihrer Entfernung vom Startknoten, wobei zunächst alle direkten Nachbarn besucht werden, dann deren Nachbarn usw.

BFS garantiert, dass in ungewichteten Graphen der kürzeste Pfad zwischen zwei Knoten gefunden wird und ist die Basis für viele weitere Graphalgorithmen.

## Aufgabenstellung

Implementieren Sie eine vollständige BFS-Klasse mit den folgenden Funktionalitäten:

1. **BFS-Traversierung** mit Rückgabe der Besuchsreihenfolge
2. **Kürzeste Pfade** von einem Startknoten zu allen erreichbaren Knoten
3. **Pfadrekonstruktion** für einen spezifischen Zielknoten
4. **Zusammenhangskomponenten** Analyse

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

        TODO: Implementieren Sie die BFS-Traversierung
        - Verwenden Sie eine Queue (deque) für die BFS
        - Markieren Sie besuchte Knoten
        - Geben Sie die Besuchsreihenfolge zurück
        """
        pass

    def shortest_paths(self, start: int) -> Dict[int, int]:
        """
        Berechnet die kürzesten Pfade vom Startknoten zu allen erreichbaren Knoten.

        Args:
            start: Startknoten

        Returns:
            Dictionary: Knoten -> Kürzeste Distanz vom Start

        TODO: Implementieren Sie die Berechnung kürzester Pfade
        - Erweitern Sie BFS um Distanzmessung
        - Speichern Sie für jeden Knoten die minimale Distanz
        - Nicht erreichbare Knoten sollten nicht im Dictionary sein
        """
        pass

    def find_path(self, start: int, target: int) -> Optional[List[int]]:
        """
        Findet den kürzesten Pfad zwischen Start- und Zielknoten.

        Args:
            start: Startknoten
            target: Zielknoten

        Returns:
            Liste der Knoten im kürzesten Pfad (inkl. Start und Ziel)
            None wenn kein Pfad existiert

        TODO: Implementieren Sie die Pfadfindung
        - Erweitern Sie BFS um Pfadverfolgung (parent tracking)
        - Rekonstruieren Sie den Pfad vom Ziel zum Start
        - Geben Sie den Pfad in korrekter Reihenfolge zurück
        """
        pass

    def connected_components(self) -> List[List[int]]:
        """
        Findet alle Zusammenhangskomponenten im Graphen.

        Returns:
            Liste von Listen, wobei jede innere Liste eine Komponente darstellt

        TODO: Implementieren Sie die Komponentenanalyse
        - Führen Sie BFS für alle unbesuchten Knoten durch
        - Sammeln Sie Knoten jeder Komponente
        - Sortieren Sie Komponenten nach Größe (größte zuerst)
        """
        pass

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

## Erwartete Ergebnisse

Für den Testgraph 1 sollten Ihre Implementierungen folgende Ergebnisse liefern:

- **Traversierung von 0**: `[0, 1, 2, 3, 4, 5]` (oder ähnliche BFS-Reihenfolge)
- **Kürzeste Pfade von 0**: `{0: 0, 1: 1, 2: 1, 3: 2, 4: 2, 5: 2}`
- **Pfad von 0 zu 5**: `[0, 2, 5]` (ein möglicher kürzester Pfad)
- **Komponenten**: `[[0, 1, 2, 3, 4, 5]]` (eine große Komponente)

## Bewertungskriterien

- **BFS-Traversierung (5 Punkte)**: Korrekte Implementierung mit Queue
- **Kürzeste Pfade (5 Punkte)**: Korrekte Distanzberechnung
- **Pfadrekonstruktion (4 Punkte)**: Vollständiger Pfad mit parent tracking
- **Zusammenhangskomponenten (4 Punkte)**: Korrekte Komponentenidentifikation

**Zeitkomplexität**: O(V + E) für alle Operationen, wobei V die Anzahl Knoten und E die Anzahl Kanten ist.