import { useState, useEffect } from 'react'
import axios from "axios";

const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });

export function LoginPage() {


  // useEffect(()=>{

  //     })
    

  return (
    <>
      <h1>Welcome to the login page.</h1>
      <p>Login below to get access to the rest of the site.</p>
    </>
  )
}

export default LoginPage