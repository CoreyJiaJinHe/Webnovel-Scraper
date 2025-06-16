import React,{ useState, useEffect, useRef } from 'react'
import { useLocation } from "react-router-dom";

import NavBar from '../components/NavBar.jsx'
import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });
import { useUser } from "../components/UserContext.jsx";


function OnlineReaderPage() {

    const {
            isLoggedIn, setIsLoggedIn,
            username, setUsername,
            verifiedState, setVerifiedState,
            logout
        } = useUser();
    const { state } = useLocation();
    const book = state?.book;

    const [chapterHTML, setChapterHTML]=useState('');

    const [currentChapter, setCurrentChapter] = useState(0);
    const [currentChapterTitle, setCurrentChapterTitle] = useState('');
    const [chapterList, setChapterList]=useState([]);
    async function grabBookChapter(){
        try {
            const response = await axios.get(`${API_URL}/getBookChapter`);
            if (response.statusText !== "OK") {
                console.log("Error getting book chapter");
            } else if (response.data.Response === "False") {
                console.log("Error getting book chapter");
            } else {
                console.log(response.data);
            }
        } catch (error) {
            console.log(error);
        }
        console.log(book);
    }

return (
    <>
        <NavBar />
        <div
            className="reader-main-container"
            style={{
                marginLeft: "120px",
                marginRight: "120px",
                minHeight: "100vh",
                display: "flex",
                flexDirection: "row",
                gap: "2rem"
            }}
        >
            {/* Left Panel */}
            <div style={{ width: "250px", display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                {/* Book Details Panel */}
                <div
                    style={{
                        background: "#23232b",
                        borderRadius: "8px",
                        padding: "1rem",
                        color: "#fff",
                        marginBottom: "1rem",
                        marginTop: "2.5rem"
                    }}
                >
                    <h3 style={{ marginTop: 0 }}>Book Details</h3>
                    {book ? (
                        <ul style={{ listStyle: "none", padding: 0 }}>
                            <li><strong>Title:</strong> {book[1]}</li>
                            <li><strong>Author:</strong> {book[2]}</li>
                            <li><strong>Description:</strong>
                                <div
                                    style={{
                                        maxHeight: "100px",
                                        overflowY: "auto",
                                        marginTop: "0.25rem",
                                        background: "#18181b",
                                        padding: "0.5rem",
                                        borderRadius: "4px"
                                    }}
                                >
                                    {book[3]}
                                </div>
                            </li>
                            <li><strong>Latest Chapter:</strong> {book[6]}</li>
                            <li><strong>Last Scraped:</strong> {book[5]}</li>
                        </ul>
                    ) : (
                        <p>No book selected.</p>
                    )}
                </div>
            </div>
            {/* Main Content */}
            <div style={{ flex: 1 }}>
                {/* Centered h1 */}
                <h1 style={{ textAlign: "center", marginTop: "2.5rem" }}>Online Reader</h1>
                {/* 500px wide div under h1 */}
                <div
                    style={{
                        width: "500px",
                        margin: "1.5rem auto",
                        background: "#23232b",
                        borderRadius: "8px",
                        padding: "1rem",
                        color: "#fff",
                        textAlign: "center"
                    }}
                >
                    <button onClick={grabBookChapter}>Grab Book Chapter</button>
                </div>
                {/* Chapter Content */}
                <div
                    className="chapter-content"
                    style={{
                        background: "#23232b",
                        borderRadius: "8px",
                        padding: "1.5rem",
                        color: "#fff",
                        marginTop: "2rem",
                        minHeight: "300px"
                    }}
                    dangerouslySetInnerHTML={{ __html: chapterHTML }}
                />
            </div>
            {/* Right Panel (Long Panel) */}
            <div style={{
                width: "250px",
                display: "flex",
                flexDirection: "column",
                gap: "1.5rem",
                marginTop: "2.5rem"
            }}>
                <div
                    style={{
                        background: "#18181b",
                        borderRadius: "8px",
                        padding: "1rem",
                        color: "#fff",
                        minHeight: "200px",
                        flex: 1
                    }}
                >
                    <h4>Extra Panel</h4>
                    <p>Additional content or controls can go here.</p>
                </div>
            </div>
        </div>
    </>
)
}

export default OnlineReaderPage;

