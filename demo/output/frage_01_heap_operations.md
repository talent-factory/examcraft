# Aufgabe 1 | Heap-Grundoperationen | 18 Punkte

## Kontext

Ein **Heap** ist ein fast vollständiger Binärbaum mit speziellen Eigenschaften. Bei einem **Min-Heap** muss der Schlüssel jedes Knotens kleiner sein als die Schlüssel seiner beiden Kinder (Min-Heap-Eigenschaft). Heaps werden als Listen repräsentiert, wobei der erste Eintrag (`lst[0]`) üblicherweise freigehalten wird (`None`). Das linke Kind von `lst[i]` befindet sich an Position `lst[2*i]` und das rechte Kind an Position `lst[2*i+1]`.

Heaps sind besonders effizient für Priority Queues, da sie das schnelle Einfügen neuer Elemente und die Extraktion des minimalen Elements ermöglichen - beides in O(log n) Zeit.

## Aufgabenstellung

Implementieren Sie die beiden fundamentalen Heap-Operationen für einen **Min-Heap**:

1. **`insert(heap, x)`** - Fügt ein Element `x` in den Heap ein
2. **`min_extract(heap)`** - Entfernt und gibt das minimale Element (Wurzel) zurück

## Code-Grundgerüst

```python
def insert(heap, x):
    """
    Fügt ein Element x in einen Min-Heap ein.
    Die Heap-Eigenschaft muss nach dem Einfügen wiederhergestellt werden.

    Args:
        heap: Liste, die einen Min-Heap repräsentiert (heap[0] = None)
        x: Das einzufügende Element

    Returns:
        None (modifiziert heap in-place)
    """
    # TODO: Implementieren Sie diese Methode
    pass

def min_extract(heap):
    """
    Entfernt das minimale Element (Wurzel) aus einem Min-Heap und
    stellt die Heap-Eigenschaft wieder her.

    Args:
        heap: Liste, die einen Min-Heap repräsentiert (heap[0] = None)

    Returns:
        Das minimale Element oder None, falls der Heap leer ist
    """
    # TODO: Implementieren Sie diese Methode
    pass

# Test-Code (nicht implementieren, nur zur Orientierung)
if __name__ == "__main__":
    # Beispiel-Heap: [None, 13, 23, 64, 29, 38, 71, 98]
    heap = [None, 13, 23, 64, 29, 38, 71, 98]

    # Test insert
    insert(heap, 5)
    print(f"Nach Einfügen von 5: {heap}")

    # Test min_extract
    min_val = min_extract(heap)
    print(f"Extrahiertes Minimum: {min_val}")
    print(f"Heap nach Extraktion: {heap}")
```

## Anforderungen

- Implementieren Sie beide Funktionen vollständig und korrekt
- Nutzen Sie die Array-Repräsentation mit `heap[0] = None`
- Die **insert**-Funktion soll das Element "nach oben" transportieren (Bubble-Up)
- Die **min_extract**-Funktion soll das Element "nach unten" transportieren (Bubble-Down)
- Beachten Sie Edge-Cases (leerer Heap, etc.)
- **Zeitkomplexität**: Beide Operationen sollen in O(log n) laufen
- **Code-Stil**: Verwenden Sie aussagekräftige Variablennamen und kommentieren Sie komplexe Stellen

## Bewertung

- **Algorithmus-Verständnis**: 6 Punkte
- **Korrekte Implementierung**: 8 Punkte
- **Code-Qualität & Edge-Cases**: 4 Punkte
- **Gesamt**: 18 Punkte
