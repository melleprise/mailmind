FROM mcr.microsoft.com/playwright:v1.52.0-jammy

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

RUN apt-get update && apt-get install -y \
    x11-apps \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libnss3 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libxss1 \
    libxshmfence1 \
    libxinerama1 \
    libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 3000
CMD ["node", "index.js"] 