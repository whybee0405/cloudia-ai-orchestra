import { useState } from 'react';
import { Plus, X, Upload } from 'lucide-react';

export default function BrandGuidelinesEditor({ initialData = {}, onChange }) {
  const [data, setData] = useState({
    primary_color: initialData.primary_color || '#3b5bdb',
    secondary_color: initialData.secondary_color || '#ffffff',
    accent_color: initialData.accent_color || '#f59e0b',
    primary_font: initialData.primary_font || '',
    secondary_font: initialData.secondary_font || '',
    tone_keywords: initialData.tone_keywords || [],
    forbidden_words: initialData.forbidden_words || [],
    required_elements: initialData.required_elements || {
      logo: false,
      hashtag: false,
      website: false,
      cta: false,
    },
    logo_url: initialData.logo_url || '',
    brand_voice: initialData.brand_voice || '',
  });

  const [newTone, setNewTone] = useState('');
  const [newForbidden, setNewForbidden] = useState('');

  const update = (key, value) => {
    const next = { ...data, [key]: value };
    setData(next);
    onChange && onChange(next);
  };

  const addTone = () => {
    if (!newTone.trim()) return;
    update('tone_keywords', [...data.tone_keywords, newTone.trim()]);
    setNewTone('');
  };

  const removeTone = (idx) =>
    update('tone_keywords', data.tone_keywords.filter((_, i) => i !== idx));

  const addForbidden = () => {
    if (!newForbidden.trim()) return;
    update('forbidden_words', [...data.forbidden_words, newForbidden.trim()]);
    setNewForbidden('');
  };

  const removeForbidden = (idx) =>
    update('forbidden_words', data.forbidden_words.filter((_, i) => i !== idx));

  const toggleRequired = (key) =>
    update('required_elements', { ...data.required_elements, [key]: !data.required_elements[key] });

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { key: 'primary_color', label: 'Primary Colour' },
          { key: 'secondary_color', label: 'Secondary Colour' },
          { key: 'accent_color', label: 'Accent Colour' },
        ].map(({ key, label }) => (
          <div key={key}>
            <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
            <div className="flex items-center gap-2">
              <input
                type="color"
                value={data[key]}
                onChange={(e) => update(key, e.target.value)}
                className="h-9 w-12 rounded border border-gray-200 cursor-pointer p-0.5"
              />
              <input
                type="text"
                value={data[key]}
                onChange={(e) => update(key, e.target.value)}
                className="flex-1 text-sm border border-gray-200 rounded px-3 py-2 font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[
          { key: 'primary_font', label: 'Primary Font' },
          { key: 'secondary_font', label: 'Secondary Font' },
        ].map(({ key, label }) => (
          <div key={key}>
            <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
            <input
              type="text"
              value={data[key]}
              onChange={(e) => update(key, e.target.value)}
              placeholder="e.g. Inter, Helvetica Neue"
              className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        ))}
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Brand Voice</label>
        <textarea
          value={data.brand_voice}
          onChange={(e) => update('brand_voice', e.target.value)}
          rows={3}
          placeholder="Describe the brand's tone and personality..."
          className="w-full text-sm border border-gray-200 rounded px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-2">Tone Keywords</label>
        <div className="flex flex-wrap gap-1.5 mb-2">
          {data.tone_keywords.map((kw, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium"
            >
              {kw}
              <button onClick={() => removeTone(idx)} className="hover:text-blue-900">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={newTone}
            onChange={(e) => setNewTone(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTone())}
            placeholder="Add keyword..."
            className="flex-1 text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={addTone}
            className="px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-2">Forbidden Words</label>
        <div className="flex flex-wrap gap-1.5 mb-2">
          {data.forbidden_words.map((w, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1 px-2.5 py-1 bg-red-50 text-red-700 rounded-full text-xs font-medium"
            >
              {w}
              <button onClick={() => removeForbidden(idx)} className="hover:text-red-900">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={newForbidden}
            onChange={(e) => setNewForbidden(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addForbidden())}
            placeholder="Add forbidden word..."
            className="flex-1 text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={addForbidden}
            className="px-3 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-2">Required Elements</label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {Object.keys(data.required_elements).map((key) => (
            <label key={key} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={!!data.required_elements[key]}
                onChange={() => toggleRequired(key)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 capitalize">{key}</span>
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Logo URL</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={data.logo_url}
            onChange={(e) => update('logo_url', e.target.value)}
            placeholder="https://..."
            className="flex-1 text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button className="inline-flex items-center gap-1.5 px-3 py-2 text-sm border border-gray-300 text-gray-700 rounded hover:bg-gray-50">
            <Upload className="w-4 h-4" />
            Upload
          </button>
        </div>
        {data.logo_url && (
          <img
            src={data.logo_url}
            alt="Logo preview"
            className="mt-2 h-12 object-contain"
            onError={(e) => (e.target.style.display = 'none')}
          />
        )}
      </div>
    </div>
  );
}
