import React, { useState, useEffect } from 'react';
import NavBar from '../components/NavBar.jsx';

import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });
function BookScraperPage() {
    const [searchTerm, setSearchTerm] = useState('');
    const [buttonText, setButtonText] = useState('Search');
    const [book, setBook] = useState(null);
    const [selectedSite, setSelectedSite] = useState('royalroad');
    const [showPopup, setShowPopup] = useState(false);


    function setSessionCookie(name, value) {
        document.cookie = `${name}=${value}; path=/; samesite=strict`;
    }

    function getSessionCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    
    useEffect(() => {
        if (!getSessionCookie('seenBookScraperPopup')) {
            setShowPopup(true);
        }
    }, []);

    const handleClosePopup = () => {
        setShowPopup(false);
        setSessionCookie('seenBookScraperPopup', '1');
    };

    // Dummy book data for demonstration; replace with real fetch logic as needed
    const dummyBook = [
        1,
        "Example Book Title",
        "Example Author",
        "This is an example description for the book.",
        "Example Latest Chapter"
    ];

    async function handleSearch(){
        if (buttonText === 'Search') {
            // Simulate search and show book details
            try{
                console.log("Searching for book:", searchTerm, "on site:", selectedSite);
                const response = await axios.get(`${API_URL}/query_book`, {
                    params: {
                        searchTerm: searchTerm,
                        siteHost: selectedSite
                    },
                    withCredentials: true
                });
            if (response.statusText === "OK") {
                setBook(response.data);
                setButtonText('Scrape');
            }
            else{
                console.log("Error fetching book data:", error);
            }
        }
        catch (error){
            console.log("Error fetching book data:", error);
        }
    }
    else if (buttonText === 'Scrape') {
        try{    
        const response = await axios.post(`${API_URL}/scrape_book`, {
                params: {
                    term: searchTerm,
                    site: selectedSite
                },
                withCredentials: true
            });
            if (response.statusText !== "OK") {
            }
        }
        catch (error){
            console.log("Error scraping book data:", error);
        }
    }
    };



    return (
        <>
            <NavBar />
            {showPopup && (
                <div className= "book-scraper-pop-up" >
                    <div className="book-scraper-pop-up-inner">
                        <button className="book-scraper-pop-up-close-button"
                        onClick={handleClosePopup} aria-label="Close">
                            ×
                            </button>
                        <h2 style={{ marginTop: 0, marginBottom: '1.5rem', fontSize: '2.2rem' }}>
                            Welcome to the Online Book Scraper Interface!
                        </h2>
                        <p style={{ textAlign: 'center', maxWidth: 500 }}>
                            Here you can directly scrape a webnovel! Either enter the book's title to search the compatible sites, or link a webnovel directly!<br /><br />
                            Click the × in the corner to close this message. You won't see it again this session.
                        </p>
                    </div>
                </div>
            )}
            <div className="scrape-background">
            <div className="scrape-container" >
                {/* Left Panel (keep default/dark background) */}
                <div className="scrape-left-panel">
                    <div className="scrape-book-details-panel">
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
                                <li><strong>Latest Chapter:</strong> {book[4]}</li>
                            </ul>
                        ) : (
                            <p>No book selected.</p>
                        )}
                    </div>
                </div>
                {/* Main Content */}
                <div className ="scrape-container-main-content">
                    {/* Card for search controls */}
                    <div className="scrape-main-search-card">
                        <select className ="scrape-main-search-select-dropdown"
                            value={selectedSite}
                            onChange={e => setSelectedSite(e.target.value)}>
                            <option value="royalroad">Royal Road</option>
                            <option value="scribblehub">ScribbleHub</option>
                            <option value="spacebattles">SpaceBattles</option>
                            <option value="novelbin">NovelBin</option>
                            <option value="foxaholic">Foxaholic</option>
                        </select>
                        <div className="scrape-main-search-select-input-row">
                            <input
                                type="text"
                                placeholder="Enter book title or URL..."
                                value={searchTerm}
                                onChange={e => setSearchTerm(e.target.value)}
                                
                            />
                            <button onClick={handleSearch}>
                                {buttonText}
                            </button>
                        </div>
                    </div>
                </div>
                {/* Right Panel: Chapter List */}
                    <div className="scrape-right-panel">
                        <div className="scrape-chapter-list-panel">
                            <h3 style={{ marginTop: 0 }}>Chapters</h3>
                            {book && Array.isArray(book[book.length - 1]) ? (
                                <ul style={{ listStyle: "none", padding: 0, maxHeight: 500, overflowY: 'auto' }}>
                                    {book[book.length - 1].map((chapter, idx) => (
                                        <li key={idx} style={{ marginBottom: '0.5rem' }}>
                                            {chapter}
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <p style={{ color: "#aaa" }}>No chapters loaded.</p>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}

export default BookScraperPage;


// .scrape-container{
//     style={{
//                     display: 'flex',
//                     flexDirection: 'row',
//                     alignItems: 'flex-start',
//                     justifyContent: 'center',
//                     marginTop: '2.5rem',
//                     gap: '2rem'
//                 }}
// }

// .scrape-left-panel{
//     width: 250px;
//     display: flex;
//     flex-direction: column;
//     gap: 1.5rem;
//     maxWidth: 400, minWidth: 300, margin: 0 
// }

// .scrape-book-details-panel{
//     background: #23232b;
//     border-radius: 8px;
//     padding: 1rem;
//     color: #fff;
//     margin-bottom: 1rem;
//     margin-top: 2.5rem;}


// .scrape-container-main-content{
//     style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'flex-start' , marginTop: '2.5rem' // <-- Add this line
// }}>
// }

// .scrape-main-search-card{
//     style={{
//                             background: '#fff',
//                             border: '2px solid #111',
//                             borderRadius: '8px',
//                             padding: '2rem 2rem 1.5rem 2rem',
//                             minWidth: 400,
//                             boxShadow: '0 2px 8px rgba(0,0,0,0.06)'
                            
//                         }}
// }

// .scrape-main-search-select-dropdown{
//      style={{
//                                 backgroundColor: '#fff',
//                                 color: '#222',
//                                 border: '1.5px solid #888',
//                                 borderRadius: '4px',
//                                 outline: 'none',
//                                 width: '220px',
//                                 padding: '0.5rem',
//                                 fontSize: '1rem',
//                                 marginBottom: '1rem'
//                             }}
// }

// .scrape-main-search-select-input-row{
//     style={{ display: 'flex', justifyContent: 'center' }}
// }

// .scrape-main-search-select-input-row input{
//     style={{
//                                     backgroundColor: '#fff',
//                                     color: '#222',
//                                     border: '1.5px solid #888',
//                                     borderRadius: '4px',
//                                     outline: 'none',
//                                     width: '350px',
//                                     padding: '0.5rem',
//                                     fontSize: '1rem'
//                                 }}
// }

// .scrape-main-search-select-input-row button{
//      style={{
//                                     backgroundColor: '#fff',
//                                     color: '#222',
//                                     border: '1.5px solid #888',
//                                     borderRadius: '4px',
//                                     outline: 'none',
//                                     padding: '0.5rem 1.5rem',
//                                     fontSize: '1rem',
//                                     marginLeft: '1rem',
//                                     cursor: 'pointer'
//                                 }}
