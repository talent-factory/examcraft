# Aufgabe 1 | Graph-Repräsentation | 15 Punkte

## Kontext

Graphen sind fundamentale Datenstrukturen in der Informatik zur Repräsentation von Beziehungen zwischen Objekten. Es gibt verschiedene Möglichkeiten, Graphen zu implementieren: als Adjazenzmatrix oder als Adjazenzliste. Jede Repräsentation hat ihre Vor- und Nachteile bezüglich Speicherverbrauch und Operationszeiten.

## Aufgabenstellung

Implementieren Sie eine vollständige Graph-Klasse mit sowohl Adjazenzlisten- als auch Adjazenzmatrix-Repräsentation.

## Code-Grundgerüst

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
        TODO: Implementieren Sie diese Methode
        Fügt eine Kante von Knoten i zu Knoten j hinzu
        Optional mit Gewicht weight
        """
        pass

    def isEdge(self, i, j):
        """
        TODO: Implementieren Sie diese Methode
        Testet, ob eine Kante von i nach j existiert
        Rückgabe: Boolean
        """
        pass

    def getNeighbors(self, i):
        """
        TODO: Implementieren Sie diese Methode
        Gibt alle Nachbarn von Knoten i zurück
        Rückgabe: Liste der Nachbarknoten
        """
        pass

class GraphMatrix:
    """Graph-Implementierung mit Adjazenzmatrix-Repräsentation"""

    def __init__(self, n):
        """
        Initialisiert einen Graphen mit n+1 Knoten (0 bis n)
        """
        self.numNodes = n
        # TODO: Implementieren Sie die Matrix-Initialisierung
        pass

    def addEdge(self, i, j, weight=1):
        """
        TODO: Implementieren Sie diese Methode
        Fügt eine Kante von Knoten i zu Knoten j hinzu
        """
        pass

    def isEdge(self, i, j):
        """
        TODO: Implementieren Sie diese Methode
        Testet, ob eine Kante von i nach j existiert
        """
        pass

    def getNeighbors(self, i):
        """
        TODO: Implementieren Sie diese Methode
        Gibt alle Nachbarn von Knoten i zurück
        """
        pass
```

## Anforderungen

- Implementieren Sie alle TODO-markierten Methoden für beide Klassen
- Die `addEdge`-Methode soll gerichtete Graphen unterstützen
- Bei ungewichteten Graphen soll das Standardgewicht 1 verwendet werden
- Die Adjazenzmatrix soll mit 0 für keine Kante und dem Gewicht für vorhandene Kanten initialisiert werden
- Achten Sie auf korrekte Behandlung von Indizes (0 bis n)

## Bewertung

- **Algorithmus-Verständnis**: 5 Punkte
- **Korrekte Implementierung**: 7 Punkte
- **Code-Qualität**: 3 Punkte
- **Gesamt**: 15 Punkte
