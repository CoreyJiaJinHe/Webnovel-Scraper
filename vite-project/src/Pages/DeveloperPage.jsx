import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom';
import { useUser } from "../components/UserContext";
import NavBar from '../components/NavBar'

import '../DeveloperPage.css'
import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });



export function DeveloperPage() {
  
  const [username, setUserName]=useState("");
  const [verifiedState, setVerifiedState]=useState(false);
  const {isDeveloper,setIsDeveloper,isLoggedIn, setIsLoggedIn} = useUser();
  const [bookCounts, setBookCounts] = useState({
    RoyalRoad: 0,
    NovelBin: 0,
    Spacebattles: 0,
    Foxaholic: 0,
    Other: 0,
  });

  useEffect(()=>{tokenLogin(),fetchBookCounts()},[])

  //Rewrite this. 
  async function fetchBookCounts() {
    try {
      const response = await axios.get(`${API_URL}/allBooks/`, { withCredentials: true });
      if (response.status === 200 && Array.isArray(response.data)) {
        // Assuming each book has a "source" or "host" property
        const counts = {
          RoyalRoad: 0,
          NovelBin: 0,
          Spacebattles: 0,
          Foxaholic: 0,
          Other: 0,
        };
        response.data.forEach(book => {
          const source = (book.websiteHost || book.source || "").toLowerCase();
          if (source.includes("royalroad")) counts.RoyalRoad++;
          else if (source.includes("novelbin")) counts.NovelBin++;
          else if (source.includes("spacebattles")) counts.Spacebattles++;
          else if (source.includes("foxaholic")) counts.Foxaholic++;
          else counts.Other++;
        });
        setBookCounts(counts);
      }
    } catch (error) {
      // Optionally handle error
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
    <div className="developer-page-main-panel">
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
          {/* Right panel */}
        <div className="developer-page-right-users-panel">




        </div>

    </div>


    </>

  )
}

export default DeveloperPage