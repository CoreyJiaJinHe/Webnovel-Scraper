import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom';
import { useUser } from "../components/UserContext";
import NavBar from '../components/NavBar'
import UserCard from '../components/UserCard'


//import '../DeveloperPage.css'
import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });



export function DeveloperPage() {
  
  
  const {
    isLoggedIn, setIsLoggedIn,
    username, setUsername,
    verifiedState, setVerifiedState,
    isDeveloper,setIsDeveloper} = useUser();

  const [bookCounts, setBookCounts] = useState({
    RoyalRoad: 0,
    NovelBin: 0,
    Spacebattles: 0,
    Foxaholic: 0,
    Other: 0,
  });
  const [usersToVerify, setUsersToVerify]=useState([]);

  useEffect(()=>{tokenLogin(),fetchBookCounts(),fetchUsersToVerify()},[])


  async function fetchUsersToVerify(){
    try{
      const response = await axios.get(`${API_URL}/dev_get_unverified/`, { withCredentials: true });
      if (response.status===200){
        setUsersToVerify(response.data);
        console.log("Users to verify:", response.data);
      }
      else{
        console.log("Failed to fetch users to verify, status code:", response.status);
      }
    }
    catch (error) {
      console.error("Failed to get unverified users:", error);
    }
  }

  function renderUsersToVerify(){
    if (!usersToVerify || usersToVerify.length === 0) {
    return <div>No users to verify.</div>;
    }
    //console.log(usersToVerify);
    return usersToVerify.map(user => (
      <UserCard
        key={user._id || user.userID}
        data={{
          userid: user.userID,
          username: user.username
        }}
        verifyUser={interface_verifyUser}
      />
    ));
  }

  function interface_verifyUser(userid){
    return verifyUser(userid);
  }

  async function verifyUser(userid) {
    try {
        const response = await axios.post(`${API_URL}/dev_verify_users/`, {"userid":userid},{ withCredentials: true });

        if (response.status === 200) return true;
    } catch (e) {}
    return false;
  }

  async function fetchBookCounts() {
    try {
      const response = await axios.get(`${API_URL}/allBooks/`, { withCredentials: true });
      if (response.status === 200 && Array.isArray(response.data)) {
        //console.log(response.data);
        const counts = {
          RoyalRoad: 0,
          NovelBin: 0,
          Spacebattles: 0,
          Foxaholic: 0,
          Other: 0,
        };
        // Loop through each [source, booksArr] pair
        response.data.forEach(([source, booksArr]) => {
        const normalizedSource = (source || "").toLowerCase();
        const numBooks = Array.isArray(booksArr) ? booksArr.length : 0;

        if (normalizedSource.includes("royalroad")) {
          counts.RoyalRoad += numBooks;
        } else if (normalizedSource.includes("novelbin")) {
          counts.NovelBin += numBooks;
        } else if (normalizedSource.includes("spacebattles")) {
          counts.Spacebattles += numBooks;
        } else if (normalizedSource.includes("foxaholic")) {
          counts.Foxaholic += numBooks;
        } else {
          counts.Other += numBooks;
        }
      });

      console.log("Book counts:", counts);
      setBookCounts(counts);
      }
    } catch (error) {
      console.error("Failed to fetch book counts:", error);
    }
  }

  const navigate = useNavigate();
  async function tokenLogin(){
    if (!isDeveloper && !isLoggedIn){
      navigate("/react/LoginPage/");
    }
    else
    {
      try{
        const response=await axios.post(`${API_URL}/token/`,{}, {withCredentials:true});
        //console.log(response)
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

  async function royalroad_retrieveFollowedList(){
    try{
      const response = await axios.post(`${API_URL}/dev/rrfollows/`, { withCredentials: true });
    }
    catch (error){
      console.error("Failed to retrieve followed list from RoyalRoad:", error);
    }
  }


  return (
    <>
    <NavBar/>
    <div className="developer-page-main-container">
        <div className="developer-page-left-statistics-panel">
          <h1 style={{ marginTop: 0, fontSize: "2rem", fontWeight: "bold", color: "#222" }}>Books</h1>
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            <li><strong>RoyalRoad:</strong> {bookCounts.RoyalRoad}</li>
            <li><strong>NovelBin:</strong> {bookCounts.NovelBin}</li>
            <li><strong>Spacebattles:</strong> {bookCounts.Spacebattles}</li>
            <li><strong>Foxaholic:</strong> {bookCounts.Foxaholic}</li>
            <li><strong>Other:</strong> {bookCounts.Other}</li>
          </ul>
        </div>
        {/*TODO*/}
        <div className={"developer-page-center-panel"}>
          <h1 style={{ marginTop: 0, fontSize: "2rem", fontWeight: "bold", color: "#222" }}>Available Actions</h1>
          <hr></hr>
          <div className="developer-page-action-cards-grid">
            <div className="developer-page-action-card">
              <p>Retrieve my followed list from RoyalRoad</p>
              <button className="button">Retrieve</button>
            </div>
          </div>
        </div>
          {/* Right panel */}
        <div className="developer-page-right-users-panel">
          <h1 style={{ marginTop: 0, fontSize: "2rem", fontWeight: "bold", color: "#222" }}>
            Users that need verification</h1>
            <hr></hr>
            <div className="developer-page-users-list"
          >{renderUsersToVerify()}</div>
        </div>
    </div>


    </>

  )
}

export default DeveloperPage