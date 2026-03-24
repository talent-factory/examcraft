# Aufgabe 3 | Heapsort-Algorithmus | 20 Punkte

## Kontext

**Heapsort** ist ein effizienter Sortieralgorithmus mit garantierter O(n log n) Zeitkomplexität. Der Algorithmus arbeitet in zwei Phasen:

1. **Heap-Konstruktion**: Die unsortierte Liste wird in einen Heap umgewandelt
2. **Sortierung**: Iterativ wird das Maximum/Minimum extrahiert und am Ende der sortierten Liste platziert

Heapsort ist ein **In-Place-Sortierverfahren**, das keinen zusätzlichen Speicher benötigt. Für aufsteigende Sortierung verwendet man einen **Max-Heap** (größtes Element an der Wurzel), für absteigende Sortierung einen **Min-Heap**.

Die Schleifeninvariante von Heapsort besagt: Zu Beginn jedes Schleifendurchlaufs bildet `lst[1:i+1]` einen gültigen Heap mit den i größten Elementen, während `lst[i+1:]` die sortierten kleineren Elemente enthält.

## Aufgabenstellung

Implementieren Sie den vollständigen **Heapsort-Algorithmus** für aufsteigende Sortierung. Dazu benötigen Sie eine modifizierte Version von `maxHeapify`, die nur bis zu einem bestimmten Index arbeitet.

## Code-Grundgerüst

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
    # TODO: Implementieren Sie diese Methode für Max-Heap
    pass

def buildMaxHeap(lst):
    """
    Konstruiert aus einer Liste einen gültigen Max-Heap.

    Args:
        lst: Liste mit beliebigen Elementen (lst[0] = None)

    Returns:
        None (modifiziert lst in-place zu einem Max-Heap)
    """
    # TODO: Implementieren Sie diese Methode
    pass

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
    # TODO: Implementieren Sie den vollständigen Heapsort-Algorithmus
    pass

# Test-Code (nicht implementieren, nur zur Orientierung)
if __name__ == "__main__":
    # Test mit verschiedenen Beispielen
    test_cases = [
        [None, 4, 1, 3, 2, 16, 9, 10, 14, 8, 7],
        [None, 64, 23, 13, 96, 6, 37, 29, 56, 80, 5],
        [None, 5, 2, 4, 6, 1, 3],
        [None, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    ]

    for i, test_list in enumerate(test_cases):
        original = test_list.copy()
        print(f"Test {i+1} - Vor Sortierung: {original[1:]}")
        heapSort(test_list)
        print(f"Test {i+1} - Nach Sortierung: {test_list[1:]}")
        print()
```

## Anforderungen

- **MaxHeapify**: Implementieren Sie für Max-Heap (größtes Element nach oben)
- Der Parameter `heap_size` begrenzt den aktiven Heap-Bereich
- **BuildMaxHeap**: Konstruiert Max-Heap aus beliebiger Liste
- **HeapSort**: Vollständige In-Place-Sortierung
  - Erst buildMaxHeap() aufrufen
  - Dann in Schleife: Maximum mit letztem Element tauschen und Heap verkleinern
  - Nach jedem Tausch maxHeapify() zur Wiederherstellung der Heap-Eigenschaft
- **Sortierung**: Aufsteigend (kleinstes Element zuerst)
- **Zeitkomplexität**: O(n log n) für alle Fälle
- **Speicherkomplexität**: O(1) zusätzlicher Speicher (In-Place)

## Bewertung

- **MaxHeapify Implementierung**: 5 Punkte
- **BuildMaxHeap Implementierung**: 4 Punkte
- **HeapSort Algorithmus**: 8 Punkte
- **Korrektheit und Effizienz**: 3 Punkte
- **Gesamt**: 20 Punkte
