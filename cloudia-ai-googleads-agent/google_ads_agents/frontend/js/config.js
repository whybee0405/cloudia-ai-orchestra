// API is served from the same origin as the frontend
export const API_BASE = '';

// Workforce registry — add a new entry here to register a new agent workforce.
// The frontend automatically builds sidebar nav and routes from this config.
export const WORKFORCES = [
  {
    id: 'google-ads',
    name: 'Google Ads',
    color: '#4285F4',
    description: 'Campaign management, bid optimisation, keyword scouting',
    agents: ['auditor', 'manager', 'reporter', 'keyword_scout', 'creator'],
    nav: [
      { id: 'queue',   label: 'Approval Queue',  icon: 'queue'   },
      { id: 'audit',   label: 'Audit Log',        icon: 'audit'   },
      { id: 'runs',    label: 'Agent Runs',        icon: 'runs'    },
      { id: 'creator', label: 'Campaign Creator',  icon: 'creator' },
    ],
  },
  // Future workforce example (disabled):
  // { id: 'seo', name: 'SEO Agents', color: '#10b981', disabled: true, description: 'Search engine optimisation automation', agents: [], nav: [] },
];

export const GLOBAL_NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
  { id: 'accounts',  label: 'Accounts',  icon: 'accounts'  },
];
