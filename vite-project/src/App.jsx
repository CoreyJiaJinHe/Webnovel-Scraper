import { useState, useEffect } from 'react'
import './App.css'
import BookCard from './components/BookCard.jsx'
//TODO: Build page. Build button to connect to backend server.py to retrieve file to download.

import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });
function App() {

  const [doOnce, setDoOnce] = useState(false);
  const [bookList, setBookList]=useState(['']);

  useEffect(()=>{
    if (!doOnce){
      setDoOnce(true);
      populateTable();
//        console.log(bookList)
      }
    })

  useEffect(()=>{
    //getBookCards()
  },[bookList])

  async function getFiles(){
    try{
      const response=await axios.get(`${API_URL}/getFiles`,{responseType:'blob'}) //withCredentials: true
      console.log(response)
      if (response.statusText!=="OK"){
        console.log("Error getting files")
      }
      else if (response.Response==="False"){
        console.log("Error getting files")
      }
      //console.log(response.headers)
      const contentDisposition=response.headers['content-disposition'];
      //console.log(contentDisposition)
      //let contentDispositionx=contentDisposition.split(/;(.+)/)[1].split(/=(.+)/)[1]+".epub";
      //console.log(contentDispositionx)
      const regex=/filename\*?=.*''(.+)/; //Regex to split string between metadata and bookTitle
      const match = contentDisposition.match(regex);
      //console.log(match);
      const bookTitle=match[1];
      //console.log(bookTitle)
      let fileName=bookTitle.replace(/%20|_/g, " ");

      fileName=fileName+".epub";
      //let fileName = contentDisposition.split 
      
      
      //fileName=fileName.replaceAll("\"",'')
      //console.log(fileName)

      //For files
      //Get response type as blob
      //get the data from blob
      //Create objecturl
      //create element, set the element to have href, then add the element to page.
      //console.log(response.headers['filename'])
      
      const file = await new Blob([response.data],{type:response.data.type})
      const url = window.URL.createObjectURL(file);
      const link = document.createElement('a')
      link.href=url;
      link.setAttribute('download',fileName)

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
              
      }
    catch(error){
      console.log(error)
    }
  }

  async function getBook(id)
  {
    try{
      const response=await axios.get(`${API_URL}/getBook`,{headers:{'bookID':{id}},responseType:'blob',withCredentials: true})
      console.log(response)
      if (response.statusText!=="OK"){
        console.log("Error getting files")
      }
      else if (response.Response==="False"){
        console.log("Error getting files")
      }
      const contentDisposition=response.headers['content-disposition'];
      let fileName = contentDisposition.split(/;(.+)/)[1].split(/=(.+)/)[1]+".epub";
      fileName=fileName.replaceAll("\"",'')
      //console.log(fileName)

      //For files
      //Get response type as blob
      //get the data from blob
      //Create objecturl
      //create element, set the element to have href, then add the element to page.
      //console.log(response.headers['filename'])
      
      const file = await new Blob([response.data],{type:response.data.type})
      const url = window.URL.createObjectURL(file);
      const link = document.createElement('a')
      link.href=url;
      link.setAttribute('download',fileName)

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
              
      }
    catch(error){
      console.log(error)
    }
  }

  async function populateTable(){
      try{
      const response = await axios.get(`${API_URL}/allBooks`)
      if (response.statusText!=="OK"){
        console.log("Error getting files")
      }
      else if (response.Response==="False"){
        console.log("Error getting files")
      }

      const dataY=await response.data
      //const dataX=JSON.parse(JSON.stringify(dataY))
      setBookList(dataY)
      //console.log(dataX)
    }
    catch(error){
      console.log(error)
    }
  }
  //dataX.map((book)=>
  //  {
  //    console.log(book)
  //  })
  const getBookCards=()=>{
    console.log(bookList)
    const list=bookList.map((book)=>{
      let newDict={
        bookName:book[1],
        lastScraped:book[2],
        latestChapter:book[3],
        _id:book[0]
      };

      console.log(newDict);
      console.log("Book value mapping");
      return <BookCard key={book[0]} data={newDict} getBook={grabBook}/>;
    })
    
    return <ul class='grid grid-cols-4 gap-6 p-5'>{list}</ul>
  }
  //justify-center items-center text-center
  function grabBook(id){
    getBook(id)
  }
  //Make categories for saved books. One for royalroad, one for novelbin, one for foxaholic, etc.
  return (
    <>
    <div class='h-full mx-50 w-[calc(100%-100)] max-w-full text-white'>
      <div class='flex flex-col gap-10 h-full mx-50 text-center '>
        <h1 class='text-4xl mt-10'>Rudimentary File Hosting</h1>
        <p>Get your files below</p>

        <button onClick={getFiles}>Get File</button>
        

      </div>
      <div>
        {
        getBookCards()
        }
      </div>
    </div>
    </>
  )
}

export default App
