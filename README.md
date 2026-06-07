# Laborsuche DACH

Dieses Projekt löst die Aufgabe, die in `BEWERBUNGSAUFGABE.md` beschrieben ist.

Ziel des Projekts ist es, eine Webanwendung zu entwickeln, die Nutzern hilft, verifizierte Anbieter im DACH-Raum für zwei gesundheitsbezogene Leistungen zu finden:

1. DEXA Body Composition Scans
2. Blutuntersuchungen als Selbstzahler ohne ärztliche Überweisung

Die Anwendung enthält eine strukturierte Datenbasis mit verifizierten Anbietern und visualisiert diese auf einer interaktiven Karte mit Kategorie-Filtern, farbigen Markern, Popups und einer Sidebar.

## Akzeptanzkriterien für Anbieter

### DEXA Body Composition Scan

Ein Anbieter wird nur dann als DEXA-Anbieter akzeptiert, wenn er eindeutig einen echten DEXA/DXA Body Composition Scan anbietet.

Der Anbieter darf nicht nur eine normale Knochendichtemessung zur Osteoporose-Diagnostik anbieten. Ein gültiger DEXA Body Composition Anbieter muss klare Hinweise auf eine Ganzkörpermessung liefern, bei der die Körperzusammensetzung gemessen wird.

Dazu gehören zum Beispiel:

* DEXA/DXA-Technologie
* Ganzkörpermessung
* Körperfett oder Fettmasse
* Muskelmasse oder Lean Mass
* Knochendichte oder Knochenmasse

### Blutuntersuchung als Selbstzahler

Ein Anbieter wird nur dann als Blutlabor akzeptiert, wenn Privatpersonen oder Selbstzahler dort Blutuntersuchungen ohne ärztliche Überweisung durchführen lassen können.

Wichtige Hinweise sind zum Beispiel:

* Blutabnahme
* Laboranalyse
* Selbstzahler oder Privatleistung
* ohne ärztliche Überweisung
* Direktlabor oder Walk-in-Labor

## Projektstruktur

```txt
ANBIETER-FINDER/
├── Daten/
│   ├── candidates.json
│   ├── manual_review_candidates.json
│   └── verified_providers.json
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   └── ProviderMap.jsx
│   │   ├── data/
│   │   │   └── providers.json
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── eslint.config.js
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── README.md
│   └── vite.config.js
├── scripts/
│   ├── search_candidates.py
│   └── ai_verifier.py
├── .env
├── BEWERBUNGSAUFGABE.md
└── README.md
```

## Datensammlung mit `search_candidates.py`

Der erste Schritt des Projekts wird durch folgendes Skript umgesetzt:

```txt
scripts/search_candidates.py
```

Dieses Skript sammelt potenzielle Anbieter-Kandidaten mithilfe der Google Places API über Google Cloud.

Das Skript sendet konfigurierbare Suchanfragen an die Google Places API. Google gibt daraufhin mögliche passende Orte zurück, inklusive Name des Anbieters, Adresse, Koordinaten, Telefonnummer, Website und Google-Maps-Link.

Diese Ergebnisse werden noch nicht als verifizierte Anbieter betrachtet. Sie werden zunächst nur als Rohkandidaten gespeichert.

Die generierten Kandidaten werden gespeichert unter:

```txt
Daten/candidates.json
```

### Suchstrategie

Die Suche basiert auf drei konfigurierbaren Teilen:

1. Städtelisten
2. Suchvorlagen für DEXA
3. Suchvorlagen für Blutlabore

Für jede Stadt erstellt das Skript automatisch mehrere Suchanfragen für beide Kategorien:

* DEXA Body Composition Scan
* Blutuntersuchung als Selbstzahler ohne ärztliche Überweisung

Dadurch ist der Ansatz skalierbar. Neue Städte oder neue Suchbegriffe können einfach ergänzt werden, ohne die Hauptlogik des Skripts zu verändern.

### Abgedeckte Regionen

Für Deutschland sucht das Skript breit über viele große und medizinisch relevante Städte, zum Beispiel Berlin, Hamburg, München, Köln, Frankfurt am Main, Stuttgart, Düsseldorf, Dortmund, Essen, Leipzig, Bremen, Dresden, Hannover, Nürnberg, Braunschweig und weitere Städte.

