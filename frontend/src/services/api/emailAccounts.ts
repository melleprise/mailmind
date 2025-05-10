/**
 * Versucht, IMAP/SMTP-Einstellungen basierend auf der E-Mail-Domain vorzuschlagen.
 * Verwendet den GET-Endpunkt /api/v1/email-accounts/suggest-settings/
 */
export const suggestSettings = async (email: string): Promise<any> => {
  console.debug(`[api.emailAccounts] Attempting to suggest settings for: ${email}`);
  try {
    const response = await apiClient.get<any>('/email-accounts/suggest-settings/', {
      method: 'get',
      params: { email }
    });
    console.info('[api.emailAccounts] Successfully received suggested settings (via GET).', response.data);
    return response.data;
  } catch (error) {
    console.error('[api.emailAccounts] Error suggesting settings:', error);
    throw error;
  }
}; 