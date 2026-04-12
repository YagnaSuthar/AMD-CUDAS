import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import './style/animation.css'
import './style/layout.css'
import './style/auth.css'
import './style/dashboard.css'
<<<<<<< HEAD
=======
import './style/notifications.css'
import './style/popup.css'
>>>>>>> b4aa5c97cf73d81492c95d8849bf44ceb641727a
import './style/landing.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