Für Österreich konzentriert sich der aktuelle Prototyp auf:

* Wien

Für die Schweiz konzentriert sich der aktuelle Prototyp auf:

* Zürich

Weitere Städte in Deutschland, Österreich oder der Schweiz können durch Erweiterung der entsprechenden Städtelisten einfach hinzugefügt werden.

### Suchbegriffe

Die DEXA-Suchanfragen wurden so formuliert, dass sie Anbieter finden, die möglicherweise echte DEXA Body Composition Scans anbieten und nicht nur normale Knochendichtemessungen.

Dafür werden Begriffe verwendet wie:

* DEXA Body Composition
* DXA Ganzkörper
* Körperzusammensetzung
* Körperfett
* Muskelmasse
* Knochendichte

Die Suchanfragen für Blutlabore wurden so formuliert, dass sie Anbieter finden, die Blutuntersuchungen für Privatpersonen oder Selbstzahler ohne ärztliche Überweisung anbieten könnten.

Dafür werden Begriffe verwendet wie:

* Blutlabor Selbstzahler
* Blutuntersuchung Selbstzahler
* Labor Blutabnahme ohne Überweisung
* Direktlabor Selbstzahler Blutabnahme
* Bluttest ohne ärztliche Überweisung

### Ausgabe der Kandidaten

Jeder Kandidat in `Daten/candidates.json` enthält folgende Informationen:

* verwendete Suchanfrage
* gesuchte Stadt
* gesuchtes Land
* Zielkategorie
* Name des Anbieters
* Adresse
* Koordinaten
* Telefonnummer
* Website
* Google-Maps-Link
* Verifizierungsstatus

Der Status wird zunächst auf `candidate` gesetzt, weil die Google Places API nur potenzielle Treffer liefert. Sie beweist nicht, dass ein Anbieter die Kriterien der Aufgabe wirklich erfüllt.

### Duplikat-Erkennung

Da derselbe Anbieter durch verschiedene Suchanfragen oder verschiedene Städte mehrfach gefunden werden kann, entfernt das Skript Duplikate vor dem Speichern der finalen Kandidatenliste.

Duplikate werden über einen erzeugten Schlüssel aus Anbietername und Adresse erkannt.

## Verifizierung der Kandidaten

Nach der Sammlung der Rohkandidaten bestand die nächste Herausforderung darin zu prüfen, ob jeder Kandidat wirklich die Anforderungen der Coding Challenge erfüllt.

### Verifizierungsansatz 1: Batch-Review mit einem KI-Tool

Der erste Verifizierungsansatz war ein Batch-basierter Review-Prozess.

Die Datei `Daten/candidates.json` wurde einem KI-Tool bereitgestellt und in Gruppen von ungefähr 100 Kandidaten geprüft.

Jeder Kandidat wurde in eine von drei Gruppen eingeordnet:

* `accept`
* `manual_review`
* `reject`

Die akzeptierten Kandidaten wurden geprüft und sahen für die finale Datenbasis geeignet aus. Die Kandidaten im Bereich `manual_review` wurden grundsätzlich ebenfalls sinnvoll klassifiziert, benötigten aber zusätzliche manuelle Prüfung, bevor sie übernommen werden konnten. Die abgelehnten Kandidaten wurden als nicht relevant für die Aufgabe behandelt und nicht in die finale Datenbasis übernommen.

Dieser Prozess half dabei, die ursprüngliche Kandidatenliste zu reduzieren und sich auf Anbieter zu konzentrieren, die wahrscheinlich zu den Kriterien passen.

### Verifizierungsansatz 2: Automatisierte Website-Prüfung mit Gemini

Als zusätzlicher Ansatz wurde folgendes Skript erstellt:

```txt
scripts/ai_verifier.py
```

Dieses Skript wurde entwickelt, um Kandidaten automatisch mit der Gemini API zu verifizieren.

Das Skript liest die Kandidaten aus:

```txt
Daten/candidates.json
```

Für jeden Kandidaten öffnet das Skript die Website des Anbieters, extrahiert relevante Website-Texte und sendet diese an Gemini. Gemini prüft den Anbieter anschließend anhand der zwei strengen Kriterien:

