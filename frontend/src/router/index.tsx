const SettingsPrompts = Loader(lazy(() => import('src/pages/SettingsPrompts')));
const SettingsAccounts = Loader(lazy(() => import('src/pages/SettingsAccounts')));

// New Log Protocol Page
const SettingsPromptsProtocol = Loader(lazy(() => import('src/pages/SettingsPromptsProtocol')));

const routes: RouteObject[] = [
  {
    path: '',
    element: <Navigate to="accounts" replace />
  },
  {
    path: 'accounts',
    element: <SettingsAccounts />
  },
  {
    path: 'prompts',
    element: <SettingsPrompts />
  },
  {
    path: 'prompts/protocol',
    element: <SettingsPromptsProtocol />
  }
]; 