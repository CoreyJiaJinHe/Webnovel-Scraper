// import { useState, useEffect } from 'react'
// import axios from "axios";
// const API_URL = "http://localhost:8000/api";
// const api = axios.create({ baseURL: API_URL });

import NavBar from '../components/NavBar'

export function HomePage() {
//   useEffect(()=>{

//       })
  return (
    <>
    <NavBar/>
    <div className="centered-container">
      <div className="main-content">
        <h1>
            Welcome to the HomePage.
        </h1>
      </div>
    </div>
    </>
  )
}

export default HomePage