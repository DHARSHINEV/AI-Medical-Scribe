import { Routes, Route, Outlet, Navigate } from 'react-router-dom'
import { AppShell, PageTitle } from './components/layout/AppShell'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import DashboardPage from './pages/DashboardPage'
import PatientsPage from './pages/PatientsPage'
import ProfilePage from './pages/ProfilePage'
import NewConsultationPage from './pages/NewConsultationPage'
import ConsultationPage from './pages/ConsultationPage'
import ReviewPage from './pages/ReviewPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import PrescriptionPage from './pages/PrescriptionPage'
import HistoryPage from './pages/HistoryPage'
import LabsPage from './pages/LabsPage'

function GenericPage({ title, eyebrow }: { title: string; eyebrow: string }) {
  return (
    <PageTitle eyebrow={eyebrow} title={title}>
      <p className="muted">Available in the MediScribe clinical documentation workspace.</p>
    </PageTitle>
  )
}

function ProtectedShell() {
  return <ProtectedRoute />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedShell />}>
        <Route element={<AppShell><Outlet /></AppShell>}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/patients" element={<PatientsPage />} />
          <Route path="/patients/:patientId" element={<ProfilePage />} />
          <Route path="/consultations/new" element={<NewConsultationPage />} />
          <Route path="/consultations/:id" element={<ConsultationPage />} />
          <Route path="/review/:id" element={<ReviewPage />} />
          <Route path="/prescription/:id" element={<PrescriptionPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/labs" element={<LabsPage />} />
          <Route path="/settings" element={<GenericPage eyebrow="WORKSPACE CONFIGURATION" title="Settings" />} />
          <Route path="/research" element={<GenericPage eyebrow="ADVANCED / RESEARCH" title="AI training & research" />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
