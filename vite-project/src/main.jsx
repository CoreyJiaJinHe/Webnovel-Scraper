import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import {
  createBrowserRouter,
  RouterProvider,
} from "react-router-dom";
import App from './App.jsx'
import HomePage from './Pages/HomePage'
import LoginPage from './Pages/LoginPage'
import DownloadPage from './Pages/DownloadPage'
import UserPage from './Pages/UserPage'
import FollowListPage from './Pages/FollowListPage'
import DeveloperPage from './Pages/DeveloperPage'
import NavBar from './components/NavBar.jsx'
import {UserContext, UserProvider} from './components/UserContext.jsx'

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
    path: "/react/UserPage/",
    element: <UserPage />,
  },
  {
    path: "/react/DownloadPage/",
    element: <DownloadPage />,
  },
  {
    path: "/react/FollowListPage/",
    element: <FollowListPage />,
  },
  {
    path: "/react/DeveloperPage/",
    element: <DeveloperPage />,
  }
,
  {
    path: "/react/NavBar/",
    element: <NavBar />,
  }
]);

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <UserProvider>
    <RouterProvider router={router} />
    {/* <App /> */}
    </UserProvider>
  </StrictMode>,
)
