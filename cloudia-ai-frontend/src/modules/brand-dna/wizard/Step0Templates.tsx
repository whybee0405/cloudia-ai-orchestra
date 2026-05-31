import { cn } from '@/lib/utils'
import { Button } from '@/shared/components/Button'
import type { WizardData } from './BrandDNAWizard'

interface Template {
  industry: string
  label: string
  icon: string
  description: string
  defaults: Partial<WizardData>
}

const TEMPLATES: Template[] = [
  {
    industry: 'restaurant',
    label: 'Restaurant & Food',
    icon: '🍽️',
    description: 'Cafés, fine dining, fast casual, food trucks',
    defaults: {
      industry: 'restaurant',
      tone: 'warm',
      language_style: 'Inviting and sensory-driven, celebrating flavour and experience. Short, evocative sentences that make the reader hungry.',
      personality_traits: ['Passionate', 'Welcoming', 'Authentic'],
      visual_style: 'warm',
      primary_color: '#c2410c',
      accent_color: '#fbbf24',
      heading_font: 'Playfair Display',
      body_font: 'Lora',
    },
  },
  {
    industry: 'retail',
    label: 'Retail',
    icon: '🛍️',
    description: 'Fashion, homewares, lifestyle stores',
    defaults: {
      industry: 'retail',
      tone: 'casual',
      language_style: 'Friendly, trend-forward, and direct. Uses active voice and speaks to the customer\'s lifestyle aspirations.',
      personality_traits: ['Stylish', 'Accessible', 'Current'],
      visual_style: 'bold',
      primary_color: '#1d4ed8',
      accent_color: '#f59e0b',
      heading_font: 'Montserrat',
      body_font: 'Inter',
    },
  },
  {
    industry: 'professional_services',
    label: 'Professional Services',
    icon: '💼',
    description: 'Law, accounting, consulting, finance',
    defaults: {
      industry: 'professional_services',
      tone: 'formal',
      language_style: 'Clear, precise, and jargon-minimal. Projects deep expertise and reliability without being distant.',
      personality_traits: ['Expert', 'Reliable', 'Trustworthy'],
      visual_style: 'corporate',
      primary_color: '#1e3a5f',
      accent_color: '#0ea5e9',
      heading_font: 'Raleway',
      body_font: 'Inter',
    },
  },
  {
    industry: 'health_wellness',
    label: 'Health & Wellness',
    icon: '🌿',
    description: 'Gyms, clinics, wellness studios, nutrition',
    defaults: {
      industry: 'health_wellness',
      tone: 'warm',
      language_style: 'Empathetic, supportive, and holistic. Avoids over-medicalised language; speaks to the whole person.',
      personality_traits: ['Caring', 'Holistic', 'Empowering'],
      visual_style: 'minimalist',
      primary_color: '#065f46',
      accent_color: '#34d399',
      heading_font: 'DM Sans',
      body_font: 'Inter',
    },
  },
  {
    industry: 'real_estate',
    label: 'Real Estate',
    icon: '🏠',
    description: 'Residential, commercial, property investment',
    defaults: {
      industry: 'real_estate',
      tone: 'authoritative',
      language_style: 'Confident and aspirational, grounded in local market knowledge. Paints a picture of possibility.',
      personality_traits: ['Knowledgeable', 'Trusted', 'Aspirational'],
      visual_style: 'luxury',
      primary_color: '#1c1917',
      accent_color: '#d97706',
      heading_font: 'Playfair Display',
      body_font: 'Raleway',
    },
  },
  {
    industry: 'education',
    label: 'Education',
    icon: '📚',
    description: 'Schools, tutoring, online courses, training',
    defaults: {
      industry: 'education',
      tone: 'warm',
      language_style: 'Encouraging, clear, and inclusive. Empowers learners at every level with a forward-looking, growth mindset voice.',
      personality_traits: ['Inspiring', 'Supportive', 'Progressive'],
      visual_style: 'playful',
      primary_color: '#1d4ed8',
      accent_color: '#f59e0b',
      heading_font: 'Nunito',
      body_font: 'Poppins',
    },
  },
  {
    industry: 'ecommerce',
    label: 'E-Commerce',
    icon: '🛒',
    description: 'Online stores, DTC brands, marketplaces',
    defaults: {
      industry: 'ecommerce',
      tone: 'casual',
      language_style: 'Conversational, benefit-focused, with a dash of urgency. Gets to the point fast and earns the click.',
      personality_traits: ['Convenient', 'Reliable', 'Value-driven'],
      visual_style: 'bold',
      primary_color: '#7c3aed',
      accent_color: '#f97316',
      heading_font: 'Poppins',
      body_font: 'Inter',
    },
  },
  {
    industry: 'hospitality_tourism',
    label: 'Hospitality & Tourism',
    icon: '✈️',
    description: 'Hotels, tours, travel agencies, experiences',
    defaults: {
      industry: 'hospitality_tourism',
      tone: 'warm',
      language_style: 'Evocative and experience-first. Paints vivid destination pictures and makes the reader feel they are already there.',
      personality_traits: ['Adventurous', 'Welcoming', 'Memorable'],
      visual_style: 'editorial',
      primary_color: '#0369a1',
      accent_color: '#fbbf24',
      heading_font: 'Montserrat',
      body_font: 'Lora',
    },
  },
  {
    industry: 'automotive',
    label: 'Automotive',
    icon: '🚗',
    description: 'Dealerships, workshops, automotive services',
    defaults: {
      industry: 'automotive',
      tone: 'authoritative',
      language_style: 'Performance-driven and bold. Technical precision balanced with genuine excitement for the machine.',
      personality_traits: ['Powerful', 'Innovative', 'Precise'],
      visual_style: 'dark-tech',
      primary_color: '#111827',
      accent_color: '#ef4444',
      heading_font: 'Raleway',
      body_font: 'Inter',
    },
  },
  {
    industry: 'beauty_personal_care',
    label: 'Beauty & Personal Care',
    icon: '💄',
    description: 'Salons, skincare, cosmetics, wellness brands',
    defaults: {
      industry: 'beauty_personal_care',
      tone: 'casual',
      language_style: 'Aspirational yet inclusive. Celebrates individuality and self-care rituals with a warm, confident voice.',
      personality_traits: ['Empowering', 'Luxurious', 'Inclusive'],
      visual_style: 'luxury',
      primary_color: '#831843',
      accent_color: '#f9a8d4',
      heading_font: 'Playfair Display',
      body_font: 'Poppins',
    },
  },
]

interface Props {
  onSelect: (defaults: Partial<WizardData>) => void
  onSkip: () => void
}

export function Step0Templates({ onSelect, onSkip }: Props) {
  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-3xl mx-auto">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">Start with an industry template</h1>
          <p className="text-slate-500 text-sm">
            Pick the template that best matches your business. We'll pre-fill sensible defaults that you can customise in the next steps.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {TEMPLATES.map(t => (
            <button
              key={t.industry}
              type="button"
              onClick={() => onSelect(t.defaults)}
              className={cn(
                'group flex flex-col items-start gap-1.5 rounded-2xl border-2 border-slate-200 bg-white p-4 text-left transition-all',
                'hover:border-brand-400 hover:shadow-md hover:-translate-y-0.5',
              )}
            >
              <span className="text-3xl">{t.icon}</span>
              <p className="text-sm font-semibold text-slate-800 group-hover:text-brand-700">{t.label}</p>
              <p className="text-xs text-slate-400 leading-snug">{t.description}</p>
            </button>
          ))}
        </div>

        <div className="mt-6 flex justify-center">
          <Button variant="secondary" onClick={onSkip}>Start from scratch →</Button>
        </div>
      </div>
    </div>
  )
}
