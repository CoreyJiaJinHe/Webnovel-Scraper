import React from 'react';
import axios from "axios";
//import "../BookCard.css"


function descriptiveBookCard({data:{_id, bookName,bookAuthor,description,lastScraped,latestChapter}}){
    return(
        <div className="descriptive-BookCard">
            <div className="descriptive-BookCard-content">
                <h3>{bookName ? bookName:"Failed to get"}</h3>
                <div>
                    <p>Latest scraped chapter: {latestChapter ? latestChapter:"?" }</p>
                    <p>Last scraped: {lastScraped? lastScraped:"?"}</p>
                </div>

            </div>

        </div>

    )


}
export default descriptiveBookCard;