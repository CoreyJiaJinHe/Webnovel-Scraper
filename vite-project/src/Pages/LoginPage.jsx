import { useState, useEffect } from 'react'
import NavBar from '../components/NavBar'


import axios from "axios";

const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });

export function LoginPage() {
  const [showAccountCreation, setShowAccountCreation] = useState(false);


  function handleSubmit(e){
    e.preventDefault();

    const form=e.target;
    const formData=new FormData(form)
  }
    
  function handleAccountCreation(e){
  
  
  
  }
  return (
    <>
    <NavBar/>
      <div className="centered-container">
        {showAccountCreation ? (
          <div className="login-content">
            <h1>Create Account</h1>
            <p>Fill out the form to create a new account.</p>
            <form className="login-form" method="post" onSubmit={handleAccountCreation}>
              <p>Username</p>
              <label>
                <input name="userName"/>
              </label>
              <p>Password</p>
              <input name="passWord"/>
              <p>Confirm Password</p>
              <input name="confirmPassWord"/>
              <button type="submit">Create Account</button>
              <button type="button" onClick={() => setShowAccountCreation(false)}>
                Back to Login
              </button>
            </form>
          </div>
        ) : (
          <div className="login-content">
            <h1>Welcome.</h1>
            <p>Login below to get access to the rest of the site.</p>
            <form className="login-form" method="post" onSubmit={handleSubmit}>
              <p>Username</p>
              <label>
                <input name="userName"/>
              </label>
              <p>Password</p>
              <input name="passWord"/>
              <button type="submit">Login</button>
              <p>Don't have an account?</p>
              <button type="button" onClick={() => setShowAccountCreation(true)}>
                Create Account
              </button>
            </form>
          </div>
        )}
      </div>
    </>
  )
}

export default LoginPage