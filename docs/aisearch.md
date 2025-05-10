# AI Search & Organize Emails (`/aisearch`)

Diese Seite ermöglicht das Durchsuchen und Organisieren von E-Mails mithilfe von KI-Vorschlägen.

## Funktionen

1.  **Ordnerübersicht:**
    *   Zeigt eine Liste aller eindeutigen Ordner **aller** verbundenen E-Mail-Konten an.
    *   Die Ordnerliste wird automatisch geladen und dedupliziert.
    *   Durch Klicken auf einen Ordner werden die darin enthaltenen E-Mails geladen.

2.  **E-Mail-Liste:**
    *   Zeigt die E-Mails des ausgewählten Ordners an.
    *   Unterstützt "Load More" zum Nachladen weiterer E-Mails.
    *   Durch Klicken auf eine E-Mail wird deren Inhalt angezeigt.

3.  **E-Mail-Detailansicht:**
    *   Zeigt den Inhalt der ausgewählten E-Mail an.
    *   Bietet einen "Back to List"-Button.

4.  **Ordnerstruktur vorschlagen (Suggest Folders):**
    *   Button `Suggest Folders` (oben rechts über der Ordnerliste).
    *   Öffnet einen Dialog, in dem eine KI-generierte Ordnerstruktur basierend auf den E-Mails des **aktuell ausgewählten Ordners** vorgeschlagen wird.
    *   Der Benutzer kann auswählen, in welchem **Zielkonto** die neuen Ordner erstellt werden sollen (Dropdown im Dialog).
    *   Der Benutzer kann einzelne oder alle vorgeschlagenen Ordnerpfade auswählen.
    *   Die ausgewählten Ordner können im Zielkonto erstellt werden.

## Aktueller Stand & Hinweise

*   Die Auswahl eines spezifischen Kontos zur Filterung der Ordnerliste wurde entfernt. Es werden immer alle Ordner aller Konten (dedupliziert) angezeigt.
*   Die Funktion zum Vorschlagen und Erstellen von Ordnern bezieht sich auf die E-Mails im **aktuell in der linken Spalte ausgewählten Ordner** und erstellt die neuen Ordner im **im Dialog ausgewählten Zielkonto**. 