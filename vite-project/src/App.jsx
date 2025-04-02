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
      const response=await axios.get(`${API_URL}/getFiles`,{
        headers: {
          'Content-Type': 'application/epub'
        }
      }
      )
      console.log(response)
      if (response.statusText!=="OK"){
        console.log("Error getting files")
      }
      else if (response.Response==="False"){
        console.log("Error getting files")
      }
      const file = await new Blob([response])
      const url = window.URL.createObjectURL(file);
      const link = document.createElement('a')
      link.href=url;
      link.setAttribute('download','FileName.epub')

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
