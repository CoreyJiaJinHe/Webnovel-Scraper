import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom';
import { useUser } from "../components/UserContext";
import NavBar from '../components/NavBar'

import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });



export function DeveloperPage() {
  
  const [username, setUserName]=useState("");
  const [verifiedState, setVerifiedState]=useState(false);
  const {isDeveloper,setIsDeveloper,isLoggedIn, setIsLoggedIn} = useUser();


  useEffect(()=>{tokenLogin()},[])


  const navigate = useNavigate();
  async function tokenLogin(){
    if (!isDeveloper && !isLoggedIn){
      navigate("/react/LoginPage/");
    }
    else
    {
      try{
        const response=await axios.post(`${API_URL}/token/`,{}, {withCredentials:true});
        console.log(response)
        if (response.status===200){
          setUserName(response.data.username);
          setVerifiedState(response.data.verified);
        }
        else
        {
          navigate("/react/LoginPage/")
          console.log("Not logged in")
        }
      }
      catch (error){
        if (error.response && error.response.status===401){
          console.log("Not logged in")
          navigate("/react/LoginPage/")
        }

        
      }
    }
}

  

  return (
    <>
    <NavBar/>
    </>
  )
}

export default DeveloperPage