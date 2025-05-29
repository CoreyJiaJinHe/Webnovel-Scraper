import React from 'react';
import axios from "axios";
//import "../CSS/UserCard.css";


function UserCard({data:{userid,username},verifyUser}){
    return(
        <div className="user-card">
            <span>
                <strong>{username}</strong> (ID: {userid})
            </span>
            <button className="user-card-verify-button" onClick={() => verifyUser(userid)}>
                Verify
            </button>
        </div>

    )


}
export default UserCard;