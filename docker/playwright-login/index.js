const express = require('express');
const { chromium } = require('playwright');
const fs = require('fs');
const app = express();
app.use(express.json());

// Login-Logik für freelance.de
async function loginFreelanceDe(username, password) {
  const browser = await chromium.launch({ headless: true, slowMo: 100 });
  const page = await browser.newPage();
  try {
    await page.goto('https://www.freelance.de/login.php');
    await page.waitForSelector('#username', { timeout: 15000 });
    await page.fill('#username', username);
    await page.fill('#password', password);
    await page.waitForTimeout(1000);
    const cookieBtn = await page.$('#CybotCookiebotDialogBodyButtonAccept');
    if (cookieBtn) {
      await cookieBtn.click();
      await page.waitForTimeout(500);
    }
    await page.evaluate(() => {
      const dialog = document.getElementById('CybotCookiebotDialog');
      if (dialog) dialog.remove();
    });
    await page.click('#login');
    await page.waitForLoadState('networkidle');
    const cookies = await page.context().cookies();
    return { success: true, cookies };
  } catch (e) {
    return { success: false, error: e.message };
  } finally {
    await browser.close();
  }
}

// Provider-Login-Dispatcher
const loginProviders = {
  'freelance.de': loginFreelanceDe,
  // Weitere Provider können hier ergänzt werden
};

// Generischer Login-Endpunkt
app.post('/login/:provider', async (req, res) => {
  const { provider } = req.params;
  const { username, password } = req.body;
  if (!loginProviders[provider]) {
    return res.status(400).json({ success: false, error: 'Unbekannter Provider' });
  }
  if (!username || !password) {
    return res.status(400).json({ success: false, error: 'Username und Passwort erforderlich' });
  }
  const result = await loginProviders[provider](username, password);
  if (result.success) {
    res.json(result);
  } else {
    res.status(500).json(result);
  }
});

app.listen(3000, () => console.log('Playwright Login Service listening on 3000')); 