import React, { useState, useEffect } from 'react';
import NavBar from '../components/NavBar.jsx';

import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });
function BookScraperPage() {
    const [searchTerm, setSearchTerm] = useState('');
    const [searchSuccess, setSearchSuccess] = useState(false);
    const [book, setBook] = useState(null);
    const [selectedSite, setSelectedSite] = useState('royalroad');
    const [showPopup, setShowPopup] = useState(false);
    const [cloudflareCookie, setCloudflareCookie] = useState("");

    const [checkedChapters, setCheckedChapters] = useState([]);
    const [chapterUrls, setChapterUrls] = useState([]);
    const [foxaholicUrlError, setFoxaholicUrlError] = useState("");
    const [websiteHosts, setWebsiteHosts] = useState([])

    
    const [showFoxaholicPopup, setShowFoxaholicPopup] = useState(() => {
    return !getSessionCookie('seenFoxaholicPopup');
    });


    // Foxaholic URL validation
    function isFoxaholicUrl(url) {
        // Accepts URLs like https://foxaholic.com/novel/...
        return /^https?:\/\/(www\.)?foxaholic\.com\/.+/.test(url.trim());
    }


    function getSessionCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    function setSessionCookie(name, value) {
        document.cookie = `${name}=${value}; path=/; samesite=strict`;
    }
    
    useEffect(() => {
        if (!getSessionCookie('seenBookScraperPopup')) {
            setShowPopup(true);
        }
        getWebsiteHosts();
    }, []);

    
    async function getWebsiteHosts(){
        try{
            const response = await axios.get(`${API_URL}/get_website_hosts`, {});
            if (response.statusText === "OK") {
                setWebsiteHosts(response.data);
            }
            else {
                console.error("Error fetching website hosts:", response);
            }
        }
        catch (error) {
            console.error("Error fetching website hosts:", error);
            setWebsiteHosts([]);
        }
    }
    

    const handleClosePopup = () => {
        setShowPopup(false);
        setSessionCookie('seenBookScraperPopup', '1');
    };

    async function handleSearch(){
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
            setSearchSuccess(true);

            const chapters = response.data.chapterTitles;
            const urls = response.data.chapterUrls;
            if (Array.isArray(response.data.chapterTitles) && Array.isArray(response.data.chapterUrls)) {
                setCheckedChapters(new Array(response.data.chapterTitles.length).fill(false));
                setChapterUrls(response.data.chapterUrls);
            } else {
                setCheckedChapters([]);
                setChapterUrls([]);
            }
        }
        else{
            setBook(null);
            setSearchSuccess(false);
            setCheckedChapters([]);
            console.log("Error fetching book data:", error);
        }
    }
    catch (error){
        setBook(null);
        setSearchSuccess(false);
        setCheckedChapters([]);
        console.log("Error fetching book data:", error);
    }
    }

    async function handleScrape() {
        if (!searchSuccess) return;
        // Get selected chapter indices
        const selectedIndices = checkedChapters
            .map((checked, idx) => checked ? idx : -1)
            .filter(idx => idx !== -1);

        // Get selected chapter URLs and titles
        const selectedUrls = selectedIndices.map(idx => chapterUrls[idx]);
        const selectedTitles = selectedIndices.map(idx => book.chapterTitles[idx]);
        try {
            const response = await axios.post(`${API_URL}/scrape_book`, {
                params: {
                    term: book.bookTitle,
                    site: selectedSite,
                    chapters: selectedTitles,
                    urls: selectedUrls
                },
                withCredentials: true
            });
            if (response.statusText !== "OK") {
                // handle error
            }
        } catch (error) {
            console.log("Error scraping book data:", error);
        }
    }
    
    function handleSearchTermChange(e) {
        const value = e.target.value;
        setSearchTerm(value);
        setBook(null);
        setSearchSuccess(false);

        if (selectedSite === "foxaholic") {
            if (!isFoxaholicUrl(value)) {
                setFoxaholicUrlError("Please enter a valid Foxaholic novel URL (e.g., https://foxaholic.com/novel/...).");
            } else {
                setFoxaholicUrlError("");
            }
        } else {
            setFoxaholicUrlError("");
        }
    }


    return (
        <>{showPopup && (
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
            <NavBar />
            
            <div className="scrape-background">
            <div className="scrape-container" >
                {/* Left Panel (keep default/dark background) */}
                <div className="scrape-left-panel">
                    <div className="scrape-book-details-panel">
                        <h3 style={{ marginTop: 0 }}>Book Details</h3>
                        {book ? (
                            <ul style={{ listStyle: "none", padding: 0 }}>
                                <li><strong>Title:</strong> {book.bookTitle}</li>
                                <li><strong>Author:</strong> {book.bookAuthor}</li>
                                <li><strong>Description:</strong>
                                    <div className="reader-book-details-panel-description">
                                        {book.bookDescription}
                                    </div>
                                </li>
                                <li><strong>Latest Chapter:</strong> {book.latestChapterTitle}</li>
                            </ul>
                        ) : (
                            <p>No book selected.</p>
                        )}
                    </div>
                </div>
                {/* Main Content */}
                    <div className="scrape-container-main-content">
                        <div className="scrape-main-search-card">
                            {/* Top row: dropdown + Search button */}
                            <div className="scrape-main-dropdown-row" style={{ position: "relative" }}>
                                <select className="scrape-main-search-select-dropdown"
                                    value={selectedSite}
                                    onChange={e => {
                                        setSelectedSite(e.target.value);
                                        setBook(null);
                                        setSearchSuccess(false);
                                        // Show popup again if switching to foxaholic and not seen before
                                        if (e.target.value === "foxaholic" && !getSessionCookie('seenFoxaholicPopup')) {
                                            setShowFoxaholicPopup(true);
                                        }
                                    }}>
                                    {websiteHosts.map(host => {
                                        // Remove everything from the last period to the end (removes .com, .net, etc.)
                                        const lastDot = host.lastIndexOf(".");
                                        const label = lastDot !== -1 ? host.substring(0, lastDot) : host;
                                        return (
                                            <option key={label} value={label}>
                                                {label}
                                            </option>
                                        );
                                    })}
                                </select>
                                <button
                                    className="scrape-main-search-button"
                                    onClick={handleSearch}
                                    disabled={selectedSite === "foxaholic"}>
                                    Search
                                </button>
                                {/* Foxaholic popup */}
                                {selectedSite === "foxaholic" && showFoxaholicPopup && (
                                    <div
                                        style={{
                                            position: "absolute",
                                            top: "110%",
                                            left: 0,
                                            right: 0,
                                            background: "#fff",
                                            border: "2px solid #d32f2f",
                                            borderRadius: "8px",
                                            boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
                                            padding: "1rem",
                                            zIndex: 100,
                                            color: "#222",
                                            textAlign: "center"
                                        }}
                                    >
                                        <button
                                            style={{
                                                position: "absolute",
                                                top: 8,
                                                right: 12,
                                                background: "none",
                                                border: "none",
                                                fontSize: "1.2rem",
                                                color: "#d32f2f",
                                                cursor: "pointer"
                                            }}
                                            aria-label="Close"
                                            onClick={() => {
                                                setShowFoxaholicPopup(false);
                                                setSessionCookie('seenFoxaholicPopup', '1');
                                            }}
                                        >
                                            ×
                                        </button>
                                        <strong style={{ color: "#d32f2f" }}>Foxaholic does not support search.</strong>
                                        <div style={{ marginTop: "0.5rem" }}>
                                            Please enter a valid Foxaholic novel URL below. This message will not appear again this session.
                                        </div>
                                    </div>
                                )}
                            </div>
                            {/* Second row: input + Scrape button */}
                            <div className="scrape-main-select-input-row">
                                <input
                                    type="text"
                                    placeholder="Enter book title or URL..."
                                    value={searchTerm}
                                    onChange={handleSearchTermChange}
                                />
                                
                                <button
                                    className="scrape-main-scrape-button"
                                    onClick={handleScrape}
                                    disabled={
                                        !searchSuccess ||
                                        ((selectedSite === "foxaholic" || selectedSite === "novelbin") && !cloudflareCookie) ||
                                        (selectedSite === "foxaholic" && (!isFoxaholicUrl(searchTerm) || !!foxaholicUrlError))
                                    }
                                >
                                    Scrape
                                </button>
                            </div>
                            {(selectedSite === "foxaholic" || selectedSite === "novelbin") && (
                            <div className="scrape-main-cloudflare-input-row">
                                <input
                                    type="text"
                                    placeholder="Enter Cloudflare cookie..."
                                    value={cloudflareCookie}
                                    onChange={e => setCloudflareCookie(e.target.value)}
                                    style={{ width: '100%' }}
                                />
                            </div>
                        )}
                        {/* This needs to be moved.*/}
                        {foxaholicUrlError && (
                            <div style={{ color: "#d32f2f", marginTop: "0.5rem" }}>{foxaholicUrlError}</div>
                        )}
                        </div>
                    </div>
                {/* Right Panel: Chapter List */}
                    <div className="scrape-right-panel">
                        <div className="scrape-right-chapter-list-panel">
                            <h2>Chapters</h2>
                            {book && Array.isArray(book.chapterTitles) ? (
                                <ul style={{ listStyle: "none", padding: 0, maxHeight: 500, overflowY: 'auto' }}>
                                {book.chapterTitles.map((chapter, idx) => (
                                    <li key={idx}>
                                        <input
                                            type="checkbox"
                                            checked={checkedChapters[idx] || false}
                                            onChange={() => {
                                                const updated = [...checkedChapters];
                                                updated[idx] = !updated[idx];
                                                setCheckedChapters(updated);
                                            }}
                                        />
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
