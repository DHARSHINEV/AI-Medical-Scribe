import { ArrowRight, FileText } from 'lucide-react'
import { Link } from 'react-router-dom'
import { PageTitle, Panel } from '../components/layout/AppShell'
import { useConsultationStore } from '../context/ConsultationContext'
export default function HistoryPage(){const {consultations}=useConsultationStore();return <><PageTitle eyebrow="CONSULTATION LOG" title="History"><span className="status-pill"><i/> Synthetic demo workspace</span></PageTitle><Panel title="Recent consultations" label={`${consultations.length} records`}><div className="table-card">{consultations.map(c=><Link className="table-row" to={`/review/${c.id}`} key={c.id}><span><b>{c.patient.name}</b><small>{c.id} · {c.patient.complaint}</small></span><span className="badge">{c.approved?'Approved':c.status}</span><FileText size={16}/><ArrowRight size={16}/></Link>)}</div></Panel></>}
