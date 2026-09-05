import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
export function ProtectedRoute() { const { isAuthenticated, isLoading } = useAuth(); const location = useLocation(); if (isLoading) return <div className="auth-loading">Checking secure session…</div>; return isAuthenticated ? <Outlet /> : <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace /> }
