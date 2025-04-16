import React from 'react';
import axios from "axios";
//import Swal from "sweetalert2";

//This fixes INVALID_URL error with Axios
const API_URL="http://localhost:8000/api";
const api= axios.create({baseURL: API_URL});

async function downloadBook(id,getBook){
        try{
            console.log("This is the ID:" +id)
            getBook(id)
        }
        catch(error){
            console.log(error.message)
        }
    }


function bookCard({data:{_id, bookName,lastScraped,latestChapter},getBook}){
    return(
        <div className="todo-card" class="grid flex max-w-96 mt-5 mb-5 border-solid border-black border-2 rounded-lg">
            <div className="st-4 p-2">
                <h3>{bookName ? bookName:"Failed to get"}</h3>
                <div>
                    <p>Latest scraped chapter:{latestChapter ? latestChapter:"?" }</p>
                </div>
                <button onClick={()=>downloadBook(_id,getBook)}>Download</button>

            </div>

        </div>

    )


}
export default bookCard;