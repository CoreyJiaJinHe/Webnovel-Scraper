import { useState, useEffect,useRef } from 'react'
import { useNavigate } from 'react-router-dom';
import NavBar from '../components/NavBar'
import '../UserPage.css'

import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });



export function UserPage() {
  const [username, setUserName] = useState("");
  const [verifiedState, setVerifiedState] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const formRef = useRef(null);


  useEffect(()=>{tokenLogin()},[])

  const navigate = useNavigate();
  async function tokenLogin(){
    const response=await axios.post(`${API_URL}/token/`,{}, {withCredentials:true});
    console.log(response)
    if (response.status===200){
      setUserName(response.data.username);
      setVerifiedState(response.data.verifiedStatus);
    }
    else
    {
      navigate("/react/LoginPage/")
      console.log("Not logged in")
    }
  }
  
  useEffect(() => {
    function handleClickOutside(event) {
      if (formRef.current && !formRef.current.contains(event.target)) {
        setShowChangePassword(false);
      }
    }
    if (showChangePassword) {
      document.addEventListener("mousedown", handleClickOutside);
    } else {
      document.removeEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showChangePassword]);
  
  async function handleChangePasswordSubmit(e) {
      e.preventDefault();

      const form = e.target;
      const formData=new FormData(form)
      const password = formData.get("password");
      const newPassword=formData.get("newPassword");
      const confirmPassword = formData.get("confirmPassword");

      console.log(username)
      console.log(password)
      console.log(confirmPassword)

      if (username==="" || password===""){
        alert ("Please enter a password");
        return;
      }

      if (newPassword!==confirmPassword){
        alert ("Passwords do not match");
        return;
      }



      //TODO: FINISH THIS
      //I need to make the alert say certain responses. Like if you gave the wrong initial password
      //const response=await axios.post(`${API_URL}/changepassword/`, { username, password, newPassword:confirmPassword})
      //console.log(response)
      
      //alert (response.data);


      setShowChangePassword(false);
      alert("Password change submitted!");

  }

  return (
    <>
    <NavBar/>
      <div className="centered-container">
        <div className="user-container ">
            <h1>User: {username}</h1>
            <div className="user-container-content">
            <p>
              Verified: {verifiedState ? "Yes" : "No"}
            </p>
            {!verifiedState && (
              <p>
                Please wait until the Administrator verifies you. <br />
                You will be unable to use this website until you are verified.
              </p>
            )}
          </div>
          <button className="password-reset-button"
            onClick={() => setShowChangePassword(true)}
          >
            Change Password
          </button>

          {showChangePassword && (
            <div className="password-change-container">
              <div className="password-change-form-container" ref={formRef}>
                <h2 >Change Password</h2>
                <form onSubmit={handleChangePasswordSubmit}>
                  <p>Current Password</p>
                  <input type="password" name="password" placeholder="Current Password" required/>
                  <p>New Password</p>
                  <input type="password" name="newPassword" placeholder="New Password" required/>
                  <p>Confirm New Password</p>
                  <input type="password" name="confirmPassword" placeholder="Confirm New Password" required/>

                  <div className="two-button-container">
                    <button type="submit">
                      Submit
                    </button>
                    <button type="button" onClick={() => setShowChangePassword(false)}>
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}

        </div>
      </div>
    </>
  )
}

export default UserPage