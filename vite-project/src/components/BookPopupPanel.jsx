import React from "react";

const BookPopup = ({ book, onClose }) => {
    if (!book) return null;

    // _id: book[0],
    // bookName: book[1],
    // bookAuthor: book[2],
    // description: book[3],
    // lastScraped: book[5],
    // latestChapter: book[6],
    return (
        <div className="pop-up-overlay" onClick={onClose}>
            <div className="pop-up-content" onClick={e => e.stopPropagation()}>
                <button className="top-right-close-button" onClick={onClose} aria-label="Close">
                    &times;
                </button>
                <h2 className="pop-up-book-title">{book[1]}</h2>
                <div className="pop-up-book-bold-text">
                    <strong>Author:</strong> {book[2]}
                </div>
                <div className="pop-up-book-bold-text">
                    <strong>Latest Chapter:</strong> {book[6]}
                </div>
                <div className="pop-up-book-bold-text">
                    <strong>Last Scraped:</strong> {book[5]}
                </div>
                <div className="pop-up-book-description" style={{ maxHeight: "80vh" }}>
                    {book[3] ? book[3] : "No description available."}
                </div>
                <button className="book-big-close-button" onClick={onClose}>
                    Close
                </button>
            </div>
        </div>
    );
};

export default BookPopup;