# Browser-Kompatibilität

## Download-Dateinamen Problem (Oktober 2025)

### Problem
Beim Export von Chat-Sessions als Markdown/JSON wurde der Dateiname nicht korrekt gesetzt. Statt des vom Benutzer eingegebenen Namens wurde die Session-ID verwendet.

### Ursache
**Browser-spezifisches Verhalten** bei der Verwendung von Blob-URLs:

1. **Blob-URL Ansatz** (funktioniert nicht in allen Browsern):
   ```typescript
   const blob = await response.blob();
   const url = window.URL.createObjectURL(blob);
   const link = document.createElement('a');
   link.href = url;
   link.download = 'mein-dateiname.md'; // ❌ Wird ignoriert in manchen Browsern
   link.click();
   ```

2. **Data-URL Ansatz** (funktioniert zuverlässiger):
   ```typescript
   const blob = await response.blob();
   const reader = new FileReader();
   reader.onload = () => {
     const dataUrl = reader.result as string;
     const link = document.createElement('a');
     link.href = dataUrl;
     link.download = 'mein-dateiname.md'; // ✅ Funktioniert
     link.click();
   };
   reader.readAsDataURL(blob);
   ```

### Lösung
Verwende **Data-URLs** statt Blob-URLs für Downloads mit benutzerdefinierten Dateinamen.

**Implementierung:** `frontend/src/components/DocumentChat/ChatInterface.tsx` (Zeile 97-145)

### Betroffene Browser
- ❌ **Safari** (macOS): Ignoriert `download` Attribut bei Blob-URLs
- ✅ **Chrome/Edge**: Funktioniert mit beiden Ansätzen
- ✅ **Firefox**: Funktioniert mit beiden Ansätzen

### Lessons Learned
1. **Immer in mehreren Browsern testen** (Chrome, Firefox, Safari)
2. **E2E-Tests für kritische User-Flows** erstellen
3. **Browser-spezifische Workarounds dokumentieren**

### Related Tasks
- TF-148: GUI Modernization
- Siehe `docs/testing-strategy.md` für E2E-Test-Implementierung

### References
- MDN: [HTMLAnchorElement.download](https://developer.mozilla.org/en-US/docs/Web/API/HTMLAnchorElement/download)
- MDN: [FileReader.readAsDataURL()](https://developer.mozilla.org/en-US/docs/Web/API/FileReader/readAsDataURL)

