import { Settings as SettingsIcon } from 'lucide-react';

export default function Settings() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-gray-400">
      <SettingsIcon className="w-10 h-10 mb-4" />
      <p className="text-lg font-medium text-gray-600">Settings coming soon</p>
      <p className="text-sm mt-1">Configuration options will appear here</p>
    </div>
  );
}
