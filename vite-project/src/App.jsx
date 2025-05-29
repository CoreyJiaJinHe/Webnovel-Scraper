//import './App.css'
import {useEffect } from 'react'
import {useNavigate} from 'react-router-dom'

function App() {
  const navigate = useNavigate();
  
  useEffect(() => {
    navigate('/react/HomePage', { replace: true });
  }, [navigate]);

  return (
    <>
    <h1>You are somewhere you shouldn't be.</h1>
    </>
  )

  
}

export default App
