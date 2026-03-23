# Design: Sprachauswahl UX-Verbesserung

## Problem

Die Sprachauswahl ist aktuell als Textliste im User-Dropdown der NavigationBar eingebettet. Bei 4 Sprachen funktioniert das, aber bei mehr Sprachen wird das Menü zu lang und die Sprachauswahl dominiert den Dropdown visuell. Sprache ist eine Benutzereinstellung, kein Schnellzugriff.

## Entscheidungen

- Sprachauswahl wird auf die Profilseite verschoben (Option C: eigene "Einstellungen"-Sektion)
- Select-Dropdown mit nativen Sprachnamen (skaliert auf beliebig viele Sprachen)
- Sofortiger Wechsel ohne Speichern-Button
- NavigationBar zeigt nur noch einen Hinweis mit Link zur Profilseite
- Der bestehende `/settings`-Link im Dropdown bleibt unveraendert

## Aenderungen

### 1. ProfileView.tsx: Neue "Einstellungen"-Sektion

Unterhalb der bestehenden Berechtigungen-Sektion eine neue Karte hinzufuegen:

- Ueberschrift: "Einstellungen" (uebersetzt via i18n)
- Select-Dropdown (`<select>`) mit LANGUAGE_OPTIONS (neu definiert in dieser Datei)
- Jede Option zeigt den nativen Sprachnamen: "Deutsch", "English", "Fran&ccedil;ais", "Italiano"
- Aktuelle Sprache ist vorausgewaehlt via `i18n.language`
- onChange ruft `handleLanguageChange` auf (sofortiger Wechsel)
- Beschreibungstext unter dem Dropdown: "Aendert die Sprache der gesamten Anwendung"
- `handleLanguageChange`-Logik: `i18n.changeLanguage(lng)` + `AuthService.updateProfile(token, { preferred_language: lng })` mit Fehlerbehandlung und Rollback (aus NavigationBar uebernommen)

Neue Imports in ProfileView.tsx:
- `AuthService` aus `../../services/AuthService`
- `useAuth` liefert bereits `user`; Token wird aus `localStorage` gelesen (gleicher Pattern wie NavigationBar)

### 2. NavigationBar.tsx: Dropdown vereinfachen

- Die Sprach-Buttons (LANGUAGE_OPTIONS map mit 4 Buttons) entfernen
- Die Sektion "Sprache" (Ueberschrift + Buttons) ersetzen durch ein einzelnes Link-Element
- Das Link-Element zeigt: aktuelle Sprache als Text (z.B. "Sprache: Deutsch")
- Klick navigiert zu `/profile` und schliesst das Dropdown
- Entfernen: `LANGUAGE_OPTIONS` Array, `handleLanguageChange` Funktion, `AuthService` Import
- Bestehender `/settings`-Link bleibt unveraendert

### 3. Uebersetzungsschluessel

Neue Keys in allen 4 Locale-Dateien (de, en, fr, it):

- `profile.profileView.settings` — Sektionsueberschrift ("Einstellungen")
- `profile.profileView.language` — Label fuer Dropdown ("Sprache")
- `profile.profileView.languageHint` — Beschreibungstext ("Aendert die Sprache der gesamten Anwendung")

Bestehender Key `nav.language` wird wiederverwendet fuer den NavigationBar-Link (zeigt "Sprache" als Praefix).

### 4. Betroffene Dateien

- `packages/core/frontend/src/components/profile/ProfileView.tsx` — Neue Sektion + Imports
- `packages/core/frontend/src/components/layout/NavigationBar.tsx` — Vereinfachung + Imports aufraemen
- `packages/core/frontend/src/locales/de/translation.json` — Neue Keys
- `packages/core/frontend/src/locales/en/translation.json` — Neue Keys
- `packages/core/frontend/src/locales/fr/translation.json` — Neue Keys
- `packages/core/frontend/src/locales/it/translation.json` — Neue Keys

### 5. Nicht im Scope

- Keine neuen Routen
- Keine neuen Komponenten-Dateien
- Keine Aenderungen am Backend
- Keine Aenderungen an ProfileEdit.tsx
- Keine neuen Tests (reine UI-Verschiebung bestehender Logik)
