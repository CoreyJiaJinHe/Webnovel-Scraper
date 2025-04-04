import React from 'react';
import axios from "axios";
import Swal from "sweetalert2";

//This fixes INVALID_URL error with Axios
const API_URL="http://localhost:8080/api";
const api= axios.create({baseURL: API_URL});

const getBook = async (id,directory)=>{
        try{
            //console.log("This is the ID:" +id)
            const response=await axios.delete(`${API_URL}/todos/${id}`)
            
        }
        catch(error){
            console.log(error.message)
        }
    }


const bookCard=({data:{_id, bookName,latestChapter,lastScraped}})=>{
    return(
        <div className="todo-card" class="mt-5 mb-5 border-solid border-black border-2 rounded-lg">
            <div className="st-4 p-2">
                



            </div>

        </div>

    )


}
export default bookCard;