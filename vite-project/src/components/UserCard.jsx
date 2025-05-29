import React from 'react';
import axios from "axios";
import { useState, useEffect } from 'react'
//import "../CSS/UserCard.css";


function UserCard({data:{userid,username},verifyUser}){
    const [verified, setVerified] = useState(false);
    const [loading, setLoading] = useState(false);

    async function handleVerify() {
        setLoading(true);
        let timeoutId = setTimeout(() => {
            setLoading(false);
        }, 10000); // 10 seconds
        //console.log(userid)
        const result = await verifyUser(userid);
        clearTimeout(timeoutId);

        if (result === true) {
            setVerified(true);
            setLoading(false);
        }
        setLoading(false);
    }

    return(
        <div className="user-card">
            <span>
                <strong>{username}</strong> (ID: {userid})
            </span>
            <button className="user-card-verify-button" 
            onClick={handleVerify}
            disabled={verified || loading}
            style={{
                background: verified ? "#aaa" : undefined,
                cursor: verified ? "not-allowed" : undefined
            }}>
                 {verified ? "Verified" : loading ? "Verifying..." : "Verify"}
            </button>
        </div>

    )


}
export default UserCard;