import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import './CSS/App.css'
import './CSS/BookCard.css'
import './CSS/DeveloperPage.css'
import './CSS/index.css'
import './CSS/NavBar.css'
import './CSS/UserCard.css'
import './CSS/UserPage.css'
import './CSS/BookPopUpPanel.css'
import './CSS/BooksPage.css'
import './CSS/FollowListPage.css'
import './CSS/LoginPage.css'
import './CSS/DownloadPage.css'

import {
  createBrowserRouter,
  RouterProvider,
} from "react-router-dom";
import NavBar from './components/NavBar.jsx'
import {UserContext, UserProvider} from './components/UserContext.jsx'

import App from './App.jsx'
import HomePage from './Pages/HomePage.jsx'
import LoginPage from './Pages/LoginPage.jsx'
import DownloadPage from './Pages/DownloadPage.jsx'
import UserPage from './Pages/UserPage.jsx'
import FollowListPage from './Pages/FollowListPage.jsx'
import DeveloperPage from './Pages/DeveloperPage.jsx'
import BooksPage from './Pages/BooksPage.jsx'
import OnlineReaderPage from './Pages/OnlineReaderPage.jsx'

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
  },
  {
    path: "/react/BooksPage/",
    element: <BooksPage />,
  },
  {
    path: "/react/NavBar/",
    element: <NavBar />,
  },
  {
    path: "/react/OnlineReaderPage/",
    element: <OnlineReaderPage />,
  },
]);

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <UserProvider>
    <RouterProvider router={router} />
    {/* <App /> */}
    </UserProvider>
  </StrictMode>,
)
