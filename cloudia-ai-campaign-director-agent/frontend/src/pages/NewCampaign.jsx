import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ChevronRight, ChevronLeft, Check, Loader } from 'lucide-react';
import { createCampaign } from '../api/campaigns';
import { api } from '../api/client';

const PLATFORMS = [
  { id: 'instagram', label: 'Instagram', emoji: '📸' },
  { id: 'facebook', label: 'Facebook', emoji: '👤' },
  { id: 'twitter', label: 'Twitter/X', emoji: '🐦' },
  { id: 'linkedin', label: 'LinkedIn', emoji: '💼' },
  { id: 'tiktok', label: 'TikTok', emoji: '🎵' },
  { id: 'youtube', label: 'YouTube', emoji: '▶' },
  { id: 'pinterest', label: 'Pinterest', emoji: '📌' },
];

const GOALS = [
  'Brand Awareness',
  'Lead Generation',
  'Community Engagement',
  'Product Launch',
  'Event Promotion',
  'Sales / Conversion',
  'Customer Retention',
];

const CONTENT_TYPES = [
  { id: 'image', label: 'Images' },
  { id: 'video', label: 'Videos' },
  { id: 'carousel', label: 'Carousels' },
  { id: 'reel', label: 'Reels / Shorts' },
  { id: 'story', label: 'Stories' },
  { id: 'text', label: 'Text Only' },
];

const STEPS = [
  'Client',
  'Goal',
  'Platforms',
  'Duration',
  'Content Mix',
  'Audience',
  'Hashtags',
  'Review',
];

function StepIndicator({ current, total }) {
  return (
    <div className="flex items-center gap-2">
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          className={`h-1.5 rounded-full flex-1 transition-all ${
            i < current ? 'bg-blue-600' : i === current ? 'bg-blue-400' : 'bg-gray-200'
          }`}
        />
      ))}
    </div>
  );
}

