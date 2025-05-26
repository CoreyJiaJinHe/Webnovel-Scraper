import { createContext, useContext, useState,useEffect } from "react";
export const UserContext = createContext();

export function UserProvider({ children }) {
    const [isDeveloper, setIsDeveloper] = useState(false);
    const [isLoggedIn, setIsLoggedIn]=useState(false);
    useEffect(() => {
        const loginTime = localStorage.getItem("loginTime");
        if (loginTime) {
            const now = Date.now();
            const oneDay = 24 * 60 * 60 * 1000;
            if (now - parseInt(loginTime, 10) < oneDay) {
                setIsLoggedIn(true);
            } else {
                setIsLoggedIn(false);
                localStorage.removeItem("loginTime");
            }
        }
    }, []);

    return (
        <UserContext.Provider value={{ isDeveloper, setIsDeveloper, isLoggedIn, setIsLoggedIn}}>
        {children}
        </UserContext.Provider>
    );
}

export function useUser() {
    return useContext(UserContext);
}