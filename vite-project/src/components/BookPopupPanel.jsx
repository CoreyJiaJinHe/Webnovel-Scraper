import React from "react";

const BookPopup = ({ book, onClose }) => {
    if (!book) return null;

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
            onClick={onClose}
        >
            <div
                className="bg-white rounded-lg shadow-lg p-8 max-w-lg w-full relative flex flex-col"
                style={{ maxHeight: "80vh", minWidth: "320px", overflow: "hidden" }}
                onClick={e => e.stopPropagation()}
            >
                <button
                    className="absolute top-2 right-2 text-gray-500 hover:text-gray-800 text-2xl"
                    onClick={onClose}
                    aria-label="Close"
                >
                    &times;
                </button>
                <h2 className="text-2xl font-bold mb-4 text-black">{book[1]}</h2>
                <div className="mb-2 text-gray-700">
                    <strong>Latest Chapter:</strong> {book[3]}
                </div>
                <div className="mb-2 text-gray-700">
                    <strong>Last Scraped:</strong> {book[2]}
                </div>
                <div
                    className="mt-4 text-gray-800 whitespace-pre-line overflow-y-auto flex-1"
                    style={{ maxHeight: "40vh" }}
                >
                    {book[4]}
                </div>
                <button
                    className="mt-6 bg-blue-600 hover:bg-blue-800 text-white font-bold py-2 px-4 rounded"
                    onClick={onClose}
                >
                    Close
                </button>
            </div>
        </div>
    );
};

export default BookPopup;