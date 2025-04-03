import { useState, useEffect } from 'react'
import './App.css'
//TODO: Build page. Build button to connect to backend server.py to retrieve file to download.

import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });
function App() {

  const [doOnce, setDoOnce] = useState(false);

  useEffect(()=>{
    if (!doOnce){
      setDoOnce(true);
      getFiles();
    }

  })

  async function getFiles(){
    try{
      const response=await axios.get(`${API_URL}/getFiles`,{responseType:'blob',withCredentials: true})
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



  return (
    <>
      <div>
        <h1>Rudimentary File Hosting</h1>
        <p>Get your files below</p>

        <button onClick={getFiles}>Get File</button>

        </div>
    </>
  )
}

export default App
