# Musterlösung: Aufgabe 3 | Heapsort-Algorithmus

## Vollständige Implementierung

```python
def maxHeapify(heap, i, heap_size):
    """
    Max-Heapify Operation, die nur bis heap_size arbeitet.
    Stellt die Max-Heap-Eigenschaft für Knoten i wieder her.

    Args:
        heap: Liste, die einen Heap repräsentiert (heap[0] = None)
        i: Index des Knotens für Heapify-Operation
        heap_size: Aktuelle Größe des Heap-Bereichs (exclusive heap[0])

    Returns:
        None (modifiziert heap in-place)
    """
    # Indizes der Kinder
    left = 2 * i
    right = 2 * i + 1

    # Finde den Index des größten Elements unter i und seinen Kindern
    largest = i

    # Prüfe linkes Kind (nur wenn es im aktuellen Heap-Bereich liegt)
    if left <= heap_size and heap[left] > heap[largest]:
        largest = left

    # Prüfe rechtes Kind (nur wenn es im aktuellen Heap-Bereich liegt)
    if right <= heap_size and heap[right] > heap[largest]:
        largest = right

    # Falls die Max-Heap-Eigenschaft verletzt ist
    if largest != i:
        # Tausche aktuellen Knoten mit größtem Kind
        heap[i], heap[largest] = heap[largest], heap[i]

        # Rekursiver Aufruf für das getauschte Kind
        maxHeapify(heap, largest, heap_size)

def buildMaxHeap(lst):
    """
    Konstruiert aus einer Liste einen gültigen Max-Heap.

    Args:
        lst: Liste mit beliebigen Elementen (lst[0] = None)

    Returns:
        None (modifiziert lst in-place zu einem Max-Heap)
    """
    heap_size = len(lst) - 1  # Anzahl der Heap-Elemente

    # Starte mit dem letzten inneren Knoten und arbeite nach oben
    for i in range(heap_size // 2, 0, -1):
        maxHeapify(lst, i, heap_size)

def heapSort(lst):
    """
    Sortiert eine Liste aufsteigend mit dem Heapsort-Algorithmus.

    Algorithmus:
    1. Baue Max-Heap aus der Liste
    2. Wiederhole für i von len(lst)-1 bis 2:
       - Tausche lst[1] (Maximum) mit lst[i]
       - Reduziere Heap-Größe um 1
       - Rufe maxHeapify(lst, 1, i-1) auf

    Args:
        lst: Zu sortierende Liste (lst[0] muss None sein)

    Returns:
        None (sortiert lst in-place aufsteigend)
    """
    # Schritt 1: Baue Max-Heap aus der unsortierten Liste
    buildMaxHeap(lst)

    # Schritt 2: Extrahiere Elemente vom Heap und sortiere
    heap_size = len(lst) - 1

    # Für alle Elemente außer der Wurzel
    for i in range(heap_size, 1, -1):
        # Tausche Maximum (Wurzel) mit letztem Heap-Element
        lst[1], lst[i] = lst[i], lst[1]

        # Reduziere Heap-Größe (sortierte Elemente am Ende ausschließen)
        heap_size -= 1

        # Stelle Max-Heap-Eigenschaft wieder her
        maxHeapify(lst, 1, heap_size)

# Test-Code
if __name__ == "__main__":
    # Hilfsfunktion für Verifikation
    def is_sorted(lst):
        """Prüft, ob eine Liste (ohne lst[0]) aufsteigend sortiert ist"""
        for i in range(2, len(lst)):
            if lst[i-1] > lst[i]:
                return False
        return True

    def is_max_heap(heap, heap_size=None):
        """Prüft, ob ein Heap die Max-Heap-Eigenschaft erfüllt"""
        if heap_size is None:
            heap_size = len(heap) - 1

        for i in range(1, heap_size // 2 + 1):
            left = 2 * i
            right = 2 * i + 1

            if left <= heap_size and heap[i] < heap[left]:
                return False
            if right <= heap_size and heap[i] < heap[right]:
                return False
        return True

    # Test mit verschiedenen Beispielen
    test_cases = [
        [None, 4, 1, 3, 2, 16, 9, 10, 14, 8, 7],
        [None, 64, 23, 13, 96, 6, 37, 29, 56, 80, 5],
        [None, 5, 2, 4, 6, 1, 3],
        [None, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
        [None, 1],  # Einzelelement
        [None, 3, 1]  # Zwei Elemente
    ]

    for i, test_list in enumerate(test_cases):
        original = test_list.copy()
        print(f"Test {i+1} - Original: {original[1:]}")

        # Test buildMaxHeap
        buildMaxHeap(test_list)
        print(f"Nach buildMaxHeap: {test_list[1:]}")
        print(f"Ist Max-Heap: {is_max_heap(test_list)}")

        # Test heapSort
        heapSort(original)
        print(f"Nach heapSort: {original[1:]}")
        print(f"Ist sortiert: {is_sorted(original)}")
        print("-" * 50)

    # Performance-Test (optional)
    import random
    import time

    # Große zufällige Liste erstellen
    large_list = [None] + [random.randint(1, 1000) for _ in range(1000)]

    start_time = time.time()
    heapSort(large_list)
    end_time = time.time()

    print(f"Sortierung von 1000 Elementen: {end_time - start_time:.4f} Sekunden")
    print(f"Ist sortiert: {is_sorted(large_list)}")
```

