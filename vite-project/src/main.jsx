import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import {
  createBrowserRouter,
  RouterProvider,
} from "react-router-dom";
import App from './App.jsx'
import {HomePage} from './Pages/HomePage'
import {LoginPage} from './Pages/LoginPage'
import DownloadPage from './Pages/DownloadPage'

const router = createBrowserRouter([
  {
    path: "/react/",
    element: <App />,
  },
  {
    path: "/react/Homepage/",
    element: <HomePage />,
  },
  {
    path: "/react/LoginPage/",
    element: <LoginPage />,
  },
  {
    path: "/react/DownloadPage/",
    element: <DownloadPage />,
  },
]);

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RouterProvider router={router} />
    {/* <App /> */}
  </StrictMode>,
)
