# Musterlösung: Aufgabe 2 | MinHeapify und Heap-Konstruktion

## Vollständige Implementierung

```python
def minHeapify(heap, i):
    """
    Stellt die Min-Heap-Eigenschaft für den Knoten an Index i wieder her.
    Der Knoten wird solange nach unten transportiert, bis die Heap-Bedingung
    erfüllt ist.

    Args:
        heap: Liste, die einen Heap repräsentiert (heap[0] = None)
        i: Index des Knotens, für den die Heap-Eigenschaft hergestellt werden soll

    Returns:
        None (modifiziert heap in-place)
    """
    # Indizes der Kinder
    left = 2 * i
    right = 2 * i + 1
    n = len(heap) - 1  # Anzahl der Heap-Elemente (ohne heap[0])

    # Finde den Index des kleinsten Elements unter i und seinen Kindern
    smallest = i

    # Prüfe linkes Kind
    if left <= n and heap[left] < heap[smallest]:
        smallest = left

    # Prüfe rechtes Kind
    if right <= n and heap[right] < heap[smallest]:
        smallest = right

    # Falls die Heap-Eigenschaft verletzt ist
    if smallest != i:
        # Tausche aktuellen Knoten mit kleinstem Kind
        heap[i], heap[smallest] = heap[smallest], heap[i]

        # Rekursiver Aufruf für das getauschte Kind
        minHeapify(heap, smallest)

def buildHeap(lst):
    """
    Konstruiert aus einer beliebigen Liste einen gültigen Min-Heap.
    Verwendet minHeapify für alle inneren Knoten von unten nach oben.

    Args:
        lst: Liste mit beliebigen Elementen (lst[0] muss None sein)

    Returns:
        None (modifiziert lst in-place zu einem gültigen Min-Heap)
    """
    n = len(lst) - 1  # Anzahl der Heap-Elemente

    # Starte mit dem letzten inneren Knoten und arbeite nach oben
    # Der letzte innere Knoten hat Index n // 2
    for i in range(n // 2, 0, -1):
        minHeapify(lst, i)

# Test-Code
if __name__ == "__main__":
    # Test 1: buildHeap
    test_list = [None, 86, 13, 23, 96, 6, 37, 29, 56, 80, 5, 92, 52, 32, 21]
    print(f"Vor buildHeap: {test_list[1:]}")  # Ohne None anzeigen
    buildHeap(test_list)
    print(f"Nach buildHeap: {test_list[1:]}")
    print()

    # Test 2: minHeapify direkt
    test_heap = [None, 50, 13, 23, 96, 6, 37, 29]
    print(f"Vor minHeapify(heap, 1): {test_heap[1:]}")
    minHeapify(test_heap, 1)
    print(f"Nach minHeapify(heap, 1): {test_heap[1:]}")
    print()

    # Test 3: Verifikation der Heap-Eigenschaft
    def is_min_heap(heap):
        """Prüft, ob ein Heap die Min-Heap-Eigenschaft erfüllt"""
        n = len(heap) - 1
        for i in range(1, n // 2 + 1):
            left = 2 * i
            right = 2 * i + 1

            if left <= n and heap[i] > heap[left]:
                return False
            if right <= n and heap[i] > heap[right]:
                return False
        return True

    # Test verschiedene Listen
    test_cases = [
        [None, 64, 23, 13, 96, 6, 37, 29, 56, 80, 5],
        [None, 1],
        [None, 3, 1, 2],
        [None, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    ]

    for i, test in enumerate(test_cases):
        original = test.copy()
        buildHeap(test)
        print(f"Test {i+1}: {original[1:]} -> {test[1:]}")
        print(f"Ist Min-Heap: {is_min_heap(test)}")
        print()
```

## Punkteverteilung

### MinHeapify Algorithmus (7 Punkte)

**Grundlegende Logik (4 Punkte):**
- **1 Punkt**: Korrekte Berechnung der Kind-Indizes (`left = 2*i`, `right = 2*i+1`)
- **1 Punkt**: Finden des kleinsten Elements unter Knoten und Kindern
- **1 Punkt**: Vergleiche mit linkem Kind (`heap[left] < heap[smallest]`)
- **1 Punkt**: Vergleiche mit rechtem Kind (`heap[right] < heap[smallest]`)