1. Bietet der Anbieter eindeutig DEXA/DXA Body Composition und nicht nur Knochendichtemessung an?
2. Bietet der Anbieter eindeutig Blutuntersuchungen für Selbstzahler ohne ärztliche Überweisung an?

Die Antwort wird in einem strukturierten JSON-Format angefordert. Dadurch kann das Ergebnis leichter automatisch verarbeitet werden.

Wenn ein Anbieter zu einer der beiden Kategorien passt, wird er gespeichert in:

```txt
Daten/verified_providers_ai.json
```

### Einschränkung der Gemini-Verifizierung

Die Gemini-basierte Verifizierung funktionierte als möglicher Automatisierungsansatz. Allerdings wurde das erlaubte API-Anfragelimit zu schnell erreicht.

Aus diesem Grund wurde die vollständige Verifizierung nicht ausschließlich mit dieser Methode fortgeführt. Stattdessen wurde der erste Verifizierungsansatz mit Batch-Review und manuellen Qualitätsprüfungen für die finale Datenbasis verwendet.

## Datendateien

Der Ordner `Daten/` enthält die Zwischen- und Enddateien des Recherche- und Verifizierungsprozesses.

* `candidates.json`
  Diese Datei enthält die Rohkandidaten, die mit `scripts/search_candidates.py` gesammelt wurden.

* `manual_review_candidates.json`
  Diese Datei enthält Kandidaten, die im ersten Review-Schritt nicht sicher akzeptiert oder abgelehnt werden konnten.
  Sie wurde während des KI-gestützten Batch-Reviews erstellt.

* `verified_providers.json`
  Diese Datei enthält die final akzeptierten Anbieter nach dem Review-Prozess.
  Sie wurde aus dem KI-gestützten Review und manuellen Qualitätsprüfungen erstellt.

Das React-Frontend verwendet eine für das Frontend vorbereitete Kopie der verifizierten Daten:

```txt
frontend/src/data/providers.json
```

## Frontend-Implementierung

Das Frontend befindet sich im Ordner `frontend/` und wurde mit React und Vite entwickelt.

Das Hauptziel des Frontends ist es, die verifizierten Anbieter aus der finalen Datenbasis auf einer interaktiven Karte darzustellen.

### Verwendete Technologien

Das Frontend verwendet folgende Technologien:

* React
* Vite
* JavaScript
* CSS
* Leaflet
* React-Leaflet
* OpenStreetMap Tiles

React wird für den Aufbau der Benutzeroberfläche mit wiederverwendbaren Komponenten verwendet. Vite dient als Build-Tool und ermöglicht eine schnelle Entwicklungsumgebung. Leaflet und React-Leaflet werden genutzt, um die interaktive Karte, Marker und Popups darzustellen.

### Relevante Frontend-Dateien

Die wichtigsten Frontend-Dateien sind:

* `frontend/src/App.jsx`
  Dies ist die Hauptkomponente der Anwendung. Sie rendert den Header der Seite und bindet die Kartenkomponente ein.

* `frontend/src/components/ProviderMap.jsx`
  Diese Komponente enthält die Hauptlogik der Karte. Sie lädt die Anbieterdaten, filtert die Anbieter nach Kategorie und rendert Sidebar, Marker, Popups und Detailbereich.

* `frontend/src/data/providers.json`
  Diese Datei enthält die für das Frontend vorbereitete Datenbasis. Sie ist eine Kopie der verifizierten Anbieter und wird direkt von der React-Anwendung importiert.

* `frontend/src/index.css`
  Diese Datei enthält das Styling der Anwendung, zum Beispiel Layout, Sidebar, Anbieter-Karten, Buttons, Kartenbereich, Popups und responsives Design.

### Nutzung der Daten im Frontend

Das React-Frontend importiert die Anbieterdaten aus:

```txt
frontend/src/data/providers.json
```

Diese Daten werden verwendet, um alle verifizierten Anbieter auf der Karte anzuzeigen.

Jeder Anbieter enthält Informationen wie:

