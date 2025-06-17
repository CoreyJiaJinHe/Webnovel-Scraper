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
    const [chapterLoaded, setChapterLoaded] = useState(false);

    const [currentChapter, setCurrentChapter] = useState(0);
    const [currentChapterTitle, setCurrentChapterTitle] = useState('');
    const [chapterList, setChapterList]=useState([]);

    async function grabBookChapter(){
        try {
            const response = await axios.get(`${API_URL}/getBookChapterList/${book[0]}`, { withCredentials: true });
            if (response.statusText !== "OK") {
                console.log("Error getting book chapter");
            } else if (response.data.Response === "False") {
                console.log("Error getting book chapter");
            }
            console.log(response.data);
            
        } catch (error) {
            console.log(error);
        }
        console.log(book);
    }
    //TODO: If it spacebattles, we need to do some extra processing to get the chapter list
    //Otherwise, it is straightforward. use the directory saved from the order of contents, and then grab the content of the chapter
    //I am contemplating whether to grab all the chapters at once or just grab the desired chapter when the user clicks on it.
    //The former is more efficient for the server but the latter is more efficient for the client in terms of memory usage.
    //Though it shouldn't be that bad since images won't be loaded until after react dom renders the chapter content.

    //TODO: Add in chapter navigation, so the user can click on a chapter in the list and it will load the content of that chapter.
    //Also make it so that there are two buttons the user can click on to go to the next or previous chapter.
    //Also make it so that the user can use the arrow keys to navigate through the chapters.
    //TODO: Limit the size of the div containing the chapter content to a certain height, and make it scrollable if the content exceeds that height.



    async function grabChapterContent(chapterId) {
        try {
            const response = await axios.get(`${API_URL}/getBookChapterContent/${book[0]}/${chapterId}`, { withCredentials: true });
            if (response.statusText !== "OK") {
                console.log("Error getting chapter content");
            } else if (response.data.Response === "False") {
                console.log("Error getting chapter content");
            }
            setChapterHTML(response.data.chapterContent);
            setCurrentChapterTitle(response.data.chapterTitle);
            setChapterLoaded(true);
        } catch (error) {
            console.log(error);
        }
    }
    // useEffect(() => {
    //     if (book) {
    //         grabBookChapter();
    //     }
    // }, [book]);
    // useEffect(() => {
    //     if (chapterList.length > 0) {
    //         grabChapterContent(chapterList[currentChapter]);
    //     }
    // }, [currentChapter, chapterList]);


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
            <div className="reader-left-panel" >
                {/* Book Details Panel */}
                <div className="reader-book-details-panel">
                    <h3 style={{ marginTop: 0 }}>Book Details</h3>
                    {book ? (
                        <ul style={{ listStyle: "none", padding: 0 }}>
                            <li><strong>Title:</strong> {book[1]}</li>
                            <li><strong>Author:</strong> {book[2]}</li>
                            <li><strong>Description:</strong>
                                <div className="reader-book-details-panel-description">
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
                <div className ="reader-book-main-panel">
                {!chapterLoaded ? (
                        <button onClick={grabBookChapter}>Grab Book Chapter</button>
                    ) : (
                        <h2 style={{ margin: 0 }}>{currentChapterTitle}</h2>
                    )}
                </div>
                {/* Chapter Content */}
                <div className="reader-book-main-panel-chapter-content"
                    dangerouslySetInnerHTML={{ __html: chapterHTML }}/>
            </div>
            {/* Right Panel (Long Panel) */}
            <div className="reader-book-right-panel">
                <div className="reader-book-right-panel-chapter-list-panel">
                    <h4>Extra Panel</h4>
                    <p>Additional content or controls can go here.</p>
                </div>
            </div>
        </div>
    </>
)
}

export default OnlineReaderPage;

