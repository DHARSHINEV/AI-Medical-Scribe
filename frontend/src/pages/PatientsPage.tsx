import { ChevronRight, Stethoscope } from 'lucide-react'
import { Link } from 'react-router-dom'
import { PageTitle } from '../components/layout/AppShell'
import { demoPatients } from '../data/demoData'
export default function PatientsPage(){return <><PageTitle eyebrow="PATIENT DIRECTORY" title="Patients"><Link className="btn primary" to="/consultations/new"><Stethoscope size={16}/> New consultation</Link></PageTitle><p className="muted">Demo records are synthetic and isolated from live clinical data.</p><div className="patient-grid">{demoPatients.map(p=><Link to={`/patients/${p.id}`} className="patient-card" key={p.id}><div className="patient-top"><span className="patient-avatar">{p.name.split(' ').map(n=>n[0]).join('')}</span><ChevronRight size={16}/></div><h3>{p.name}</h3><span className="muted">{p.age} · {p.sex} · {p.mrn}</span><p>{p.complaint}</p><div className="tag-row">{p.conditions.map(c=><span className="tag" key={c}>{c}</span>)}</div></Link>)}</div></>}
