import { createContext, useContext, useState,useEffect } from "react";
export const UserContext = createContext();

import axios from "axios";

const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });

export function UserProvider({ children }) {
    const [isDeveloper, setIsDeveloper] = useState(false);
    const [isLoggedIn, setIsLoggedIn]=useState(false);
    const [username, setUsername] = useState("");
    const [verifiedState, setVerifiedState] = useState(false);


    useEffect(() => {
        const loginTime = localStorage.getItem("loginTime");
        if (loginTime) {
            const now = Date.now();
            const oneDay = 24 * 60 * 60 * 1000;
            if (now - parseInt(loginTime, 10) < oneDay) {
                setIsLoggedIn(true);
            } else {
                setIsLoggedIn(false);
                setIsDeveloper(false);
                localStorage.removeItem("loginTime");
            }
        } else {
            setIsLoggedIn(false);
            setIsDeveloper(false);
        }
    }, []);
    
    async function logout() {
        setIsLoggedIn(false);
        setIsDeveloper(false);
        localStorage.removeItem("loginTime");
        localStorage.removeItem("access_token"); // If you store it here

        // Remove access_token cookie for all common cases
        document.cookie = "access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        document.cookie = "access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=" + window.location.hostname + ";";
        document.cookie = "access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC;";

        if (document.cookie.split(';').some(cookie => cookie.trim().startsWith('access_token='))){
            try{
                const response=await axios.post(`${API_URL}/logout/`,{},{withCredentials:true});
                console.log("Logout response:",response);
            }
            catch (error){
            }


        }


    }

    return (
        <UserContext.Provider value={{ 
            isDeveloper, setIsDeveloper, 
            isLoggedIn, setIsLoggedIn, logout,
            username, setUsername,
            verifiedState, setVerifiedState
            }}>
            {children}
        </UserContext.Provider>
    );
}

export function useUser() {
    return useContext(UserContext);
}