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

    const [currentChapterID, setCurrentChapterID] = useState("");
    const [currentChapterTitle, setCurrentChapterTitle] = useState('');
    const [chapterList, setChapterList]=useState([]);
    const [chapterNames, setChapterNames] = useState([]);
    const [chapterDir, setChapterDir]=useState([]);
    const [chapterIDList, setChapterIDList] = useState([]);

    function extractChapterNames(dataArray) {
    return dataArray.map(str => {
        const [, , filePathRaw = ''] = str.split(';');
        const fileName = filePathRaw.trim().split('/').pop() || '';
        let name = fileName
        .replace(book[1], '')
        .replace('.html', '')
        .replace(/^[-_\s]+/, '')
        .trim();

        const extraMatch = name.match(/(?:^|\s)-?\s*(?:Chapter\s*)?\d+\s*-\s*(Extra.*)$/i);
        if (extraMatch) {
            return extraMatch[1].trim();
        }

        // Remove leading number and dash if followed by "Chapter"
        name = name.replace(/^\d+\s*-\s*(?=Chapter\s*\d+)/i, '');

        //Ensure only one "Chapter" at the start
        const chapterMatch = name.match(/(Chapter\s*\d+.*)/i);
        if (chapterMatch) {
            name = chapterMatch[1].trim();
        } else if (!/^Chapter/i.test(name)) {
            name = "Chapter " + name;
        }
        

        return name;
    });
}

    function extractChapterDir(dataArray){
        return dataArray.map(str => str.split(';')[2]?.trim());
    }
    function extractChapterIDs(dataArray) {
        return dataArray.map(str => {
            return str.split(';')[0]?.trim();
        });
    }
    

    async function grabBookChapter(){
        try {
            const response = await axios.get(`${API_URL}/getBookChapterList/${book[0]}`, { withCredentials: true });
            if (response.statusText !== "OK") {
                console.log("Error getting book chapter");
            } else if (response.data.Response === "False") {
                console.log("Error getting book chapter");
            }
            console.log(response.data)
            setChapterList(response.data);
            
            //const chapterNames=extractChapterNames(response.data);
            // setChapterNames(chapterNames);
            // const chapterLinks=extractChapterDir(response.data);
            // setChapterDir(chapterLinks);
            const chapterIDs= extractChapterIDs(response.data);
            setChapterIDList(chapterIDs);
            //console.log("Chapter ID List: ", chapterIDList);
            
        } catch (error) {
            console.log(error);
        }
        //console.log(book);
    }

    function renderChapterList({ grabChapterContent }) {
    return (
        <ul style={{ listStyle: "none", padding: 0 }}>
        {chapterList.map((chapterStr, index) => {
            const parts = chapterStr.split(';');
            const chapterID = parts[0]?.trim() || index;
            const chapterTitle = parts[2]?.trim() || '';
            return (
            <li
                key={chapterID + '-' + index} // Use both for uniqueness if IDs repeat
                onClick={() => grabChapterContent(chapterID, chapterTitle)}
            >
                {chapterTitle}
            </li>
            );
        })}
        </ul>
    );
    }
    function goToPreviousChapter() {
        // Find the index of the current chapter in chapterList
        const currentIndex = chapterList.findIndex(str => {
            const parts = str.split(';');
            return parts[0]?.trim() === currentChapterID && (parts[2]?.trim() === currentChapterTitle);
        });
        if (currentIndex > 0) {
            const prevChapterStr = chapterList[currentIndex - 1];
            const prevParts = prevChapterStr.split(';');
            const prevChapterID = prevParts[0]?.trim();
            const prevChapterTitle = prevParts[2]?.trim() || '';
            console.log("Previous Chapter ID: ", prevChapterID, "Title: ", prevChapterTitle);
            grabChapterContent(prevChapterID, prevChapterTitle);
        }
    }

    function goToNextChapter() {
        // Find the index of the current chapter in chapterList
        const currentIndex = chapterList.findIndex(str => {
            const parts = str.split(';');
            return parts[0]?.trim() === currentChapterID && (parts[2]?.trim() === currentChapterTitle);
        });
        if (currentIndex !== -1 && currentIndex < chapterList.length - 1) {
            const nextChapterStr = chapterList[currentIndex + 1];
            const nextParts = nextChapterStr.split(';');
            const nextChapterID = nextParts[0]?.trim();
            const nextChapterTitle = nextParts[2]?.trim() || '';
            console.log("Next Chapter ID: ", nextChapterID, "Title: ", nextChapterTitle);
            grabChapterContent(nextChapterID, nextChapterTitle);
        }
    }

    // Add key press listener for chapter navigation
    useEffect(() => {
        function handleKeyDown(e) {
            if (
                e.key === 'ArrowLeft' ||
                e.key === 'a' ||
                e.key === 'A'
            ) {
                goToPreviousChapter();
            } else if (
                e.key === 'ArrowRight' ||
                e.key === 'd' ||
                e.key === 'D'
            ) {
                goToNextChapter();
            }
        }
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [currentChapterID, currentChapterTitle, chapterList]);

    //DONE TODO: If it spacebattles, we need to do some extra processing to get the chapter list
    //Otherwise, it is straightforward. use the directory saved from the order of contents, and then grab the content of the chapter
    //I am contemplating whether to grab all the chapters at once or just grab the desired chapter when the user clicks on it.
    //The former is more efficient for the server but the latter is more efficient for the client in terms of memory usage.
    //Though it shouldn't be that bad since images won't be loaded until after react dom renders the chapter content.
    //DO THIS ON SERVER SIDE, so that the client doesn't have to do any processing.


    //DONE TODO: Add in chapter navigation, so the user can click on a chapter in the list and it will load the content of that chapter.
    //DONE TODO: Also make it so that there are two buttons the user can click on to go to the next or previous chapter.
    //DONE TODO: Also make it so that the user can use the arrow keys to navigate through the chapters.
    //TODO: Limit the size of the div containing the chapter content to a certain height, and make it scrollable if the content exceeds that height.



    async function grabChapterContent(chapterID, chapterTitle) {
        console.log("Grab chapter content for: ", book[0], chapterID, chapterTitle);
        try {
            // Send bookID, chapterID, and chapterTitle as query parameters
            const response = await axios.get(`${API_URL}/getBookChapterContent`, {
                params: {
                    bookID: book[0],
                    chapterID: chapterID,
                    chapterTitle: chapterTitle
                },
                withCredentials: true
            });
            if (response.status===200){
                setChapterHTML(response.data.chapterContent);
                setCurrentChapterTitle(response.data.chapterTitle);
                setChapterLoaded(true);
                setCurrentChapterID(chapterID);
            }
            if (response.statusText !== "OK" || response.data.Response === "False") {
                console.log("Error getting chapter content");
            }
        } catch (error) {
            console.log(error);
        }
    }

return (
    <>
        <NavBar />
        <div className="reader-main-container">
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
                <button onClick={goToPreviousChapter}>&lt;</button>
                <div className="reader-book-main-panel-heading">
                {!chapterLoaded ? (
                    <button onClick={grabBookChapter}>Grab Book Chapter</button>
                ) : (
                    <h2 style={{ margin: 0 }}>{currentChapterTitle}</h2>
                )}
                </div>
                <button onClick={goToNextChapter}>&gt;</button>

                </div>
                {/* Chapter Content */}
                <div className="reader-book-main-panel-chapter-content"
                    dangerouslySetInnerHTML={{ __html: chapterHTML }}/>
            </div>
            {/* Right Panel (Long Panel) */}
            <div className="reader-book-right-panel">
                <div className="reader-book-right-panel-chapters-panel">
                    <h4 className="sticky-chapter-header">Available Chapters</h4>
                    <div className="chapter-list-scroll">
                        {renderChapterList({ grabChapterContent })}
                    </div>
                </div>
            </div>
        </div>
    </>
)
}

export default OnlineReaderPage;