## Punkteverteilung

### MaxHeapify Implementierung (5 Punkte)

**Grundlegende Logik (3 Punkte):**

- **1 Punkt**: Korrekte Berechnung der Kind-Indizes (`left = 2*i`, `right = 2*i+1`)
- **1 Punkt**: Finden des größten Elements (`heap[left] > heap[largest]`)
- **1 Punkt**: Berücksichtigung des `heap_size` Parameters (`left <= heap_size`)

**Max-Heap Spezifika (2 Punkte):**

- **1 Punkt**: Vergleich für Max-Heap (größtes Element nach oben)
- **1 Punkt**: Rekursiver Aufruf mit korrektem `heap_size`

### BuildMaxHeap Implementierung (4 Punkte)

**Heap-Konstruktion (4 Punkte):**

- **1 Punkt**: Korrekte Berechnung der Heap-Größe
- **1 Punkt**: Schleife von letztem inneren Knoten zur Wurzel
- **1 Punkt**: Aufruf von `maxHeapify` mit korrekter Heap-Größe
- **1 Punkt**: Bottom-Up Ansatz verstanden und implementiert

### HeapSort Algorithmus (8 Punkte)

**Heap-Konstruktion (2 Punkte):**

- **1 Punkt**: Aufruf von `buildMaxHeap(lst)` am Anfang
- **1 Punkt**: Korrekte Initialisierung von `heap_size`

**Sortier-Schleife (4 Punkte):**

- **1 Punkt**: Korrekte Schleife `range(heap_size, 1, -1)`
- **1 Punkt**: Tausch von Maximum mit letztem Element
- **1 Punkt**: Reduzierung der Heap-Größe (`heap_size -= 1`)
- **1 Punkt**: Aufruf von `maxHeapify(lst, 1, heap_size)`

**Algorithmus-Verständnis (2 Punkte):**

- **1 Punkt**: Verständnis der In-Place Sortierung
- **1 Punkt**: Korrekte Schleifeninvariante umgesetzt

### Korrektheit und Effizienz (3 Punkte)

**Funktionale Korrektheit (2 Punkte):**

- **1 Punkt**: Algorithmus produziert korrekt sortierte Ausgabe
- **1 Punkt**: Heap-Eigenschaft wird korrekt aufrecht erhalten

**Effizienz (1 Punkt):**

- **1 Punkt**: O(n log n) Zeitkomplexität eingehalten, In-Place implementiert

## Erklärung

### Heapsort-Algorithmus

**Phase 1 - Heap-Konstruktion:**
Die unsortierte Liste wird in einen Max-Heap umgewandelt. Dies geschieht in O(n log n) Zeit durch `buildMaxHeap`.

**Phase 2 - Sortierung:**
Iterativ wird das Maximum (Wurzel) mit dem letzten Element getauscht und aus dem Heap entfernt. Der verkleinerte Heap wird durch `maxHeapify` repariert.

**Schleifeninvariante:**

- `lst[1:heap_size+1]` bildet einen Max-Heap mit den `heap_size` größten Elementen
- `lst[heap_size+1:]` enthält die sortierten kleineren Elemente

**Zeitkomplexität:**

- Worst-Case: O(n log n)
- Average-Case: O(n log n)
- Best-Case: O(n log n)

**Speicherkomplexität:** O(1) zusätzlicher Speicher (In-Place)

### Warum Max-Heap für aufsteigende Sortierung?

Da wir aufsteigend sortieren wollen, benötigen wir das größte Element zuerst. Ein Max-Heap liefert das Maximum an der Wurzel, das dann an die richtige Position (Ende) getauscht wird.

## Häufige Fehler

**MaxHeapify-Implementierung:**

- **Min- statt Max-Heap** (-3 Punkte): `heap[left] < heap[largest]` statt `>`
- **heap_size ignoriert** (-2 Punkte): Vergleich ohne Berücksichtigung der aktuellen Heap-Größe
- **Falsche Rekursion** (-1 Punkt): Aufruf ohne `heap_size` Parameter

**BuildMaxHeap-Implementierung:**

- **Falscher Heapify-Aufruf** (-2 Punkte): Ohne `heap_size` Parameter
- **Falsche Schleifenrichtung** (-1 Punkt): Aufsteigend statt absteigend
- **Min-Heap gebaut** (-2 Punkte): Verwendung von minHeapify statt maxHeapify

**HeapSort-Algorithmus:**

- **Keine Heap-Konstruktion** (-3 Punkte): buildMaxHeap nicht aufgerufen
- **Falsche Tausch-Operation** (-2 Punkte): Falsche Indizes beim Tauschen
- **Heap-Größe nicht reduziert** (-2 Punkte): `heap_size` bleibt konstant
- **Falsche Schleifengrenzen** (-2 Punkte): Schleife bis 0 statt bis 2
- **Max-Heapify falsch aufgerufen** (-2 Punkte): Falsche Parameter oder Index

**Allgemeine Abzüge:**

- **Absteigende statt aufsteigende Sortierung** (-3 Punkte): Falsche Sortierrichtung
- **Nicht In-Place** (-2 Punkte): Verwendung zusätzlicher Arrays
- **Syntaxfehler** (-2 Punkte): Code nicht ausführbar
- **Schlechte Code-Struktur** (-1 Punkt): Unklare Variablennamen, fehlende Kommentare
