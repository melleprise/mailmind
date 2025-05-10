FROM mcr.microsoft.com/playwright:v1.44.0-jammy
# Wir verwenden v1.44.0, da wir wissen, dass dieser Tag existiert.
# Wenn v1.51.0 benötigt wird, müssen wir die Playwright-Version in crawl4ai prüfen
# und ggf. eine neuere Basis oder ein Downgrade von crawl4ai in Betracht ziehen.

# Systemabhängigkeiten (Python) installieren
USER root
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

# Arbeitsverzeichnis erstellen und Rechte setzen (pwuser ist Standard im Playwright-Image)
RUN mkdir -p /app && chown -R pwuser:pwuser /app
WORKDIR /app

# Konfiguration kopieren
COPY ./crawl4ai-config.yml /app/config.yml

# Minimales Server-Skript kopieren
COPY ./server.py /app/server.py

# Crawl4AI und Uvicorn systemweit installieren
RUN pip3 install --no-cache-dir crawl4ai uvicorn[standard]

# Wechsel zu pwuser
USER pwuser

# Port freigeben
EXPOSE 11235

# Standard-Command zum Starten des Servers
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "11235"] 