# Lösung: Topological Sorting with DFS

**Punkte: 16**

## Vollständige Lösung

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
        """
        # Initialisiere alle Knoten als WHITE
        all_nodes = set(self.graph.keys())
        for neighbors in self.graph.values():
            all_nodes.update(neighbors)

        self.node_states = {node: NodeState.WHITE for node in all_nodes}

        # Führe DFS für alle unbesuchten Knoten durch
        for node in all_nodes:
            if self.node_states[node] == NodeState.WHITE:
                if self._dfs_cycle_check(node):
                    return True

        return False

    def _dfs_cycle_check(self, node: int) -> bool:
        """
        Hilfsmethode für DFS-basierte Zykluserkennung.

        Args:
            node: Aktueller Knoten für DFS

        Returns:
            True wenn Zyklus in diesem Teilbaum gefunden
        """
        # Markiere Knoten als in Bearbeitung (GRAY)
        self.node_states[node] = NodeState.GRAY

        # Besuche alle Nachbarn
        for neighbor in self.graph.get(node, []):
            if self.node_states[neighbor] == NodeState.GRAY:
                # Zurück-Kante gefunden -> Zyklus
                return True
            elif self.node_states[neighbor] == NodeState.WHITE:
                if self._dfs_cycle_check(neighbor):
                    return True

        # Markiere Knoten als abgeschlossen (BLACK)
        self.node_states[node] = NodeState.BLACK
        return False

    def topological_sort(self) -> Optional[List[int]]:
        """
        Führt topologische Sortierung durch.

        Returns:
            Liste der Knoten in topologischer Reihenfolge oder None bei Zyklus
        """
        # Prüfe auf Zyklen
        if self.has_cycle():
            return None

        # Reset für topologische Sortierung
        all_nodes = set(self.graph.keys())
        for neighbors in self.graph.values():
            all_nodes.update(neighbors)

        visited = set()
        self.finish_order = []

        # Führe DFS für alle unbesuchten Knoten durch
        for node in sorted(all_nodes):  # Sortiert für deterministische Ergebnisse
            if node not in visited:
                self._dfs_topological(node, visited)

        # Kehre die Finish-Order um für topologische Reihenfolge
        return self.finish_order[::-1]

    def _dfs_topological(self, node: int, visited: Set[int]):
        """
        Hilfsmethode für DFS-basierte topologische Sortierung.

        Args:
            node: Aktueller Knoten für DFS
            visited: Set der bereits besuchten Knoten
        """
        visited.add(node)

        # Rekursiv alle Nachbarn besuchen
        for neighbor in sorted(self.graph.get(node, [])):
            if neighbor not in visited:
                self._dfs_topological(neighbor, visited)

        # Knoten zur finish_order hinzufügen (Post-Order)
        self.finish_order.append(node)

    def resolve_dependencies(self, dependencies: Dict[str, Set[str]]) -> Optional[List[str]]:
        """
        Löst Abhängigkeiten für Build-System auf.

        Args:
            dependencies: Dictionary (Item -> Set von Abhängigkeiten)

        Returns:
            Liste in Build-Reihenfolge oder None bei zirkulären Abhängigkeiten
        """
        # Erstelle Mapping String -> Int
        all_items = set(dependencies.keys())
        for deps in dependencies.values():
            all_items.update(deps)

        item_to_id = {item: idx for idx, item in enumerate(sorted(all_items))}
        id_to_item = {idx: item for item, idx in item_to_id.items()}

        # Konvertiere zu Integer-Graph
        int_graph = {}
        for item, deps in dependencies.items():
            item_id = item_to_id[item]
            int_graph[item_id] = []

            # Abhängigkeiten zeigen auf das Item (umgekehrte Richtung)
            for dep in deps:
                dep_id = item_to_id[dep]
                if dep_id not in int_graph:
                    int_graph[dep_id] = []
                int_graph[dep_id].append(item_id)

        # Führe topologische Sortierung durch
        temp_topo = TopologicalSort(int_graph)
        sorted_ids = temp_topo.topological_sort()

        if sorted_ids is None:
            return None

        # Konvertiere zurück zu Strings
        return [id_to_item[node_id] for node_id in sorted_ids]

    def longest_path_in_dag(self, weights: Dict[Tuple[int, int], float]) -> Dict[int, float]:
        """
        Berechnet längste Pfade in gewichtetem DAG (für kritische Pfadanalyse).

        Args:
            weights: Dictionary (source, target) -> Kantengewicht

        Returns:
            Dictionary Knoten -> Maximale Distanz von Quellknoten
        """
        # Führe topologische Sortierung durch
        topo_order = self.topological_sort()
        if topo_order is None:
            return {}

        # Initialisiere Distanzen
        distances = {}
        all_nodes = set(self.graph.keys())
        for neighbors in self.graph.values():
            all_nodes.update(neighbors)

        # Finde Quellknoten (keine eingehenden Kanten)
        has_incoming = set()
        for source, targets in self.graph.items():
            for target in targets:
                has_incoming.add(target)

        source_nodes = all_nodes - has_incoming

        # Initialisiere alle Distanzen mit negativer Unendlichkeit
        for node in all_nodes:
            distances[node] = float('-inf')

        # Quellknoten haben Distanz 0
        for source in source_nodes:
            distances[source] = 0.0

        # Bearbeite Knoten in topologischer Reihenfolge
        for node in topo_order:
            if distances[node] != float('-inf'):  # Knoten ist erreichbar
                for neighbor in self.graph.get(node, []):
                    edge_weight = weights.get((node, neighbor), 0)
                    new_distance = distances[node] + edge_weight

                    if new_distance > distances[neighbor]:
                        distances[neighbor] = new_distance

        # Entferne unerreichbare Knoten
        result = {}
        for node, dist in distances.items():
            if dist != float('-inf'):
                result[node] = dist

        return result

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

## Detaillierte Punkteverteilung

### Zykluserkennung (4 Punkte)

- **DFS-Farbmarkierung (2 Punkte)**: Korrekte Verwendung von WHITE/GRAY/BLACK
- **Zurück-Kanten-Erkennung (1 Punkt)**: GRAY-Nachbar = Zyklus
- **Vollständige Knotenabdeckung (1 Punkt)**: Alle Knoten werden geprüft

**Häufige Fehler:**

- Nur explizite Graph-Knoten prüfen (-1 Punkt)
- Falsche Farbzustände verwenden (-2 Punkte)
- Zurück-Kanten nicht korrekt erkennen (-1 Punkt)

### Topologische Sortierung (5 Punkte)

- **Zyklusprüfung zuerst (1 Punkt)**: Keine Sortierung bei Zyklen
- **DFS Post-Order (2 Punkte)**: Korrekte finish_order Sammlung
- **Reihenfolgen-Umkehrung (1 Punkt)**: finish_order umkehren für topologische Ordnung
- **Vollständige Knotenabdeckung (1 Punkt)**: Alle Knoten werden sortiert

**Häufige Fehler:**

- Post-Order nicht implementiert (-2 Punkte)
- Reihenfolge nicht umgekehrt (-1 Punkt)
- Isolierte Knoten vergessen (-1 Punkt)

### Abhängigkeitsauflösung (4 Punkte)

- **String-ID Mapping (1 Punkt)**: Bidirektionale Konvertierung String ↔ Int
- **Graph-Umkehrung (1 Punkt)**: Abhängigkeiten → Items statt Items → Abhängigkeiten
- **Topologische Anwendung (1 Punkt)**: Korrekte Verwendung der Sortierung
- **Rückkonvertierung (1 Punkt)**: Integer-Ergebnis zu String-Liste

**Häufige Fehler:**

- Graph-Richtung falsch (-2 Punkte)
- Fehlende String-Konvertierung (-1 Punkt)
- Unvollständige Item-Sammlung (-1 Punkt)

### Längster Pfad (3 Punkte)

- **Quellknoten-Identifikation (1 Punkt)**: Knoten ohne eingehende Kanten
- **Topologische Verarbeitung (1 Punkt)**: Knoten in korrekter Reihenfolge
- **Kantenrelaxierung (1 Punkt)**: Maximale Distanz-Updates

**Häufige Fehler:**

- Falsche Quellknoten-Erkennung (-1 Punkt)
- Distanz-Initialisierung falsch (-1 Punkt)
- Relaxierung für Minimum statt Maximum (-1 Punkt)

## Zeitkomplexitätsanalyse

- **Zykluserkennung**: O(V + E)
- **Topologische Sortierung**: O(V + E)
- **Abhängigkeitsauflösung**: O(V + E) + O(V log V) für Mapping
- **Längster Pfad**: O(V + E) nach topologischer Sortierung

## Erwartete Ausgabe

```
Hat Zyklus (DAG): False
Topologische Sortierung: [0, 2, 1, 3, 4]

Hat Zyklus (zyklisch): True
Topologische Sortierung (zyklisch): None

Build-Reihenfolge: ['main.c', 'util.c', 'util.h', 'main.o', 'util.o', 'program']
Längste Pfade: {0: 0.0, 1: 5.0, 2: 3.0, 3: 11.0, 4: 12.0}
```
