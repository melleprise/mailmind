# AI Actions

## Ziel
Dieses Verzeichnis enthält alle Komponenten, Typen und Logik für wiederverwendbare, datenbankgestützte AI Actions (AI Agenten), die im System als eigenständige Tasks ausgeführt werden können.

## Features
- Verwaltung von AI Actions im Settings-Menü
- Jede Action kann einen oder mehrere Prompts enthalten
- Jede Action ist ein eigenständiger AI Agent (z.B. hole alle Links, hole Unsubscribe-Link, etc.)
- Actions können per MCP (Multi-Chain-Processing) ausgeführt werden
- Prompts werden über ein generisches Prompt-Fenster an den Agenten übergeben
- Actions können beliebig erweitert, sortiert und aktiviert/deaktiviert werden

## Komponenten
- ActionList: Zeigt alle verfügbaren Actions an
- ActionForm: Erstellen/Bearbeiten einer Action inkl. Prompts
- ActionRunner: Startet eine Action und zeigt den Fortschritt/Status an

## Hinweise
- Die Actions werden in der Datenbank gespeichert und können dynamisch erweitert werden
- Jede Action ist lose an einen oder mehrere Prompts gebunden
- Die Ausführung erfolgt asynchron über das Backend (MCP)

---
Letzte Aktualisierung: $(date) 