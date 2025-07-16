import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom';
import NavBar from '../components/NavBar'
import { useUser } from "../components/UserContext";


// import axios from "axios";
// const API_URL = `${import.meta.env.BACKEND_LOCAL_HOST}/api`;
// const api = axios.create({ baseURL: API_URL });

import axios from "axios";

const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });

export function LoginPage() {
  const [showAccountCreation, setShowAccountCreation] = useState(false);
  const [username, setUserName]=useState("");
  const [password, setPassword]=useState("");
  const [confirmPassword, setConfirmPassword]=useState("");
  const {isDeveloper,setIsDeveloper,isLoggedIn, setIsLoggedIn, recentAttempt, setRecentAttempt} = useUser();
  const [redirectCountdown, setRedirectCountdown] = useState(2);
  

  useEffect(() => {
      if (!isLoggedIn) {
          if (!document.cookie.includes("recentAttempt=true")) {
              // Cookie not present, attempt backend call
              tokenLogin();
              document.cookie = "recentAttempt=true; path=/";
              setRecentAttempt(true);
          }
      }
  }, []);

  const navigate = useNavigate();
  
  async function tokenLogin(){
    if (!isLoggedIn){
        try{
            const response=await axios.post(`${API_URL}/token/`,{}, {withCredentials:true});
            console.log(response)
            if (response.status===200){
              navigate("/react/HomePage/");
              console.log(response.data.isDeveloper);
              setIsDeveloper(response.data.isDeveloper);
              setIsLoggedIn(true);
              setUserName(response.data.username);
              setVerifiedState(response.data.verifiedStatus);
            }
            else
            {
              console.log("Not logged in")
              setIsDeveloper(False);
            }
          }
        catch (error){
            setIsLoggedIn(false);
            setIsDeveloper(false);
        }
      }
    else{
      navigate("/react/HomePage/");
    }
  }

  useEffect(() => {
    let timer;
    if (isLoggedIn) {
      setRedirectCountdown(2); // reset countdown
      timer = setInterval(() => {
        setRedirectCountdown((prev) => prev - 1);
      }, 1000);
      const navTimeout = setTimeout(() => {
        navigate("/react/HomePage/");
      }, 2000);
      return () => {
        clearInterval(timer);
        clearTimeout(navTimeout);
      };
    }
  }, [isLoggedIn, navigate]);

  async function handleLoginSubmit(e){
    e.preventDefault();

    const form = e.target;
    const formData=new FormData(form)
    const username = formData.get("username");
    const password = formData.get("password");
    setUserName(formData.get("username"));
    setPassword(formData.get("password"));

    console.log(username)
    console.log(password)

    if (username==="" || password===""){
      alert ("Please enter a username and password");
      return;
    }
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    console.log("Submitting login with params:", params.toString());
    console.log("API URL:", `${API_URL}/login/`);

    try {
        const response=await axios.post(`${API_URL}/login/`, params, {
        withCredentials: true,
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        });
        console.log("Login response status:", response.status);

        if (response.status===200){
          alert("Logged in successfully");
          localStorage.setItem("loginTime", Date.now().toString()); // Optional: for 1-day timeout
          console.log(response.data.isDeveloper);
          
          setIsDeveloper(response.data.isDeveloper);
          setIsLoggedIn(true);
          setUserName(response.data.username);
          setVerifiedState(response.data.verifiedStatus);
        }
      } catch (error) {
        if (error.response && error.response.status === 401) {
          alert ("Invalid username or password. Please try again.");
        }
      }
    
    //alert (response.data);
  }
    
  async function handleAccountCreation(e){
    e.preventDefault();


    const form = e.target;
    const formData=new FormData(form)
    const username = formData.get("username");
    const password = formData.get("password");
    const confirmPassword = formData.get("confirmPassWord");
    setUserName(formData.get("username"));
    setPassword(formData.get("password"));
    setConfirmPassword(formData.get("confirmPassWord"));

    console.log(username)
    console.log(password)
    console.log(confirmPassword)

    if (username==="" || password===""){
      alert ("Please enter a username and password");
      return;
    }

    if (password!==confirmPassword){
      alert ("Passwords do not match");
      return;
    }
    const response=await axios.post(`${API_URL}/register/`, { username, password })
    console.log(response)
    
    alert ("Your account has been created. You can now log in. Please give it a few days for your account to be verified.");



  }

  return (
  <>
    <NavBar/>
    <div className="centered-container">
      <div className="login-content">
        {!isLoggedIn ? (
          showAccountCreation ? (
            <>
              <h1>Create Account</h1>
              <p>Fill out the form to create a new account.</p>
              <form className="login-form" onSubmit={handleAccountCreation}>
                <p>Username</p>
                <label>
                  <input name="username"/>
                </label>
                <p>Password</p>
                <input type="password" name="password"/>
                <p>Confirm Password</p>
                <input name="confirmPassWord" type="password"/>
                <button className="block mt-6 mx-auto" type="submit">Create Account</button>
              </form>
              <button type="button" onClick={() => setShowAccountCreation(false)}>
                Back to Login
              </button>
            </>
          ) : (
            <>
              <h1>Welcome.</h1>
              <p>Login below to get access to the rest of the site.</p>
              <form className="login-form" onSubmit={handleLoginSubmit}>
                <p>Username</p>
                <label>
                  <input name="username"/>
                </label>
                <p>Password</p>
                <input type="password" name="password"/>
                <button className="block mt-6 mx-auto" type="submit">Login</button>
              </form>
              <p>Don't have an account?</p>
              <button type="button" onClick={() => setShowAccountCreation(true)}>
                Create Account
              </button>
            </>
          )
        ) : (
          <div className="login-success-message">
            <h2>Login successful!</h2>
            <br></br>
            <p>You are now logged in as {username}</p>
            <br></br>
            <p>Redirecting in {redirectCountdown} second{redirectCountdown !== 1 ? "s" : ""}...</p>

          </div>
        )}
      </div>
    </div>
  </>
)
}

export default LoginPage