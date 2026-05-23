import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import 'vazir-font/dist/Without-Latin/font-face-WOL.css'
import './i18n'
import './index.css'
import App from './App.jsx'

const savedTheme = localStorage.getItem('theme') || 'light'
document.documentElement.setAttribute('data-theme', savedTheme)

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
