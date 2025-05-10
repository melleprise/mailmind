import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// Hier könntest du Backend-Integration, Language Detector etc. hinzufügen
// Für den Anfang eine minimale Konfiguration:

i18n
  .use(initReactI18next) // Übergibt i18n Instanz an react-i18next.
  .init({
    // Ressourcen (Übersetzungen)
    // Füge hier deine Übersetzungsdateien hinzu oder lade sie dynamisch
    resources: {
      en: {
        translation: {
          "Welcome to React": "Welcome to React and react-i18next",
          // Füge hier weitere englische Übersetzungen hinzu
          "Failed to load request logs.": "Failed to load request logs.",
          "Failed to load log details.": "Failed to load log details.",
          "Prompt Protocol": "Prompt Protocol",
          "Timestamp": "Timestamp",
          "User": "User",
          "Provider": "Provider",
          "Model": "Model",
          "Status": "Status",
          "Duration (ms)": "Duration (ms)",
          "Actions": "Actions",
          "Success": "Success",
          "Failure": "Failure",
          "View Details": "View Details",
          "Close": "Close",
          "Request Details": "Request Details",
          "Prompt Sent": "Prompt Sent",
          "Raw Response Received": "Raw Response Received",
          "No response recorded.": "No response recorded.",
          "Details": "Details"
        }
      },
      de: {
        translation: {
          "Welcome to React": "Willkommen bei React und react-i18next",
          // Füge hier weitere deutsche Übersetzungen hinzu (aus SettingsPromptsProtocol.tsx kopiert)
          "Failed to load request logs.": "Anfrageprotokolle konnten nicht geladen werden.",
          "Failed to load log details.": "Protokolldetails konnten nicht geladen werden.",
          "Prompt Protocol": "Prompt Protokoll",
          "Timestamp": "Zeitstempel",
          "User": "Benutzer",
          "Provider": "Anbieter",
          "Model": "Modell",
          "Status": "Status",
          "Duration (ms)": "Dauer (ms)",
          "Actions": "Aktionen",
          "Success": "Erfolgreich",
          "Failure": "Fehlgeschlagen",
          "View Details": "Details anzeigen",
          "Close": "Schließen",
          "Request Details": "Anfragedetails",
          "Prompt Sent": "Gesendeter Prompt",
          "Raw Response Received": "Empfangene Rohantwort",
          "No response recorded.": "Keine Antwort aufgezeichnet.",
          "Details": "Details"
        }
      }
    },
    lng: "de", // Standardsprache
    fallbackLng: "en", // Fallback-Sprache

    interpolation: {
      escapeValue: false // react benötigt dies nicht, da es standardmäßig escaped
    }
  });

export default i18n; 