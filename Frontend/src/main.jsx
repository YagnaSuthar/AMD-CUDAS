import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import './style/animation.css'
import './style/layout.css'
import './style/auth.css'
import './style/dashboard.css'
import './style/landing.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
