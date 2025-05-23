import React from 'react';
import axios from "axios";
import "../BookCard.css"

async function downloadBook(id,getBook){
        try{
            //console.log("This is the ID:" +id)
            getBook(id)
        }
        catch(error){
            console.log(error.message)
        }
    }


function bookCard({data:{_id, bookName,lastScraped,latestChapter},getBook}){
    return(
        <div className="book-card">
            <div className="book-card-content">
                <h3>{bookName ? bookName:"Failed to get"}</h3>
                <div>
                    <p>Latest scraped chapter: {latestChapter ? latestChapter:"?" }</p>
                    <p>Last scraped: {lastScraped? lastScraped:"?"}</p>
                </div>
                <button className="download-button" onClick={()=>downloadBook(_id,getBook)}>Download</button>

            </div>

        </div>

    )


}
export default bookCard;