# Aufgabe 2 | MinHeapify und Heap-Konstruktion | 15 Punkte

## Kontext

Die Funktion `minHeapify(heap, i)` ist eine zentrale Hilfsfunktion für Heap-Operationen. Sie stellt die Min-Heap-Eigenschaft für den Knoten an Index `i` wieder her, falls diese verletzt ist. Dies geschieht durch "nach unten" transportieren des Knotens, bis die Heap-Bedingung erfüllt ist.

Diese Funktion wird sowohl bei der Heap-Konstruktion (`buildHeap`) als auch beim Heapsort-Algorithmus verwendet. Die rekursive Implementierung ist elegant, aber auch eine iterative Version ist möglich.

## Aufgabenstellung

Implementieren Sie die Funktion `minHeapify(heap, i)`, die die Min-Heap-Eigenschaft für den Knoten an Index `i` wiederherstellt. Zusätzlich implementieren Sie `buildHeap(lst)`, die aus einer beliebigen Liste einen gültigen Min-Heap konstruiert.

## Code-Grundgerüst

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
    # TODO: Implementieren Sie diese Methode (rekursiv)
    pass

def buildHeap(lst):
    """
    Konstruiert aus einer beliebigen Liste einen gültigen Min-Heap.
    Verwendet minHeapify für alle inneren Knoten von unten nach oben.

    Args:
        lst: Liste mit beliebigen Elementen (lst[0] muss None sein)

    Returns:
        None (modifiziert lst in-place zu einem gültigen Min-Heap)
    """
    # TODO: Implementieren Sie diese Methode
    pass

# Test-Code (nicht implementieren, nur zur Orientierung)
if __name__ == "__main__":
    # Beispiel: Unsortierte Liste in Heap umwandeln
    test_list = [None, 86, 13, 23, 96, 6, 37, 29, 56, 80, 5, 92, 52, 32, 21]
    print(f"Vor buildHeap: {test_list}")

    buildHeap(test_list)
    print(f"Nach buildHeap: {test_list}")

    # Test minHeapify direkt
    test_heap = [None, 50, 13, 23, 96, 6, 37, 29]
    print(f"Vor minHeapify(heap, 1): {test_heap}")
    minHeapify(test_heap, 1)
    print(f"Nach minHeapify(heap, 1): {test_heap}")
```

## Anforderungen

- **minHeapify**: Implementieren Sie die Funktion **rekursiv**
- Finden Sie das kleinste Element unter dem Knoten und seinen beiden Kindern
- Falls der Knoten nicht das kleinste ist, tauschen Sie ihn mit dem kleinsten Kind
- Verwenden Sie Rekursion für weitere Heapify-Aufrufe
- **buildHeap**: Rufen Sie minHeapify für alle inneren Knoten auf (vom letzten inneren Knoten zur Wurzel)
- **Beachten Sie**: `len(heap)/2` gibt den Index des letzten inneren Knotens an
- **Zeitkomplexität**: minHeapify in O(log n), buildHeap in O(n log n) Worst-Case
- **Edge-Cases**: Knoten ohne Kinder, Heap mit nur einem Element

## Bewertung

- **MinHeapify Algorithmus**: 7 Punkte
- **BuildHeap Implementierung**: 5 Punkte
- **Rekursion und Edge-Cases**: 3 Punkte
- **Gesamt**: 15 Punkte