**Rekursion und Tausch (3 Punkte):**
- **1 Punkt**: Korrektes Tauschen (`heap[i], heap[smallest] = heap[smallest], heap[i]`)
- **1 Punkt**: Rekursiver Aufruf `minHeapify(heap, smallest)`
- **1 Punkt**: Korrekte Rekursions-Bedingung (`smallest != i`)

### BuildHeap Implementierung (5 Punkte)

**Schleifenlogik (3 Punkte):**
- **1 Punkt**: Korrekter Startindex (`n // 2` - letzter innerer Knoten)
- **1 Punkt**: Korrekte Schleife `range(n // 2, 0, -1)`
- **1 Punkt**: Aufruf von `minHeapify(lst, i)` für jeden inneren Knoten

**Heap-Konstruktion (2 Punkte):**
- **1 Punkt**: Verständnis des "Bottom-Up" Ansatzes
- **1 Punkt**: Korrekte Berechnung der Heap-Größe (`len(lst) - 1`)

### Rekursion und Edge-Cases (3 Punkte)

**Rekursions-Implementierung (2 Punkte):**
- **1 Punkt**: Rekursiver Abbruch (keine explizite Abbruchbedingung nötig)
- **1 Punkt**: Korrekte rekursive Struktur

**Edge-Cases (1 Punkt):**
- **1 Punkt**: Behandlung von Knoten ohne/mit nur einem Kind

## Erklärung

### MinHeapify
Die Funktion arbeitet nach dem "Sink-Down" Prinzip. Sie vergleicht einen Knoten mit seinen Kindern und tauscht ihn mit dem kleinsten, falls die Min-Heap-Eigenschaft verletzt ist. Danach wird rekursiv weitergemacht.

### BuildHeap
Durch den "Bottom-Up" Ansatz wird die Heap-Eigenschaft effizient hergestellt. Blattknoten (die größere Indizes als `n//2` haben) erfüllen automatisch die Heap-Eigenschaft, da sie keine Kinder haben.

**Zeitkomplexität:**
- `minHeapify`: O(log n) - maximale Baumhöhe
- `buildHeap`: O(n log n) im Worst-Case, aber tatsächlich O(n) bei genauerer Analyse

### Rekursions-Design
Der rekursive Aufruf erfolgt nur bei Verletzung der Heap-Eigenschaft. Das Argument wird bei jedem Aufruf "größer" (tiefer im Baum), garantiert also Terminierung.

## Häufige Fehler

**MinHeapify-Implementierung:**
- **Falsche Kind-Indizes** (-2 Punkte): `left = i*2` statt `left = 2*i`
- **Grenzen nicht beachtet** (-2 Punkte): Kein Check auf `left <= n` oder `right <= n`
- **Iterativ statt rekursiv** (-2 Punkte): While-Schleife statt Rekursion
- **Fehlende Rekursion** (-2 Punkte): Nur ein Tausch ohne weiteren Aufruf
- **Falsche Rekursions-Bedingung** (-1 Punkt): Aufruf auch bei `smallest == i`

**BuildHeap-Implementierung:**
- **Falscher Startindex** (-2 Punkte): Beginnt bei `n` statt `n//2`
- **Falsche Schleifenrichtung** (-2 Punkte): Aufsteigende statt absteigende Schleife
- **Blattknoten einbezogen** (-1 Punkt): Schleife bis `n` statt bis `1`
- **Heap-Größe falsch** (-1 Punkt): `len(lst)` statt `len(lst)-1`

**Allgemeine Abzüge:**
- **Nicht-rekursive Lösung** (-3 Punkte): Aufgabe verlangte explizit Rekursion
- **Syntaxfehler** (-2 Punkte): Code nicht ausführbar
- **Schlechte Variablennamen** (-1 Punkt): Unklare Bezeichnungen
- **Keine Heap-Eigenschaft erfüllt** (-5 Punkte): Algorithmus funktional falsch