# Prompt-Kontext & KnowledgeFields: {cv} und {agent}

## Zweck
Die Platzhalter `{cv}` und `{agent}` werden in Prompt-Templates verwendet, um dynamisch Kontext aus der Knowledge Base des Nutzers einzufügen.

## Funktionsweise
- Die Backend-Logik sucht beim Ausführen eines Prompts nach KnowledgeFields mit den Keys `cv` und `agent` für den jeweiligen User.
- Die Werte dieser Felder werden automatisch in den Prompt-Kontext eingefügt und ersetzen die Platzhalter `{cv}` und `{agent}` im Template.
- Fehlt ein Wert, kann (je nach Implementierung) ein Default-Text eingefügt werden oder der Task bricht mit einem klaren Fehler ab.

## Best Practices
- **Jedes Prompt-Template, das `{cv}` oder `{agent}` verwendet, muss sicherstellen, dass diese Felder in der Knowledge Base gepflegt sind.**
- Templates dürfen keine Platzhalter verwenden, die nicht garantiert im Kontext vorhanden sind.
- Änderungen an der Knowledge-Logik immer hier dokumentieren.

## Fehlervermeidung
- Vor jedem `.format(**prompt_context)`-Aufruf muss geprüft werden, ob alle Platzhalter im Kontext vorhanden sind.
- Bei neuen Platzhaltern immer die Knowledge Base und die Prompt-Templates synchron halten.

## Beispiel (Prompt-Auszug)
```
weiterer kontext:
```
{cv}
```

Deine Aufgabe:
```
{agent}
```
```

## Pflege
- Die KnowledgeFields können im Admin oder über ein passendes Frontend gepflegt werden.
- Änderungen an den Prompts oder der Knowledge-Logik immer in dieser Datei dokumentieren. 