export default function NewCampaign() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [formError, setFormError] = useState('');

  const [form, setForm] = useState({
    client_id: '',
    client_name: '',
    new_client_name: '',
    create_new_client: false,
    name: '',
    goal: '',
    platforms: [],
    start_date: '',
    end_date: '',
    frequency_per_week: 3,
    content_types: [],
    target_audience: '',
    brief: '',
    hashtags: '',
    tone: '',
  });

  const { data: clientsData } = useQuery({
    queryKey: ['clients'],
    queryFn: () => api.get('/clients').then((r) => r.data),
    staleTime: 60000,
  });

  const clients = clientsData?.clients || clientsData || [];

  const mutation = useMutation({
    mutationFn: createCampaign,
    onSuccess: (data) => {
      const id = data?.id || data?.campaign_id;
      navigate(`/campaigns/${id}`);
    },
    onError: (err) => {
      setFormError(err?.response?.data?.detail || 'Failed to create campaign');
    },
  });

  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  const togglePlatform = (id) => {
    set('platforms', form.platforms.includes(id)
      ? form.platforms.filter((p) => p !== id)
      : [...form.platforms, id]);
  };

  const toggleContentType = (id) => {
    set('content_types', form.content_types.includes(id)
      ? form.content_types.filter((c) => c !== id)
      : [...form.content_types, id]);
  };

  const canNext = () => {
    if (step === 0) return form.create_new_client ? !!form.new_client_name.trim() : !!form.client_id;
    if (step === 1) return !!form.goal && !!form.name.trim();
    if (step === 2) return form.platforms.length > 0;
    if (step === 3) return !!form.start_date && !!form.end_date && form.frequency_per_week > 0;
    if (step === 4) return form.content_types.length > 0;
    if (step === 5) return !!form.brief.trim();
    return true;
  };

  const next = () => {
    setFormError('');
    if (!canNext()) { setFormError('Please complete this step before continuing.'); return; }
    setStep((s) => s + 1);
  };

  const back = () => { setFormError(''); setStep((s) => s - 1); };

  const submit = () => {
    setFormError('');
    const payload = {
      client_id: form.create_new_client ? null : form.client_id,
      client_name: form.create_new_client ? form.new_client_name : undefined,
      name: form.name,
      goal: form.goal,
      platforms: form.platforms,
      start_date: form.start_date,
      end_date: form.end_date,
      frequency_per_week: Number(form.frequency_per_week),
      content_types: form.content_types,
      target_audience: form.target_audience,
      brief: form.brief,
      hashtags: form.hashtags.split(/[\s,]+/).filter(Boolean).map((h) => h.replace(/^#/, '')),
      tone: form.tone,
    };
    mutation.mutate(payload);
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900">New Campaign</h1>
        <p className="text-sm text-gray-500 mt-0.5">Step {step + 1} of {STEPS.length}: {STEPS[step]}</p>
      </div>

      <StepIndicator current={step} total={STEPS.length} />

      <div className="bg-white border border-gray-200 rounded-xl p-6 mt-4">

        {step === 0 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-gray-800">Select Client</h2>

            <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700">
              <input
                type="checkbox"
                checked={form.create_new_client}
                onChange={(e) => set('create_new_client', e.target.checked)}
                className="rounded border-gray-300"
              />
              Create new client
            </label>

            {form.create_new_client ? (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">New Client Name</label>
                <input
                  type="text"
                  value={form.new_client_name}
                  onChange={(e) => set('new_client_name', e.target.value)}
                  placeholder="Client name"
                  className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            ) : (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Existing Client</label>
                {clients.length > 0 ? (
                  <select
                    value={form.client_id}
                    onChange={(e) => set('client_id', e.target.value)}
                    className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="">Select client...</option>
                    {clients.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                ) : (
                  <p className="text-sm text-gray-400">No clients yet. Check "Create new client" above.</p>
                )}
              </div>
            )}
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-gray-800">Campaign Goal & Name</h2>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Goal</label>
              <div className="grid grid-cols-2 gap-2">
                {GOALS.map((g) => (
                  <button
                    key={g}
                    onClick={() => set('goal', g)}
                    className={`text-left px-3 py-2 text-sm rounded border transition-all ${
                      form.goal === g
                        ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium'
                        : 'border-gray-200 text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    {g}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Campaign Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
                placeholder="e.g. Summer Launch 2025"
                className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-gray-800">Select Platforms</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {PLATFORMS.map((p) => (
                <button
                  key={p.id}
                  onClick={() => togglePlatform(p.id)}
                  className={`flex items-center gap-2 px-3 py-3 rounded-lg border text-sm font-medium transition-all ${
                    form.platforms.includes(p.id)
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <span className="text-xl">{p.emoji}</span>
                  {p.label}
                  {form.platforms.includes(p.id) && <Check className="w-4 h-4 ml-auto" />}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-gray-800">Duration & Frequency</h2>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Start Date</label>
                <input
                  type="date"
                  value={form.start_date}
                  onChange={(e) => set('start_date', e.target.value)}
                  className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">End Date</label>
                <input
                  type="date"
                  value={form.end_date}
                  onChange={(e) => set('end_date', e.target.value)}
                  min={form.start_date}
                  className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Posts per Week: {form.frequency_per_week}
              </label>
              <input
                type="range"
                min={1}
                max={21}
                value={form.frequency_per_week}
                onChange={(e) => set('frequency_per_week', e.target.value)}
                className="w-full accent-blue-600"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>1/week</span>
                <span>3/week</span>
                <span>21/week (3/day)</span>
              </div>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-gray-800">Content Mix</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {CONTENT_TYPES.map((ct) => (
                <button
                  key={ct.id}
                  onClick={() => toggleContentType(ct.id)}
                  className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border text-sm font-medium transition-all ${
                    form.content_types.includes(ct.id)
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {ct.label}
                  {form.content_types.includes(ct.id) && <Check className="w-4 h-4 ml-auto" />}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 5 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-gray-800">Target Audience & Brief</h2>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Target Audience</label>
              <input
                type="text"
                value={form.target_audience}
                onChange={(e) => set('target_audience', e.target.value)}
                placeholder="e.g. Women 25-40 interested in fitness"
                className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Campaign Brief</label>
              <textarea
                value={form.brief}
                onChange={(e) => set('brief', e.target.value)}
                rows={5}
                placeholder="Describe the campaign objectives, key messages, tone of voice, and any specific requirements..."
                className="w-full text-sm border border-gray-200 rounded px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Tone</label>
              <input
                type="text"
                value={form.tone}
                onChange={(e) => set('tone', e.target.value)}
                placeholder="e.g. Professional, Casual, Humorous, Inspirational"
                className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
        )}

        {step === 6 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-gray-800">Hashtags</h2>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Enter hashtags (space or comma separated)
              </label>
              <textarea
                value={form.hashtags}
                onChange={(e) => set('hashtags', e.target.value)}
                rows={4}
                placeholder="#brand #campaign #marketing"
                className="w-full text-sm border border-gray-200 rounded px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              {form.hashtags && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {form.hashtags
                    .split(/[\s,]+/)
                    .filter(Boolean)
                    .map((h, i) => (
                      <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                        {h.startsWith('#') ? h : `#${h}`}
                      </span>
                    ))}
                </div>
              )}
            </div>
          </div>
        )}

        {step === 7 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-gray-800">Review & Launch</h2>

            <div className="bg-gray-50 rounded-lg p-4 space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                <div>
                  <span className="text-xs text-gray-500 block">Client</span>
                  <span className="text-gray-800 font-medium">
                    {form.create_new_client ? form.new_client_name : (clients.find((c) => c.id === form.client_id)?.name || form.client_id)}
                  </span>
                </div>
                <div>
                  <span className="text-xs text-gray-500 block">Campaign Name</span>
                  <span className="text-gray-800 font-medium">{form.name}</span>
                </div>
                <div>
                  <span className="text-xs text-gray-500 block">Goal</span>
                  <span className="text-gray-800">{form.goal}</span>
                </div>
                <div>
                  <span className="text-xs text-gray-500 block">Duration</span>
                  <span className="text-gray-800">{form.start_date} → {form.end_date}</span>
                </div>
                <div>
                  <span className="text-xs text-gray-500 block">Frequency</span>
                  <span className="text-gray-800">{form.frequency_per_week} posts/week</span>
                </div>
                <div>
                  <span className="text-xs text-gray-500 block">Tone</span>
                  <span className="text-gray-800">{form.tone || 'Not specified'}</span>
                </div>
              </div>

              <div>
                <span className="text-xs text-gray-500 block mb-1">Platforms</span>
                <div className="flex flex-wrap gap-1">
                  {form.platforms.map((p) => (
                    <span key={p} className="px-2 py-0.5 bg-white border border-gray-200 rounded text-xs">{p}</span>
                  ))}
                </div>
              </div>

              <div>
                <span className="text-xs text-gray-500 block mb-1">Content Types</span>
                <div className="flex flex-wrap gap-1">
                  {form.content_types.map((c) => (
                    <span key={c} className="px-2 py-0.5 bg-white border border-gray-200 rounded text-xs">{c}</span>
                  ))}
                </div>
              </div>

              {form.target_audience && (
                <div>
                  <span className="text-xs text-gray-500 block">Target Audience</span>
                  <span className="text-gray-800">{form.target_audience}</span>
                </div>
              )}

              <div>
                <span className="text-xs text-gray-500 block">Brief</span>
                <p className="text-gray-800 text-sm mt-0.5">{form.brief}</p>
              </div>
            </div>

            {formError && (
              <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{formError}</p>
            )}
          </div>
        )}

        {formError && step < 7 && (
          <p className="text-sm text-red-600 mt-3">{formError}</p>
        )}
      </div>

      <div className="flex items-center justify-between mt-4">
        <button
          onClick={back}
          disabled={step === 0}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <ChevronLeft className="w-4 h-4" />
          Back
        </button>

        {step < STEPS.length - 1 ? (
          <button
            onClick={next}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Next
            <ChevronRight className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={submit}
            disabled={mutation.isPending}
            className="inline-flex items-center gap-1.5 px-6 py-2 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            {mutation.isPending ? <Loader className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
            {mutation.isPending ? 'Launching...' : 'Launch Campaign'}
          </button>
        )}
      </div>
    </div>
  );
}
