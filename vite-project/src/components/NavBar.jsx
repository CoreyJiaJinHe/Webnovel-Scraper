import '../NavBar.css'
import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react'
import { useUser } from "./UserContext";


import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });


function Navbar(){
    const { isDeveloper, setIsDeveloper, isLoggedIn, setIsLoggedIn } = useUser();
    
    function logout(e){
        setIsLoggedIn(false);
        setIsDeveloper(false);
        localStorage.removeItem("loginTime");
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


                </ul>
            </navbar>
            <navbar className="navbar-right">
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
                        <button onClick={logout} className="logout-button">
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