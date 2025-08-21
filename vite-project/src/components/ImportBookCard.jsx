import React from "react";

const ImportBookCard = ({ book }) => (
  <div className="import-book-card"
    
  >
    <div><strong>ID:</strong> {book.bookID}</div>
    <div><strong>Name:</strong> {book.bookName}</div>
    <div><strong>Author:</strong> {book.author || book.bookAuthor}</div>
    <div>
      <strong>Edited:</strong>{" "}
      {book.edited !== undefined
        ? book.edited
          ? <span style={{ color: "green" }}>Yes</span>
          : <span style={{ color: "red" }}>No</span>
        : "Unknown"}
    </div>
  </div>
);

export default ImportBookCard;