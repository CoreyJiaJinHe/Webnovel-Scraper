import React from 'react';


const ImportBookListItem = ({ bookLabel, idx, displayLabel, onImport }) => (
  <li className="import-book-list-item"
    key={bookLabel || idx}
    
  >
    <span style={{ fontSize: "0.95rem", flex: 1, marginRight: "1rem", wordBreak: "break-word" }}>
      {displayLabel}
    </span>
    <button className="import-book-list-item-button"
          onClick={() => onImport(bookLabel)}
    >
      Import
    </button>
  </li>
);


export default ImportBookListItem