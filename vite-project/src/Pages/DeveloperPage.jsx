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

  const [bookCounts, setBookCounts] = useState({});
  
  const [importedBooksTotal, setImportedBooksTotal] = useState(0);
  const [importedNonEditedBooksTotal, setImportedNonEditedBooksTotal] = useState(0);

  const [usersToVerify, setUsersToVerify]=useState([]);

  useEffect(()=>{tokenLogin(),fetchBookCounts(),fetchUsersToVerify(), fetchImportedBooksTotals()},[])


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
      const counts = {};
      response.data.forEach(([source, booksArr]) => {
        // Normalize the source name
        let label = source || "Other";
        // Remove protocol, www., subdomains, and TLDs
        label = label
          .replace(/^(https?:\/\/)?(www\.)?/i, "") // remove protocol and www
          .replace(/^forums\./i, "") // remove 'forums.' prefix
          .replace(/\..*$/, "") // remove everything after first dot (TLD and subdomains)
          .toLowerCase();
        // Capitalize first letter
        label = label.charAt(0).toUpperCase() + label.slice(1);
        counts[label] = Array.isArray(booksArr) ? booksArr.length : 0;
      });
      setBookCounts(counts);
    }
  } catch (error) {
    console.error("Failed to fetch book counts:", error);
  }
}
  async function fetchImportedBooksTotals() {
    try {
      const response = await axios.get(`${API_URL}/dev/get_total_imported_books/`, { withCredentials: true });
      
      if (response.status === 200 && Array.isArray(response.data)) {
        setImportedBooksTotal(Number(response.data) || 0);
      }
    } catch (error) {
      console.error("Failed to fetch imported books:", error);
    }
    try{
      const response = await axios.get(`${API_URL}/dev/get_total_imported_non_edited_books/`, { withCredentials: true });
      
      if (response.status === 200 && Array.isArray(response.data)) {
        setImportedNonEditedBooksTotal(Number(response.data) || 0);
      }
    } catch (error) {
      console.error("Failed to fetch imported non-edited books:", error);
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
  const [importedBooks,setImportedBooks]=useState([]);

  async function retrieve_imported_books(){
    try {
      const response = await axios.get(`${API_URL}/dev/get_imported_books/`, { withCredentials: true });
      if (response.status === 200 && Array.isArray(response.data)) {
        // Process the imported books data
        console.log("Imported books:", response.data);
      }
    } catch (error) {
      console.error("Failed to retrieve imported books:", error);
    }
  }

  const [importedNonEditedBooks,setImportedNonEditedBooks]=useState([]);
  async function retrieve_imported_non_edited_books(){
    try{
      const response = await axios.get(`${API_URL}/dev/get_imported_non_edited_books/`, { withCredentials: true });
      if (response.status === 200 && Array.isArray(response.data)) {
        // Process the non-edited imported books data
        console.log("Non-edited imported books:", response.data);
      }
    } catch (error) {
      console.error("Failed to retrieve non-edited imported books:", error);
    }
  }

  const [availableBooksForImport, setAvailableBooksForImport] = useState([]);
  const [sanitizedBooksForImport, setSanitizedBooksForImport] = useState([]);

  // Update your retrieve_available_books function:
  async function retrieve_available_books() {
    try {
      const response = await axios.post(`${API_URL}/dev/fetch_available_books_for_import/`, {}, { withCredentials: true });
      if (response.status === 200 && Array.isArray(response.data)) {
        setAvailableBooksForImport(response.data);
        // Create a sanitized version for display
        const sanitized = response.data.map(str => str.replace(/_/g, " "));
        setSanitizedBooksForImport(sanitized);
        console.log("Available books for import:", response.data);
      }
    } catch (error) {
      console.error("Failed to retrieve available books for import:", error);
    }
  }

  async function importBook(bookLabel) {
    try{
      const response = await axios.post(`${API_URL}/dev/import_book/`, { bookLabel }, { withCredentials: true });
      if (response.status === 200) {
        console.log("Book imported successfully:", response.data);
      }
    }
    catch (error){
      console.error("Failed to import book:", error);
    }

  }

  return (
    <>
    <NavBar/>
    <div className="developer-page-main-container">
      <div className="developer-page-left-column">
        <div className="developer-page-left-statistics-panel">
          <h1 style={{textDecoration: "underline", marginTop: 0, fontSize: "2rem", fontWeight: "bold", color: "#222" }}>Book Statistics</h1>
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {Object.entries(bookCounts)
              .sort(([a], [b]) => {
                const order = [
                  "Royalroad",
                  "Spacebattles",
                  "Novelbin",
                  "Foxaholic"
                ];
                const idxA = order.findIndex(site => a.toLowerCase() === site.toLowerCase());
                const idxB = order.findIndex(site => b.toLowerCase() === site.toLowerCase());
                if (idxA === -1 && idxB === -1) return a.localeCompare(b); // both unknown, sort alphabetically
                if (idxA === -1) return 1; // a is unknown, put after b
                if (idxB === -1) return -1; // b is unknown, put after a
                return idxA - idxB; // sort by order
              })
              .map(([site, count]) => (
                <li key={site}>
                  <strong>{site}:</strong> {count}
                </li>
              ))}
          </ul>
          <h1 style={{textDecoration: "underline", margin: "1rem 0", fontSize: "2rem", fontWeight: "bold" }}>Imported Books:</h1>
              <p>Imported: {importedBooksTotal || 0}</p>
              <p>Non-Edited: {importedNonEditedBooksTotal || 0}</p>
        </div>

        <div className="developer-page-left-import-panel">
          <h1
            style={{
              textDecoration: "underline",
              margin: 0,
              padding: "1rem 0 0.5rem 0",
              fontSize: "1rem",
              fontWeight: "bold",
              background: "#f5f5f5",
              zIndex: 1,
            }}
          >
            Available Books for Import
          </h1>
          <div style={{ overflowY: "auto", maxHeight: "300px", padding: "0 1rem" }}>
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {availableBooksForImport.length === 0 ? (
                <li>No books available for import.</li>
              ) : (
                availableBooksForImport.map((bookLabel, idx) => (
                  <li
                    key={bookLabel || idx}
                    style={{
                      marginBottom: "0.75rem",
                      background: "#f5f5f5",
                      borderRadius: "8px",
                      boxShadow: "0 1px 4px rgba(0,0,0,0.07)",
                      padding: "1px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      minHeight: "48px",
                      wordBreak: "break-word"
                    }}
                  >
                    <span style={{ fontSize: "0.95rem", flex: 1, marginRight: "1rem", wordBreak: "break-word" }}>
                      {sanitizedBooksForImport[idx]}
                    </span>
                    <button
                      style={{
                        padding: "2px 10px",
                        fontSize: "0.85rem",
                        backgroundColor: "#1976d2",
                        color: "#fff",
                        border: "none",
                        borderRadius: "4px",
                        cursor: "pointer",
                        whiteSpace: "nowrap"
                      }}
                      className="button"
                      onClick={() => {
                        importBook(bookLabel);
                      }}
                    >
                      Import
                    </button>
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>
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
            <div className="developer-page-action-card">
              <p>See imported books</p>
              <button className="button" onClick={retrieve_imported_books}>View</button>
            </div>
            <div className="developer-page-action-card">
              <p>See imported books that need action</p>
              <button className="button" onClick={retrieve_imported_non_edited_books}>View</button>
            </div>
            <div className="developer-page-action-card">
              <p>See available books to import</p>
              <button className="button" onClick={retrieve_available_books}>View</button>
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