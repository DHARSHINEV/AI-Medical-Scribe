import { Routes, Route, Outlet, Navigate, Link, useParams } from 'react-router-dom'
import { AppShell, PageTitle } from './components/layout/AppShell'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { useConsultationStore } from './context/ConsultationContext'
import { demoPatients } from './data/demoData'
import DashboardPage from './pages/DashboardPage'
import PatientsPage from './pages/PatientsPage'
import ConsultationPage from './pages/ConsultationPage'
import ReviewPage from './pages/ReviewPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import PrescriptionPage from './pages/PrescriptionPage'
import HistoryPage from './pages/HistoryPage'
function ProfilePage(){const {patientId}=useParams();const patient=demoPatients.find(p=>p.id===patientId)||demoPatients[0];return <><PageTitle eyebrow="PATIENT PROFILE · SYNTHETIC" title={patient.name}><Link className="btn primary" to={`/consultations/new?patient=${patient.id}`}>Start encounter</Link></PageTitle><div className="profile-grid"><div className="info-card"><b>Demographics</b><p>{patient.age} · {patient.sex} · {patient.mrn}</p><p>{patient.complaint}</p></div><div className="info-card"><b>Conditions & medications</b>{patient.conditions.map(x=><p key={x}>{x}</p>)}{patient.medications.map(x=><p key={x}>{x}</p>)}</div><div className="info-card warning"><b>Allergies</b>{patient.allergies.map(x=><p key={x}>{x}</p>)}</div></div></>}
function GenericPage({title,eyebrow}:{title:string;eyebrow:string}){return <><PageTitle eyebrow={eyebrow} title={title}><p className="muted">Available in the same synthetic demo workspace and FastAPI-ready service layer.</p></PageTitle></>}
function NewConsultationRoute(){const { createDemoConsultation } = useConsultationStore(); const patientId = new URLSearchParams(window.location.search).get('patient'); const patient = demoPatients.find(p => p.id === patientId) ?? demoPatients[0]; const id = createDemoConsultation(patient); return <Navigate to={`/consultations/${id}`} replace/>}
function ProtectedShell(){return <ProtectedRoute/>}
export default function App(){return <Routes><Route path="/login" element={<LoginPage/>}/><Route path="/register" element={<RegisterPage/>}/><Route element={<ProtectedShell/>}><Route element={<AppShell><Outlet/></AppShell>}><Route path="/" element={<DashboardPage/>}/><Route path="/patients" element={<PatientsPage/>}/><Route path="/patients/:patientId" element={<ProfilePage/>}/><Route path="/consultations/new" element={<NewConsultationRoute/>}/><Route path="/consultations/:id" element={<ConsultationPage/>}/><Route path="/review/:id" element={<ReviewPage/>}/><Route path="/prescription/:id" element={<PrescriptionPage/>}/><Route path="/history" element={<HistoryPage/>}/><Route path="/labs" element={<GenericPage eyebrow="SECONDARY WORKSPACE" title="Lab reports"/>}/><Route path="/settings" element={<GenericPage eyebrow="WORKSPACE CONFIGURATION" title="Settings"/>}/><Route path="/research" element={<GenericPage eyebrow="ADVANCED / RESEARCH" title="AI training & research"/>}/></Route></Route><Route path="*" element={<Navigate to="/" replace/>}/></Routes>}
