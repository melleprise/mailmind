"""
Beispiel wie API-Keys aus der Datenbank abgerufen und genutzt werden können.
Dieses Skript ist als Referenz gedacht und sollte nicht direkt ausgeführt werden.
"""

import logging
from django.contrib.auth import get_user_model
from mailmind.core.models import APICredential
from google import generativeai as genai
from groq import Groq

User = get_user_model()
logger = logging.getLogger(__name__)

def get_api_key_for_user(user_id, provider):
    """
    Holt den API-Key eines bestimmten Nutzers für einen Anbieter.
    
    Args:
        user_id: ID des Nutzers
        provider: String mit dem Provider-Namen (z.B. 'google_gemini', 'groq')
        
    Returns:
        Der entschlüsselte API-Key oder None, wenn nicht gefunden/entschlüsselt
    """
    try:
        # Nutzer abrufen
        user = User.objects.get(id=user_id)
        
        # APICredential-Objekt abrufen
        credential = APICredential.objects.get(user=user, provider=provider)
        
        # API-Key entschlüsseln
        api_key = credential.get_api_key()
        
        if not api_key:
            logger.error(f"API-Key für Nutzer {user_id} und Provider {provider} konnte nicht entschlüsselt werden")
            return None
            
        logger.debug(f"API-Key für Nutzer {user_id} und Provider {provider} erfolgreich abgerufen")
        return api_key
        
    except User.DoesNotExist:
        logger.error(f"Nutzer mit ID {user_id} nicht gefunden")
        return None
    except APICredential.DoesNotExist:
        logger.error(f"Keine API-Credentials für Nutzer {user_id} und Provider {provider} gefunden")
        return None
    except Exception as e:
        logger.exception(f"Fehler beim Abrufen des API-Keys: {str(e)}")
        return None

def use_google_gemini_api(user_id):
    """Beispiel für die Nutzung des Google Gemini API"""
    api_key = get_api_key_for_user(user_id, 'google_gemini')
    
    if not api_key:
        return "API-Key konnte nicht abgerufen werden"
    
    # API konfigurieren
    genai.configure(api_key=api_key)
    
    # Modell instanziieren
    model = genai.GenerativeModel('gemini-pro')
    
    # API-Anfrage senden
    response = model.generate_content("Erkläre mir kurz, was API-Keys sind.")
    
    return response.text

def use_groq_api(user_id):
    """Beispiel für die Nutzung des Groq API"""
    api_key = get_api_key_for_user(user_id, 'groq')
    
    if not api_key:
        return "API-Key konnte nicht abgerufen werden"
    
    # Client initialisieren
    client = Groq(api_key=api_key)
    
    # API-Anfrage senden
    response = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "user", "content": "Erkläre mir kurz, was API-Keys sind."}
        ]
    )
    
    return response.choices[0].message.content

# Beispiel für eine Funktion, die in einer View oder Task verwendet werden könnte
def generate_text_with_preferred_provider(user_id, prompt):
    """
    Nutzt den bevorzugten API-Provider des Nutzers, um Text zu generieren.
    Versucht zuerst Groq, dann Google Gemini.
    
    Args:
        user_id: ID des Nutzers
        prompt: Text-Prompt für die Generierung
        
    Returns:
        Generierter Text oder Fehlermeldung
    """
    # Zuerst Groq versuchen
    groq_api_key = get_api_key_for_user(user_id, 'groq')
    if groq_api_key:
        try:
            client = Groq(api_key=groq_api_key)
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Fehler bei Groq API-Anfrage: {str(e)}")
            # Fallback zu Google Gemini, wenn Groq fehlschlägt
    
    # Als Fallback Google Gemini verwenden
    gemini_api_key = get_api_key_for_user(user_id, 'google_gemini')
    if gemini_api_key:
        try:
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Fehler bei Google Gemini API-Anfrage: {str(e)}")
            return f"Fehler bei der Text-Generierung: {str(e)}"
    
    return "Keine gültigen API-Credentials für verfügbare Provider gefunden" 