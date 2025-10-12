# Musterlösung: Aufgabe 1 | Heap-Grundoperationen

## Vollständige Implementierung

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
    # Element am Ende anhängen
    heap.append(x)

    # Index des eingefügten Elements
    i = len(heap) - 1

    # Element nach oben transportieren (Bubble-Up)
    while i > 1 and heap[i // 2] > heap[i]:
        # Tausche mit Vaterknoten
        heap[i // 2], heap[i] = heap[i], heap[i // 2]
        i = i // 2

def min_extract(heap):
    """
    Entfernt das minimale Element (Wurzel) aus einem Min-Heap und
    stellt die Heap-Eigenschaft wieder her.

    Args:
        heap: Liste, die einen Min-Heap repräsentiert (heap[0] = None)

    Returns:
        Das minimale Element oder None, falls der Heap leer ist
    """
    # Edge-Case: Leerer Heap
    if len(heap) <= 1:
        return None

    # Edge-Case: Nur ein Element
    if len(heap) == 2:
        return heap.pop()

    # Minimum merken (Wurzel)
    min_val = heap[1]

    # Letztes Element an die Wurzel setzen
    heap[1] = heap.pop()

    # Heap-Eigenschaft wiederherstellen (Bubble-Down)
    n = len(heap) - 1  # Anzahl der Heap-Elemente
    i = 1

    while i <= n // 2:  # Solange i ein innerer Knoten ist
        # Linkes Kind
        left = 2 * i
        # Rechtes Kind (falls vorhanden)
        right = 2 * i + 1 if 2 * i + 1 <= n else left

        # Finde kleinsten Knoten unter aktuellem Knoten und seinen Kindern
        smallest = i

        if left <= n and heap[left] < heap[smallest]:
            smallest = left

        if right <= n and heap[right] < heap[smallest]:
            smallest = right

        # Wenn Heap-Eigenschaft erfüllt, beenden
        if smallest == i:
            break

        # Tausche mit kleinstem Kind
        heap[i], heap[smallest] = heap[smallest], heap[i]
        i = smallest

    return min_val

# Test-Code
if __name__ == "__main__":
    # Beispiel-Heap: [None, 13, 23, 64, 29, 38, 71, 98]
    heap = [None, 13, 23, 64, 29, 38, 71, 98]
    print(f"Ursprünglicher Heap: {heap}")

    # Test insert
    insert(heap, 5)
    print(f"Nach Einfügen von 5: {heap}")

    insert(heap, 45)
    print(f"Nach Einfügen von 45: {heap}")

    # Test min_extract
    min_val = min_extract(heap)
    print(f"Extrahiertes Minimum: {min_val}")
    print(f"Heap nach Extraktion: {heap}")

    # Mehrere Extraktionen
    while len(heap) > 1:
        min_val = min_extract(heap)
        print(f"Extrahiert: {min_val}, Heap: {heap}")
```

## Punkteverteilung

### Algorithmus-Verständnis (6 Punkte)

**Insert-Operation (3 Punkte):**

- **1 Punkt**: Verständnis, dass Element am Ende eingefügt wird
- **1 Punkt**: Erkennen, dass "Bubble-Up" zur Wurzel erforderlich ist
- **1 Punkt**: Korrekte Vater-Kind-Beziehung (`i // 2` für Vaterknoten)

**Min-Extract-Operation (3 Punkte):**

- **1 Punkt**: Verständnis, dass Wurzel das Minimum ist
- **1 Punkt**: Erkennen, dass letztes Element an die Wurzel muss
- **1 Punkt**: Verständnis des "Bubble-Down" Prozesses

### Korrekte Implementierung (8 Punkte)

**Insert-Implementierung (3 Punkte):**

- **1 Punkt**: `heap.append(x)` zum Anhängen
- **1 Punkt**: Korrekte While-Schleife mit Bedingung `i > 1 and heap[i//2] > heap[i]`
- **1 Punkt**: Korrektes Tauschen und Update von `i = i // 2`

**Min-Extract-Implementierung (5 Punkte):**

- **1 Punkt**: Rückgabe der Wurzel `heap[1]`
- **1 Punkt**: Setzen des letzten Elements an die Wurzel mit `heap.pop()`
- **1 Punkt**: Korrekte Schleifenbedingung `i <= n // 2`
- **1 Punkt**: Finden des kleinsten Elements unter Knoten und Kindern
- **1 Punkt**: Korrektes Tauschen und Fortsetzen der Schleife

### Code-Qualität & Edge-Cases (4 Punkte)

**Edge-Case-Behandlung (2 Punkte):**

- **1 Punkt**: Behandlung leerer Heap (`len(heap) <= 1`)
- **1 Punkt**: Behandlung Heap mit nur einem Element

**Code-Qualität (2 Punkte):**

- **1 Punkt**: Aussagekräftige Variablennamen (`left`, `right`, `smallest`)
- **1 Punkt**: Kommentare und saubere Struktur

## Erklärung

### Insert-Operation

Das Element wird zunächst am Ende der Liste eingefügt, wodurch die Heap-Eigenschaft verletzt werden kann. Durch "Bubble-Up" wird das Element solange mit seinem Vaterknoten getauscht, bis die Min-Heap-Eigenschaft wieder erfüllt ist.

### Min-Extract-Operation

Das minimale Element befindet sich immer an der Wurzel (`heap[1]`). Nach dem Entfernen wird das letzte Element an die Wurzel gesetzt, wodurch die Heap-Eigenschaft verletzt wird. Durch "Bubble-Down" wird das Element mit dem kleineren seiner Kinder getauscht, bis die Eigenschaft wieder erfüllt ist.

## Häufige Fehler

**Insert-Operation:**

- **Falsche Vater-Beziehung** (-1 Punkt): Verwendung von `i * 2` statt `i // 2`
- **Fehlende Schleifenbedingung** (-1 Punkt): Vergessen von `i > 1`
- **Fehlerhafte Tausch-Operation** (-1 Punkt): Inkorrekte Indizierung

**Min-Extract-Operation:**

- **Falsche Heap-Größe** (-1 Punkt): Nicht berücksichtigen, dass `heap[0] = None`
- **Infinite Loops** (-2 Punkte): Falsche Schleifenbedingungen
- **Edge-Cases ignoriert** (-1 Punkt): Keine Behandlung leerer/einelementiger Heaps
- **Falsche Kind-Indizierung** (-1 Punkt): Rechtes Kind nicht korrekt berechnet

**Allgemeine Abzüge:**

- **Schlechte Code-Qualität** (-1 Punkt): Keine Kommentare, unklare Variablennamen
- **Syntaxfehler** (-2 Punkte): Code nicht ausführbar
