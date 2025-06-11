import React, { useState } from "react";
const BookPopup = ({ book, onClose,isLoggedIn, addToFollowList ,removeFromFollowList}) => {
    if (!book) return null;
    const [isFollowed, setIsFollowed] = useState(false);

    
    const handleFollow = () => {
        addToFollowList(book[0]);
        setIsFollowed(true);
    };

    const handleUnfollow = () => {
        removeFromFollowList(book[0]);
        setIsFollowed(false);
    };


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
                {isLoggedIn && (
                    isFollowed ? (
                        <button className="book-big-follow-button"  style={{background: "#ef4444", // Red for unfollow 
                            }}onClick={handleUnfollow}>
                            Unfollow Book
                        </button>
                    ) : (
                        <button className="book-big-follow-button" style={{background: "#10b981", // Green for unfollow 
                            }}onClick={handleFollow}>
                            Follow Book
                        </button>
                    )
                )}
                <button className="book-big-close-button" onClick={onClose}>
                    Close
                </button>
            </div>
        </div>
    );
};

export default BookPopup;