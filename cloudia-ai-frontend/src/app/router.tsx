import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from './layout/AppShell'
import { ClientList } from '@/modules/clients/ClientList'
import { CreateClient } from '@/modules/clients/CreateClient'
import { ClientHub } from '@/modules/clients/ClientHub'
import { BrandDNAView } from '@/modules/brand-dna/BrandDNAView'
import { BrandDNASetup } from '@/modules/brand-dna/BrandDNASetup'
import { BrandDNAReviewPage } from '@/modules/brand-dna/BrandDNAReviewPage'
import { BrandDNAWizard } from '@/modules/brand-dna/wizard/BrandDNAWizard'
import { CampaignsModule } from '@/modules/campaigns/CampaignsModule'
import { AdsModule } from '@/modules/google-ads/AdsModule'
import { WebdevModule } from '@/modules/webdev/WebdevModule'

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<Navigate to="/clients" replace />} />
          <Route path="clients" element={<ClientList />} />
          <Route path="clients/new" element={<CreateClient />} />
          <Route path="clients/:clientId" element={<ClientHub />} />
          <Route path="clients/:clientId/brand-dna" element={<BrandDNAView />} />
          <Route path="clients/:clientId/brand-dna/setup" element={<BrandDNASetup />} />
          <Route path="clients/:clientId/brand-dna/review" element={<BrandDNAReviewPage />} />
          <Route path="clients/:clientId/brand-dna/wizard" element={<BrandDNAWizard />} />
          <Route path="clients/:clientId/campaigns/*" element={<CampaignsModule />} />
          <Route path="clients/:clientId/ads/*" element={<AdsModule />} />
          <Route path="clients/:clientId/webdev/*" element={<WebdevModule />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
