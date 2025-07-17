import React, { useState, useEffect, useRef } from 'react';
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

    const [lastCheckedIndex, setLastCheckedIndex] = useState(null);

    const [customBookName, setCustomBookName] = useState('');

    const [showFoxaholicPopup, setShowFoxaholicPopup] = useState(() => {
    return !getSessionCookie('seenFoxaholicPopup');
    });


    // Foxaholic URL validation
    function isFoxaholicUrl(url) {
        // Accepts URLs like https://foxaholic.com/novel/...
        return /^https?:\/\/(www\.)?foxaholic\.com\/.+/.test(url.trim());
    }

    const [searchConditions, setSearchConditions] = useState({});

    

    const royalroadSortOptions = [
        { key: "popularity", label: "Popularity" },
        { key: "relevance", label: "Relevance" }
    ];

    const spacebattlesSortOptions = [
        { key: "sort_title", label: "Title" },
        { key: "sort_reply_count", label: "Reply Count" },
        { key: "sort_view_count", label: "View Count" },
        { key: "sort_last_threadmark", label: "Last Threadmark" },
        { key: "sort_watchers", label: "Watchers" }
    ];
    //TODO: FINISH THIS
    //Implement search conditions

    
    const enforceTimer = useRef(null);
    const pendingConditions = useRef(null);

    // Debounced enforcement for word count min/max
    function enforceWordCountLimits(conditions) {
        const updated = { ...conditions };
        const min = Math.max(0, parseInt(updated["word_count_min"] || "0", 10));
        let max = parseInt(updated["word_count_max"] || "0", 10);

        updated["word_count_min"] = min.toString();
        if (max < min) {
            updated["word_count_max"] = min.toString();
        } else {
            updated["word_count_max"] = max.toString();
        }
        setSearchConditions(updated);
    }

    function handleConditionChange(key, value) {
        setSearchConditions(prev => {
            const updated = { ...prev };

            if (key === "word_count_min") {
                updated["word_count_min"] = value;
            } else if (key === "word_count_max") {
                updated["word_count_max"] = value;
            } else if (key === "threadmark_status") {
                if (value) {
                    updated[key] = value;
                } else {
                    delete updated[key];
                }
            } else {
                if (value === true) {
                    updated[key] = true;
                } else {
                    delete updated[key];
                }
            }

            // Debounce enforcement for word count min/max
            if (key === "word_count_min" || key === "word_count_max") {
                pendingConditions.current = updated;
                if (enforceTimer.current) clearTimeout(enforceTimer.current);
                enforceTimer.current = setTimeout(() => {
                    enforceWordCountLimits(pendingConditions.current);
                    enforceTimer.current = null;
                }, 3000);
            }

            return updated;
        });
    }


    function handleSortChange(site, value) {
        setSearchConditions(prev => {
            const updated = { ...prev };
            // Remove all sort_ and royalroad keys
            if (site === "royalroad") {
                delete updated["popularity"];
                delete updated["relevance"];
                if (value) updated[value] = true;
            } else if (site === "forums.spacebattles") {
                Object.keys(updated).forEach(k => {
                    if (k.startsWith("sort_")) delete updated[k];
                });
                if (value) updated[value] = true;
            }
            return updated;
        });
    }

    const incrementTimers = useRef({});
    
    function startRapidChange(key, delta) {
        stopRapidChange(key);

        function change() {
            setSearchConditions(prev => {
                const updated = { ...prev };
                if (key === "word_count_min") {
                    let min = parseInt(updated["word_count_min"] || "0", 10);
                    let next = min + delta;
                    if (next < 0) next = 0;
                    updated["word_count_min"] = next.toString();
                } else if (key === "word_count_max") {
                    let max = parseInt(updated["word_count_max"] || "0", 10);
                    let next = max + delta;
                    updated["word_count_max"] = next.toString();
                }
                // Debounce enforcement for word count min/max
                pendingConditions.current = updated;
                if (enforceTimer.current) clearTimeout(enforceTimer.current);
                enforceTimer.current = setTimeout(() => {
                    enforceWordCountLimits(pendingConditions.current);
                    enforceTimer.current = null;
                }, 3000);
                return updated;
            });
        }

        change();
        incrementTimers.current[key] = setInterval(change, 80);
    }

    function stopRapidChange(key) {
        if (incrementTimers.current[key]) {
            clearInterval(incrementTimers.current[key]);
            incrementTimers.current[key] = null;
        }
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
                    bookID: book.bookID,
                    bookAuthor: book.bookAuthor,
                    bookTitle: book.bookTitle,
                    selectedSite: selectedSite,
                    cookie: cloudflareCookie,
                    book_chapter_urls: selectedUrls
                },{responseType:'blob'},{
                withCredentials: true
            });
            if (response.statusText === "OK" && response.data.Response !== "False") {
                let fileName=book.bookTitle+".epub";
                if (customBookName.trim() !== '') {
                    fileName = customBookName + ".epub";
                }
                const file = await new Blob([response.data],{type:response.data.type})
                const url = window.URL.createObjectURL(file);
                const link = document.createElement('a')
                link.href=url;
                link.setAttribute('download',fileName)

                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
            if (response.statusText !== "OK") {
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

    //TODO: Implement shift click functionality to select all markdown boxes for chapters.
    //TODO: Implemention a button to select all chapters for scraping.
    //TODO: Implement a field to change the name of the file, if none provided, default to bookTitle.
    // Checkbox handler with shift-click support


    
    function handleChapterCheckboxChange(idx, e) {
        
        const shiftKey = window.event ? window.event.shiftKey : false;
        let updated = [...checkedChapters];
        if (shiftKey && lastCheckedIndex !== null) {
            const [start, end] = [lastCheckedIndex, idx].sort((a, b) => a - b);
            for (let i = start; i <= end; i++) {
                updated[i] = true;
            }
        } else {
            updated[idx] = !updated[idx];
        }
        setCheckedChapters(updated);
        setLastCheckedIndex(idx);
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
            
            <div className="book-scraper-background">
            <div className="book-scraper-container" >
                {/* Left Panel (keep default/dark background) */}
                <div className="book-scraper-left-panel">
                    <div className="book-scraper-book-details-panel">
                        <h3 style={{ marginTop: 0 }}>Book Details</h3>
                        {book ? (
                            <ul style={{ listStyle: "none", padding: 0 }}>
                                <li><strong>Title:</strong> {book.bookTitle}</li>
                                <li><strong>Author:</strong> {book.bookAuthor}</li>
                                <li><strong>Description:</strong>
                                    <div className="book-scraper-book-details-panel-description">
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
                    <div className="book-scraper-container-main-content">
                        <div className="book-scraper-main-search-card">
                            {/* Top row: dropdown + Search button */}
                            <div className="book-scraper-main-dropdown-row" style={{ position: "relative" }}>
                                <select className="book-scraper-main-search-select-dropdown"
                                    value={selectedSite}
                                    onChange={e => {
                                        setSelectedSite(e.target.value);
                                        setBook(null);
                                        setSearchSuccess(false);
                                        setSearchConditions({}); // Reset all search conditions when site changes
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
                                    className="book-scraper-main-search-button"
                                    onClick={handleSearch}
                                    disabled={selectedSite === "foxaholic"}>
                                    Search
                                </button>
                                {/* Foxaholic popup */}
                                {selectedSite === "foxaholic" && showFoxaholicPopup && (
                                    <div className="book-scraper-foxaholic-popup">
                                        <button className="book-scraper-foxaholic-popup-close-button"
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
                            <div className="book-scraper-main-select-input-row">
                                <input
                                    type="text"
                                    placeholder="Enter book title or URL..."
                                    value={searchTerm}
                                    onChange={handleSearchTermChange}
                                />
                                
                                <button
                                    className="book-scraper-main-scrape-button"
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
                            <div className="book-scraper-main-cloudflare-input-row">
                                <input
                                    type="text"
                                    placeholder="Enter Cloudflare cookie..."
                                    value={cloudflareCookie}
                                    onChange={e => setCloudflareCookie(e.target.value)}
                                    style={{ width: '100%' }}
                                />
                            </div>
                        )}
                        {foxaholicUrlError && (
                            <div style={{ color: "#d32f2f", marginTop: "0.5rem" }}>{foxaholicUrlError}</div>
                        )}
                        </div>
                        <div className="book-scraper-main-search-card" style={{ marginTop: "1rem", color:"black" }}>
                            <h2>Change File Name</h2>
                            <p>Current File Name: {(book && book.bookTitle) ? book.bookTitle : "Does not exist"}</p>
                            <input type ="text" placeholder="Optional: Change file name"
                                value={customBookName}
                                style={{ width: '100%', marginBottom: '0.5rem', marginTop: '0.5rem' }}
                                onChange={e => setCustomBookName(e.target.value)}
                            />
                        </div>
                        {/* New card panel for search conditions */}
                        <div className="book-scraper-main-search-card" style={{ marginTop: "1rem", color: "black" }}>
                            <h2>Search Options</h2>
                            {selectedSite === "royalroad" && (
                                <div>
                                    <label style={{ display: "block", marginBottom: "0.5rem" }}>
                                        Sort By:&nbsp;
                                        <select
                                            value={
                                                royalroadSortOptions.find(opt => searchConditions[opt.key])?.key || ""
                                            }
                                            onChange={e => handleSortChange("royalroad", e.target.value)}
                                            style={{ marginRight: "0.5rem" }}
                                        >
                                            <option value="">Select...</option>
                                            {royalroadSortOptions.map(opt => (
                                                <option key={opt.key} value={opt.key}>{opt.label}</option>
                                            ))}
                                        </select>
                                    </label>
                                </div>
                            )}
                            {selectedSite === "forums.spacebattles" && (
                                <div>
                                    <label style={{ display: "block", marginBottom: "0.5rem" }}>
                                        Sort By:&nbsp;
                                        <select
                                            value={
                                                spacebattlesSortOptions.find(opt => searchConditions[opt.key])?.key || ""
                                            }
                                            onChange={e => handleSortChange("forums.spacebattles", e.target.value)}
                                            style={{ marginRight: "0.5rem" }}
                                        >
                                            <option value="">Select...</option>
                                            {spacebattlesSortOptions.map(opt => (
                                                <option key={opt.key} value={opt.key}>{opt.label}</option>
                                            ))}
                                        </select>
                                    </label>
                                    {/* Word Count Range */}
                                    <label style={{ display: "block", marginBottom: "0.5rem" }}>
                                        Word Count:&nbsp;
                                        <span style={{ marginRight: "0.3rem" }}>Min</span>
                                        <div style={{ display: "inline-flex", alignItems: "center", marginRight: "1rem" }}>
                                            <input
                                                type="number"
                                                min={0}
                                                value={searchConditions["word_count_min"] || ""}
                                                onChange={e => handleConditionChange("word_count_min", e.target.value)}
                                                style={{
                                                    width: "80px",
                                                    outline: "2px solid #b3b3b3",
                                                    border: "1px solid #b3b3b3",
                                                    borderRadius: "4px",
                                                    background: "white",
                                                    WebkitAppearance: 'textfield',
                                                    MozAppearance: 'textfield',
                                                    appearance: 'textfield',
                                                }}
                                            />
                                            <button
                                                type="button"
                                                style={{maxWidtdh:"50px", marginLeft: "4px", padding: "2px 8px", background: "white", color: "black", border: "1px solid #b3b3b3", borderRadius: "4px" }}
                                                onMouseDown={() => startRapidChange("word_count_min", 1)}
                                                onMouseUp={() => stopRapidChange("word_count_min")}
                                                onMouseLeave={() => stopRapidChange("word_count_min")}
                                                onTouchStart={() => startRapidChange("word_count_min", 1)}
                                                onTouchEnd={() => stopRapidChange("word_count_min")}
                                            >+</button>
                                            <button
                                                type="button"
                                                style={{maxWidtdh:"50px", marginLeft: "2px", padding: "2px 8px", background: "white", color: "black", border: "1px solid #b3b3b3", borderRadius: "4px" }}
                                                onMouseDown={() => startRapidChange("word_count_min", -1)}
                                                onMouseUp={() => stopRapidChange("word_count_min")}
                                                onMouseLeave={() => stopRapidChange("word_count_min")}
                                                onTouchStart={() => startRapidChange("word_count_min", -1)}
                                                onTouchEnd={() => stopRapidChange("word_count_min")}
                                                disabled={parseInt(searchConditions["word_count_min"] || "0", 10) <= 0}
                                            >-</button>
                                        </div>
                                        <span style={{ marginRight: "0.3rem" }}>Max</span>
                                        <div style={{ display: "inline-flex", alignItems: "center" }}>
                                            <input
                                                type="number"
                                                min={searchConditions["word_count_min"] || 0}
                                                value={searchConditions["word_count_max"] || ""}
                                                onChange={e => handleConditionChange("word_count_max", e.target.value)}
                                                style={{
                                                    width: "80px",
                                                    outline: "2px solid #b3b3b3",
                                                    border: "1px solid #b3b3b3",
                                                    borderRadius: "4px",
                                                    background: "white",
                                                    
                                                    WebkitAppearance: 'textfield',
                                                    MozAppearance: 'textfield',
                                                    appearance: 'textfield',
                                                }}
                                            />
                                            <button
                                                type="button"
                                                style={{maxWidtdh:"50px", marginLeft: "4px", padding: "2px 8px", background: "white", color: "black", border: "1px solid #b3b3b3", borderRadius: "4px" }}
                                                onMouseDown={() => startRapidChange("word_count_max", 1)}
                                                onMouseUp={() => stopRapidChange("word_count_max")}
                                                onMouseLeave={() => stopRapidChange("word_count_max")}
                                                onTouchStart={() => startRapidChange("word_count_max", 1)}
                                                onTouchEnd={() => stopRapidChange("word_count_max")}
                                            >+</button>
                                            <button
                                                type="button"
                                                style={{maxWidtdh:"50px", marginLeft: "2px", padding: "2px 8px", background: "white", color: "black", border: "1px solid #b3b3b3", borderRadius: "4px" }}
                                                onMouseDown={() => startRapidChange("word_count_max", -1)}
                                                onMouseUp={() => stopRapidChange("word_count_max")}
                                                onMouseLeave={() => stopRapidChange("word_count_max")}
                                                onTouchStart={() => startRapidChange("word_count_max", -1)}
                                                onTouchEnd={() => stopRapidChange("word_count_max")}
                                                disabled={parseInt(searchConditions["word_count_max"] || "0", 10) <= parseInt(searchConditions["word_count_min"] || "0", 10)}
                                            >-</button>
                                        </div>
                                    </label>
                                    {/* Threadmark Status dropdown */}
                                    <label style={{ display: "block", marginBottom: "0.5rem" }}>
                                        Threadmark Status:&nbsp;
                                        <select
                                            value={searchConditions["threadmark_status"] || ""}
                                            onChange={e => handleConditionChange("threadmark_status", e.target.value !== "" ? e.target.value : undefined)}
                                            style={{ marginRight: "0.5rem" }}
                                        >
                                            <option value="">Select...</option>
                                            <option value="completed">Completed</option>
                                            <option value="ongoing">Ongoing</option>
                                            <option value="hiatus">Hiatus</option>
                                            <option value="dropped">Dropped</option>
                                        </select>
                                    </label>
                                    {/* Direction toggle */}
                                    <label style={{ display: "block", marginBottom: "0.5rem" }}>
                                        Direction:&nbsp;
                                        <select
                                            value={searchConditions["direction"] === true ? "desc" : "asc"}
                                            onChange={e => handleConditionChange("direction", e.target.value === "desc")}
                                            style={{ marginRight: "0.5rem" }}
                                        >
                                            <option value="asc">Ascending</option>
                                            <option value="desc">Descending</option>
                                        </select>
                                    </label>
                                </div>
                            )}
                        </div>
                        </div>
                {/* Right Panel: Chapter List */}
                    <div className="book-scraper-right-panel">
                        <div className="book-scraper-right-chapter-list-panel">
                            <h2 style={{ display: "inline-block", marginRight: "1rem" }}>Chapters</h2>
                            <button
                                type="button"
                                style={{ fontSize: "1rem", padding: "0.3rem 0.8rem", marginBottom: "0.5rem", color: 'white' }}
                                onClick={() => {
                                    if (book && Array.isArray(book.chapterTitles)) {
                                        const allChecked = checkedChapters.every(Boolean);
                                        setCheckedChapters(new Array(book.chapterTitles.length).fill(!allChecked));
                                    }
                                }}
                            >
                                {book && Array.isArray(book.chapterTitles) && checkedChapters.every(Boolean) ? "Unselect All" : "Select All"}
                            </button>
                            {book && Array.isArray(book.chapterTitles) ? (
                                <ul style={{ listStyle: "none", padding: 0, maxHeight: 500, overflowY: 'auto' }}>
                                {book.chapterTitles.map((chapter, idx) => (
                                    <li key={idx}>
                                        <input
                                            type="checkbox"
                                            checked={checkedChapters[idx] || false}
                                            onChange={e => handleChapterCheckboxChange(idx, e)}
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