* Name des Anbieters
* Kategorie
* Adresse
* Koordinaten
* Kontaktinformationen
* Website
* Google-Maps-Link
* Selbstzahler-Status
* optionale Preisinformationen

Die Koordinaten sind besonders wichtig, weil sie genutzt werden, um die Marker der Anbieter auf der Karte zu platzieren.

### Kartenfunktionen

Die Karte bietet folgende Funktionen:

* interaktive Karte auf Basis von OpenStreetMap
* ein Marker pro Anbieter mit gültigen Koordinaten
* unterschiedliche Markerfarben nach Kategorie

  * blauer Marker für DEXA-Anbieter
  * roter Marker für Blutlabore
* Popup mit Anbieterinformationen beim Klick auf einen Marker
* Sidebar mit allen Anbietern
* Kategorie-Filter:

  * alle Anbieter
  * nur DEXA-Anbieter
  * nur Blutlabore
* Detailbereich für den ausgewählten Anbieter
* responsives Layout für Desktop und mobile Geräte

### Filterlogik

Das Frontend erlaubt es Nutzern, Anbieter nach Kategorie zu filtern.

Die verfügbaren Filter sind:

* `Alle`
* `DEXA`
* `Blutlabor`

Wenn ein Filter ausgewählt wird, werden nur Anbieter der entsprechenden Kategorie in der Sidebar und auf der Karte angezeigt.

### Angezeigte Anbieterinformationen

Das Frontend zeigt nur Informationen an, die für Nutzer relevant sind.

Angezeigt werden:

* Name
* Kategorie
* Adresse
* kurze Leistungsbeschreibung
* Selbstzahler-Status
* Preis, falls öffentlich verfügbar
* Telefonnummer, falls vorhanden
* Website-Link, falls vorhanden
* Google-Maps-Link, falls vorhanden

Interne Verifizierungsinformationen werden im Frontend nicht angezeigt, weil sie für die nutzerorientierte Kartenansicht nicht notwendig sind.

### Preisanzeige

Preise werden nur angezeigt, wenn öffentliche und eindeutige Preisinformationen in den Daten vorhanden sind.

Wenn keine zuverlässige öffentliche Preisinformation gefunden wurde, wird im User Interface kein Preis angezeigt.
## Umgebungsvariablen 

Für die Datensammlung und die optionale KI-Verifizierung werden API-Schlüssel benötigt.

Diese Schlüssel werden lokal in einer `.env`-Datei gespeichert:

```txt
GOOGLE_PLACES_API_KEY=your_google_places_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```


Der `GOOGLE_PLACES_API_KEY` wird von `scripts/search_candidates.py` verwendet, um Kandidaten über die Google Places API zu sammeln.

Der `GEMINI_API_KEY` wird von `scripts/ai_verifier.py` verwendet, um Anbieter-Websites automatisiert mit Gemini zu prüfen.

## Projekt lokal starten

### Voraussetzungen

Für das Frontend werden benötigt:

* Node.js
* npm

### Frontend installieren

Zuerst in den Frontend-Ordner wechseln:

```bash
cd frontend
```

Dann die Abhängigkeiten installieren:

```bash
npm install
```

### Entwicklungsserver starten

Die Anwendung kann lokal mit folgendem Befehl gestartet werden:

```bash
npm run dev
```

Danach zeigt Vite eine lokale URL an:

```txt
http://localhost:5173
```
## Was ich mit mehr Zeit noch machen würde

Mit mehr Zeit würde ich vor allem die Datenqualität weiter verbessern und die Anwendung technisch erweitern.

Mögliche nächste Schritte wären:

* Die Ergebnisse mit weiteren Fachpersonen gegenprüfen.
* Weitere Städte in Deutschland, Österreich und der Schweiz ergänzen, insbesondere für DEXA-Anbieter.
* Die Datei `manual_review_candidates.json` vollständig manuell durchgehen.
* Bei Unsicherheiten Anbieter direkt kontaktieren, zum Beispiel telefonisch oder per E-Mail.
* Marker-Clustering für viele Anbieter ergänzen.
* Eine Backend-API oder Datenbank statt einer statischen JSON-Datei verwenden.
* Ein Docker-Setup ergänzen, damit das Projekt einfacher gestartet werden kann.
