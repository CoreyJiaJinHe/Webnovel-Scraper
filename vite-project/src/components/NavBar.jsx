//import '../NavBar.css'
import {Link, useNavigate } from 'react-router-dom';
import { useUser } from "./UserContext";
import { useState, useEffect } from 'react'

import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });


function Navbar(){
    const { 
        isLoggedIn, setIsLoggedIn,
        username, setUserName,
        verifiedState, setVerifiedState,
        logout,
        isDeveloper, setIsDeveloper} = useUser();

    const navigate = useNavigate();

    async function handleLogout(e) {
        await logout();
        navigate("/react/LoginPage");
    }

    useEffect(() => {
        if (!isLoggedIn) {
          tokenLogin();
      }
    }, []);

    async function tokenLogin(){
    if (!isLoggedIn){
        try{
        const response=await axios.post(`${API_URL}/token/`,{}, {withCredentials:true});
        //console.log(response)
        if (response.status===200){
            setUserName(response.data.username);
            setVerifiedState(response.data.verified);
            setIsLoggedIn(true);
            setIsDeveloper(response.data.isDeveloper);
        }
        else
        {
            setIsLoggedIn(false);
            console.log("Not logged in")
        }
      }
      catch (error){
        if (error.response && error.response.status===401){
            console.log("Not logged in")
        }
      }
    }
    else
    {
        console.log("Not logged in")
    }
  }

    return(
        <>
        <nav>
            <navbar className="navbar-center">
                <ul className="nav-links">
                    <li>
                        
                        <Link to="/react/HomePage">Home Page</Link>
                    </li>
                    <li>
                        <Link to="/react/DownloadPage">Downloads</Link>
                    </li>
                    <li>
                        <Link to="/react/BooksPage">Books</Link>
                    </li>
                    <li>
                        <Link to="/react/BookScraperPage">Online Api</Link>
                    </li>

                </ul>
            </navbar>
            <navbar className="navbar-right">
                {isDeveloper && (
                    <li>
                        <Link to="/react/DeveloperBookEditPage">Edit Book Data</Link>
                    </li>
                )}
                {isDeveloper && (
                    <li>
                        <Link to="/react/DeveloperPage">Developer</Link>
                    </li>
                )}
                <li>
                    <Link to="/react/FollowListPage">Follow Lists</Link>
                </li>
                <li>
                    <Link to="/react/UserPage">User</Link>
                </li>
                {isLoggedIn ? (
                        <button onClick={handleLogout} className="logout-button">
                            Logout
                        </button>
                    ) : (
                        <Link to="/react/LoginPage">Login</Link>
                    )}
            </navbar>


        </nav>        
        </>
    )


}
export default Navbar