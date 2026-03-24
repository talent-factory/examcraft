# Musterlösung: Aufgabe 1 | Graph-Repräsentation

## Vollständige Implementierung

```python
class Graph:
    """Graph-Implementierung mit Adjazenzlisten-Repräsentation"""

    def __init__(self, n):
        """
        Initialisiert einen Graphen mit n+1 Knoten (0 bis n)
        """
        self.numNodes = n
        self.vertices = []
        for i in range(n + 1):
            self.vertices.append({})

    def addEdge(self, i, j, weight=None):
        """
        Fügt eine Kante von Knoten i zu Knoten j hinzu
        Optional mit Gewicht weight
        """
        if weight is None:
            weight = 1
        self.vertices[i][j] = weight

    def isEdge(self, i, j):
        """
        Testet, ob eine Kante von i nach j existiert
        Rückgabe: Boolean
        """
        return j in self.vertices[i]

    def getNeighbors(self, i):
        """
        Gibt alle Nachbarn von Knoten i zurück
        Rückgabe: Liste der Nachbarknoten
        """
        return list(self.vertices[i].keys())

class GraphMatrix:
    """Graph-Implementierung mit Adjazenzmatrix-Repräsentation"""

    def __init__(self, n):
        """
        Initialisiert einen Graphen mit n+1 Knoten (0 bis n)
        """
        self.numNodes = n
        # Initialisiere (n+1) x (n+1) Matrix mit Nullen
        self.matrix = []
        for i in range(n + 1):
            row = [0] * (n + 1)
            self.matrix.append(row)

    def addEdge(self, i, j, weight=1):
        """
        Fügt eine Kante von Knoten i zu Knoten j hinzu
        """
        self.matrix[i][j] = weight

    def isEdge(self, i, j):
        """
        Testet, ob eine Kante von i nach j existiert
        """
        return self.matrix[i][j] != 0

    def getNeighbors(self, i):
        """
        Gibt alle Nachbarn von Knoten i zurück
        """
        neighbors = []
        for j in range(self.numNodes + 1):
            if self.matrix[i][j] != 0:
                neighbors.append(j)
        return neighbors
```

## Punkteverteilung

### Algorithmus-Verständnis (5 Punkte)

- **Graph-Repräsentationen verstehen** (2 Punkte): Verständnis der Unterschiede zwischen Adjazenzliste und Adjazenzmatrix
- **Datenstruktur-Wahl** (2 Punkte): Korrekte Wahl der Python-Datenstrukturen (dict für Adjazenzliste, Liste von Listen für Matrix)
- **Index-Handling** (1 Punkt): Verständnis des Index-Bereichs (0 bis n)

### Korrekte Implementierung (7 Punkte)

- **Graph-Klasse Methoden** (3 Punkte): addEdge, isEdge, getNeighbors korrekt implementiert
- **GraphMatrix Initialisierung** (2 Punkte): Korrekte Matrix-Initialisierung
- **GraphMatrix Methoden** (2 Punkte): Alle Methoden korrekt implementiert

### Code-Qualität (3 Punkte)

- **Lesbarkeit und Stil** (1 Punkt): Konsistente Einrückung, aussagekräftige Variablennamen
- **Effizienz** (1 Punkt): Effiziente Implementierung beider Repräsentationen
- **Fehlerbehandlung** (1 Punkt): Angemessene Behandlung von Grenzfällen
