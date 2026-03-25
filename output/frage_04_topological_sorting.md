# Aufgabe 4: Topological Sorting with DFS

**Punkte: 16**

## Kontext

Die topologische Sortierung ist ein fundamentaler Algorithmus für gerichtete azyklische Graphen (DAGs), der eine lineare Anordnung der Knoten erstellt, bei der für jede gerichtete Kante (u,v) der Knoten u in der Sortierung vor v erscheint. Dieser Algorithmus ist essentiell für Abhängigkeitsauflösung, Projektplanung, Compiler-Design und Build-Systeme.

Die DFS-basierte Implementierung nutzt die Post-Order-Traversierung: Knoten werden in umgekehrter Reihenfolge ihrer DFS-Fertigstellung sortiert. Dies garantiert eine korrekte topologische Ordnung.

## Aufgabenstellung

Implementieren Sie eine vollständige TopologicalSort-Klasse mit den folgenden Funktionalitäten:

1. **Topologische Sortierung** mittels DFS
2. **Zykluserkennung** zur Validierung des DAG
3. **Abhängigkeitsauflösung** für Build-Systeme
4. **Längster Pfad** in DAGs für kritische Pfade

```python
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum

class NodeState(Enum):
    """Zustände für DFS-Traversierung."""
    WHITE = 0  # Unbesucht
    GRAY = 1   # In Bearbeitung
    BLACK = 2  # Abgeschlossen

class TopologicalSort:
    def __init__(self, graph: Dict[int, List[int]]):
        """
        Initialisiert die TopologicalSort-Klasse mit einem gerichteten Graphen.

        Args:
            graph: Dictionary mit Adjazenzliste (Knoten -> Liste der Nachfolger)
        """
        self.graph = graph
        self.node_states = {}
        self.finish_order = []

    def has_cycle(self) -> bool:
        """
        Prüft ob der Graph einen Zyklus enthält.

        Returns:
            True wenn Zyklus gefunden, False wenn DAG

        TODO: Implementieren Sie die Zykluserkennung
        - Verwenden Sie DFS mit Farbmarkierung (WHITE, GRAY, BLACK)
        - GRAY-Knoten sind in der aktuellen DFS-Spur
        - Zurück-Kante zu GRAY-Knoten = Zyklus gefunden
        - Setzen Sie node_states entsprechend
        """
        pass

    def _dfs_cycle_check(self, node: int) -> bool:
        """
        Hilfsmethode für DFS-basierte Zykluserkennung.

        Args:
            node: Aktueller Knoten für DFS

        Returns:
            True wenn Zyklus in diesem Teilbaum gefunden

        TODO: Implementieren Sie die DFS-Zyklusprüfung
        - Markieren Sie Knoten als GRAY beim Betreten
        - Rekursive Prüfung aller Nachbarn
        - Zurück-Kante erkennen (Nachbar ist GRAY)
        - Knoten als BLACK markieren beim Verlassen
        """
        pass

    def topological_sort(self) -> Optional[List[int]]:
        """
        Führt topologische Sortierung durch.

        Returns:
            Liste der Knoten in topologischer Reihenfolge oder None bei Zyklus

        TODO: Implementieren Sie die topologische Sortierung
        - Prüfen Sie zuerst auf Zyklen
        - Führen Sie DFS für alle unbesuchten Knoten durch
        - Sammeln Sie Knoten in finish_order (Post-Order)
        - Kehren Sie die Reihenfolge um für topologische Ordnung
        """
        pass

    def _dfs_topological(self, node: int):
        """
        Hilfsmethode für DFS-basierte topologische Sortierung.

        Args:
            node: Aktueller Knoten für DFS

        TODO: Implementieren Sie die DFS-Traversierung
        - Markieren Sie Knoten als besucht
        - Rekursiv alle Nachbarn besuchen
        - Knoten zur finish_order hinzufügen (Post-Order)
        """
        pass

    def resolve_dependencies(self, dependencies: Dict[str, Set[str]]) -> Optional[List[str]]:
        """
        Löst Abhängigkeiten für Build-System auf.

        Args:
            dependencies: Dictionary (Item -> Set von Abhängigkeiten)

        Returns:
            Liste in Build-Reihenfolge oder None bei zirkulären Abhängigkeiten

        TODO: Implementieren Sie die Abhängigkeitsauflösung
        - Konvertieren Sie String-IDs zu Integer-Graph
        - Führen Sie topologische Sortierung durch
        - Konvertieren Sie Ergebnis zurück zu String-IDs
        - Behandeln Sie fehlende Abhängigkeiten korrekt

        Beispiel:
        dependencies = {
            'main.o': {'main.c', 'util.h'},
            'util.o': {'util.c', 'util.h'},
            'program': {'main.o', 'util.o'}
        }
        Result: ['main.c', 'util.h', 'util.c', 'main.o', 'util.o', 'program']
        """
        pass

    def longest_path_in_dag(self, weights: Dict[Tuple[int, int], float]) -> Dict[int, float]:
        """
        Berechnet längste Pfade in gewichtetem DAG (für kritische Pfadanalyse).

        Args:
            weights: Dictionary (source, target) -> Kantengewicht

        Returns:
            Dictionary Knoten -> Maximale Distanz von Quellknoten

        TODO: Implementieren Sie die Längste-Pfad-Berechnung
        - Führen Sie topologische Sortierung durch
        - Bearbeiten Sie Knoten in topologischer Reihenfolge
        - Relaxieren Sie ausgehende Kanten für maximale Distanz
        - Initialisieren Sie Quellknoten (keine eingehenden Kanten) mit 0

        Hinweis: Längster Pfad = Dijkstra mit negativierten Gewichten,
        aber effizienter in DAGs durch topologische Ordnung
        """
        pass

# Testfälle
if __name__ == "__main__":
    # Testgraph 1: Einfacher DAG
    dag = {
        0: [1, 2],
        1: [3],
        2: [3, 4],
        3: [4],
        4: []
    }

    # Testgraph 2: Graph mit Zyklus
    cyclic_graph = {
        0: [1],
        1: [2],
        2: [0, 3],
        3: []
    }

    # Test für DAG
    topo_dag = TopologicalSort(dag)
    print("Hat Zyklus (DAG):", topo_dag.has_cycle())

    result = topo_dag.topological_sort()
    print("Topologische Sortierung:", result)

    # Test für zyklischen Graph
    topo_cyclic = TopologicalSort(cyclic_graph)
    print("\nHat Zyklus (zyklisch):", topo_cyclic.has_cycle())

    cyclic_result = topo_cyclic.topological_sort()
    print("Topologische Sortierung (zyklisch):", cyclic_result)

    # Test für Abhängigkeitsauflösung
    dependencies = {
        'main.o': {'main.c', 'util.h'},
        'util.o': {'util.c', 'util.h'},
        'program': {'main.o', 'util.o'}
    }

    build_order = topo_dag.resolve_dependencies(dependencies)
    print("\nBuild-Reihenfolge:", build_order)

    # Test für längsten Pfad
    weights = {
        (0, 1): 5,
        (0, 2): 3,
        (1, 3): 6,
        (2, 3): 2,
        (2, 4): 4,
        (3, 4): 1
    }

    longest_paths = topo_dag.longest_path_in_dag(weights)
    print("Längste Pfade:", longest_paths)
```

## Erwartete Ergebnisse

Für die Testgraphen sollten Ihre Implementierungen folgende Ergebnisse liefern:

- **DAG Zyklusprüfung**: `False` (kein Zyklus)
- **Topologische Sortierung**: `[0, 2, 1, 3, 4]` (eine mögliche Ordnung)
- **Zyklische Zyklusprüfung**: `True` (Zyklus gefunden)
- **Build-Reihenfolge**: Abhängigkeiten zuerst, dann Items
- **Längste Pfade**: Maximale Distanzen von Quellknoten

## Bewertungskriterien

- **Zykluserkennung (4 Punkte)**: Korrekte DFS-Implementierung mit Farbmarkierung
- **Topologische Sortierung (5 Punkte)**: DFS Post-Order mit korrekter Umkehrung
- **Abhängigkeitsauflösung (4 Punkte)**: String-Graph-Konvertierung und Anwendung
- **Längster Pfad (3 Punkte)**: Topologische Ordnung für DAG-Optimierung

**Zeitkomplexität**: O(V + E) für alle Operationen, wobei V die Anzahl Knoten und E die Anzahl Kanten ist.
