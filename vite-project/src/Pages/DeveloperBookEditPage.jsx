import React, { useState, useRef, useEffect } from 'react';
import NavBar from '../components/NavBar.jsx';
import axios from "axios";

const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });

const existingBookTitles = [
    "Harry Potter and the Methods of Rationality",
    "Worm",
    "Mother of Learning",
    "The Wandering Inn",
    "The New Normal",
    "A Practical Guide to Evil",
    "The Iron Teeth",
    "The Perfect Run",
    "The Last Angel",
    "The Zombie Knight Saga"
];

function DeveloperBookEditPage() {
    const [searchTerm, setSearchTerm] = useState('');
    const [recommendations, setRecommendations] = useState([]);
    const [showDropdown, setShowDropdown] = useState(false);
    const [book, setBook] = useState(null);
    const [searchError, setSearchError] = useState('');
    const [orderOfContents, setOrderOfContents] = useState([]);
    const [checkedChapters, setCheckedChapters] = useState([]);
    const [draggedIndex, setDraggedIndex] = useState(null);

    const [lastCheckedIndex, setLastCheckedIndex] = useState(null);

    const [dropTargetIndex, setDropTargetIndex] = useState(null);
    const [existingBookTitles,setExistingBookTitles]=useState([]);

    const [rawOrderOfContents, setRawOrderOfContents] = useState([]);
    const [orderOfContentsTitles, setOrderOfContentsTitles] = useState([]);

    const inputRef = useRef();
    const searchTimeout = useRef();

//TODO: CLEAN THIS WHOLE FUCKING PAGE UP.

    useEffect(() => {
        // Fetch existing book titles from the API on page load
        async function fetchExistingBooks() {
            try {
                const response = await axios.get(`${API_URL}/allBooks`, { withCredentials: true });
                if (response.status === 200 && response.data) {
                    let allTitles = [];

                    // Loop through each site
                    for (let i = 0; i < response.data.length; i++) {
                        const siteArray = response.data[i];
                        // siteArray[0] is the site host (string)
                        // siteArray[1] is the array of books for this site
                        const booksArray = siteArray[1];

                        // Loop through each book in this site's books array
                        for (let j = 0; j < booksArray.length; j++) {
                            const book = booksArray[j];
                            // book[1] is the title
                            const title = book[1];
                            allTitles.push(title);
                        }
                    }
                    setExistingBookTitles(allTitles);
                    // Optionally, fetch recommendations for empty searchTerm on load:
                    // setRecommendations(titles);
                    console.log("Extracted book titles:", allTitles);
                }
            } catch (error) {
                console.error("Error fetching existing books:", error);
            }
        }
        fetchExistingBooks();
    }, []); // <-- runs once on page load

    
    function fetchRecommendations(value) {
        if (!value) {
            setRecommendations([]);
            setShowDropdown(false);
            return;
        }
        const filtered = existingBookTitles.filter(title =>
            title.toLowerCase().includes(value.toLowerCase())
        );
        setRecommendations(filtered);
        setShowDropdown(filtered.length > 0);
    }

    function extractChapterTitles(orderOfContents) {
    // orderOfContents: array of strings like "1618925;url;./books/raw/Dread Mage/Dread Mage - 1618925 - Chapter 14 - Magic Schmagic.html"
    return orderOfContents.map(item => {
        const parts = item.split(';');
        // Trim whitespace/newlines from the file path
        let filePath = parts[parts.length - 1].trim();
        // Remove ".html" from the end if present
        filePath=filePath.replace(/\.html$/, '');
        // Find all ' - ' positions
        const dashPositions = [];
        let idx = filePath.indexOf(' - ');
        while (idx !== -1) {
            dashPositions.push(idx);
            idx = filePath.indexOf(' - ', idx + 1);
        }
        let chapterTitle;
        if (dashPositions.length >= 2) {
            const secondLastIdx = dashPositions[dashPositions.length - 2];
            chapterTitle = filePath.substring(secondLastIdx + 3);
        } else if (dashPositions.length === 1) {
            chapterTitle = filePath.substring(dashPositions[0] + 3);
        } else {
            chapterTitle = filePath;
        }
        return chapterTitle;
    });
}


    function logOrderOfContents() {
        console.log("Current order_of_contents:", orderOfContentsTitles);
        console.log("Current raw order_of_contents:", rawOrderOfContents);
    }

    // Search for the book (exactly as typed)
    async function handleSearch(query) {
        setSearchError("")
        try {
            const response = await axios.get(`${API_URL}/retrieve_book`, {
                params: { bookTitle: query },
                withCredentials: true
            });
            console.log(response.data)
            if (response.status === 200 && response.data) {

                setBook(response.data[0]); // book object
                // Process order_of_contents to extract chapter titles
                setRawOrderOfContents(response.data[1] || []);
                const chapterTitles = extractChapterTitles(response.data[1] || []);
                console.log(chapterTitles)
                setOrderOfContentsTitles(chapterTitles);
                setCheckedChapters(new Array(chapterTitles.length).fill(false));
            
            } else {
                setSearchError("Book not found.");
            }
        } catch {
            console.log("Exception occurred")
            setSearchError("Book not found.");
        }
        if (searchError){
            console.log(`This is the error ${searchError}`)
            }
    }

    // Handle input change and fetch recommendations
    const handleInputChange = e => {
        const value = e.target.value;    
        setSearchTerm(value); // <-- This makes the input controlled and visible
        fetchRecommendations(value);
    };

    // Handle selecting a recommendation
    const handleRecommendationClick = rec => {
        setSearchTerm(rec);
        setShowDropdown(false);
        inputRef.current.blur();
    };

    // Handle input blur (hide dropdown after a short delay to allow click)
    const handleInputBlur = () => {
        setTimeout(() => setShowDropdown(false), 150);
    };

    // Handle input focus (show dropdown if recommendations exist)
    const handleInputFocus = () => {
        if (recommendations.length > 0) setShowDropdown(true);
    };

    // Checkbox handler
    const handleCheckbox = (idx, e) => {
        // Use window.event to check for shiftKey on checkbox change
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
    };

    // Drag and drop handlers
    const handleDragStart = idx => {
            setDraggedIndex(idx);
    };

    const handleDragOver = idx => {
    if (draggedIndex === null || draggedIndex === idx) return;
    setDropTargetIndex(idx); // Just record the drop target
};

    const handleDragEnd = () => {
    if (draggedIndex === null || dropTargetIndex === null || draggedIndex === dropTargetIndex) {
        setDraggedIndex(null);
        setDropTargetIndex(null);
        return;
    }

    // Find all checked indices
    const selectedIndices = checkedChapters
        .map((checked, i) => checked ? i : -1)
        .filter(i => i !== -1);

    // If the dragged index is not checked, treat as single drag
    const draggingIndices = checkedChapters[draggedIndex] ? selectedIndices : [draggedIndex];

    // Remove all dragging items from arrays
    let updatedTitles = [...orderOfContentsTitles];
    let updatedRaw = [...rawOrderOfContents];
    let updatedChecked = [...checkedChapters];

    // Remove in reverse order to avoid index shift
    const sortedDraggingIndices = [...draggingIndices].sort((a, b) => b - a);
    sortedDraggingIndices.forEach(i => {
        updatedTitles.splice(i, 1);
        updatedRaw.splice(i, 1);
        updatedChecked.splice(i, 1);
    });

    // Insert all dragging items at the new idx
    // If dragging down, adjust idx to account for removals above
    let insertAt = dropTargetIndex;
    draggingIndices.forEach(i => {
        if (i < dropTargetIndex) insertAt--;
    });

    // Insert in original order
    draggingIndices.forEach((i, offset) => {
    updatedTitles.splice(insertAt + offset, 0, orderOfContentsTitles[i]);
    updatedRaw.splice(insertAt + offset, 0, rawOrderOfContents[i]);
    updatedChecked.splice(insertAt + offset, 0, true);
});
    setOrderOfContentsTitles(updatedTitles);
    setRawOrderOfContents(updatedRaw);
    setCheckedChapters(updatedChecked);

    setDraggedIndex(null);
    setDropTargetIndex(null);
};
    // Delete selected chapters
    const handleDelete = () => {
        const updatedTitles = orderOfContentsTitles.filter((_, idx) => !checkedChapters[idx]);
        const updatedRaw = rawOrderOfContents.filter((_, idx) => !checkedChapters[idx]);
        const updatedChecked = checkedChapters.filter((checked, idx) => !checkedChapters[idx]);
        setOrderOfContentsTitles(updatedTitles);
        setRawOrderOfContents(updatedRaw);
        setCheckedChapters(updatedChecked);
        setLastCheckedIndex(null);
    };

    useEffect(() => {
    // This will always log the latest order after any update
    logOrderOfContents();
}, [rawOrderOfContents]);


    return (
        <>
            <NavBar />
            <div className="scrape-background">
                <div className="scrape-container">
                    {/* Left Panel: Book Details */}
                    <div className="scrape-left-panel">
                        <div className="scrape-book-details-panel">
                            <h3 style={{ marginTop: 0 }}>Book Details</h3>
                            {book ? (
                                <ul style={{ listStyle: "none", padding: 0 }}>
                                    <li><strong>Title:</strong> {book["bookName"]}</li>
                                    <li><strong>Author:</strong> {book["bookAuthor"]}</li>
                                    <li><strong>Description:</strong>
                                        <div className="reader-book-details-panel-description">
                                            {book["bookDescription"]}
                                        </div>
                                    </li>
                                    <li><strong>Latest Chapter:</strong> {book["lastChapterTitle"]}</li>
                                </ul>
                            ) : (
                                <p>No book selected.</p>
                            )}
                        </div>
                    </div>
                    {/* Main Content: Fuzzy Search */}
                    <div className="scrape-container-main-content">
                        <div className="scrape-main-search-card">
                            <div className="scrape-main-select-input-row" style={{ position: 'relative' }}>
                                <input
                                    ref={inputRef}
                                    type="text"
                                    placeholder="Enter book title..."
                                    value={searchTerm}
                                    onChange={handleInputChange}
                                    onFocus={handleInputFocus}
                                    onBlur={handleInputBlur}
                                    onKeyDown={e => { if (e.key === 'Enter') handleSearch(searchTerm); }}
                                    autoComplete="off"
                                />
                                <button
                                    className="scrape-main-search-button"
                                    onClick={() => handleSearch(searchTerm)}
                                    style={{ marginLeft: 'auto', marginRight: 20 }}
                                >
                                    Search
                                </button>
                                {/* Dropdown for fuzzy recommendations */}
                                {showDropdown && recommendations.length > 0 && (
                                    <ul
                                        style={{
                                            position: 'absolute',
                                            top: '100%',
                                            left: 0,
                                            right: 0,
                                            background: '#fff',
                                            border: '1px solid #ccc',
                                            zIndex: 10,
                                            listStyle: 'none',
                                            margin: 0,
                                            padding: 0,
                                            maxHeight: 200,
                                            overflowY: 'auto',
                                            color: 'black' // <-- add this
                                        }}
                                    >
                                        {recommendations.map((rec, idx) => (
                                            <li
                                                key={idx}
                                                style={{
                                                    padding: '0.5rem 1rem',
                                                    cursor: 'pointer',
                                                    borderBottom: idx !== recommendations.length - 1 ? '1px solid #eee' : 'none',
                                                    color: 'black' // <-- add this
                                                }}
                                                onMouseDown={() => handleRecommendationClick(rec)}
                                            >
                                                {rec}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                            {searchError && (
                                <div style={{ color: 'red', marginTop: '1rem' }}>{searchError}</div>
                            )}
                        </div>
                    </div>
                    {/* Right Panel: Chapter List */}
                    <div className="scrape-right-panel">
                        <div className="scrape-right-chapter-list-panel">
                            <h2>Chapters</h2>
                            {orderOfContentsTitles.length > 0 ? (
                                <>
                                    <button
                                        onClick={handleDelete}
                                        disabled={!checkedChapters.some(Boolean)}
                                        style={{ marginBottom: '1rem' }}
                                    >
                                        Delete Selected
                                    </button>
                                    <ul style={{ listStyle: "none", padding: 0, maxHeight: 500, overflowY: 'auto' }}>
                                    {orderOfContentsTitles.map((chapter, idx) => (
                                        <li
                                            key={idx}
                                            draggable={checkedChapters[idx]}
                                            onDragStart={() => handleDragStart(idx)}
                                            onDragOver={e => { e.preventDefault(); handleDragOver(idx); }}
                                            onDragEnd={handleDragEnd}
                                            style={{
                                                background: checkedChapters[idx] ? "#e0e7ff" : undefined,
                                                cursor: checkedChapters[idx] ? "grab" : "default"
                                            }}
                                        >
                                            <input
                                            type="checkbox"
                                            checked={checkedChapters[idx] || false}
                                            onChange={e => handleCheckbox(idx, e)}
                                            draggable={false}
                                            style={{ marginRight: 8 }}
                                        />
                                            {chapter}
                                        </li>
                                    ))}
                                </ul>
                                </>
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

export default DeveloperBookEditPage;