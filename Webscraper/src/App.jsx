import { useState } from 'react'
import axios from "axios";

const API_URL = "http://127.0.0.1:8000"
const api = axios.create({ baseURL: API_URL })


function App() {


  function loadChapterList(url) {
    if (url == null) {
      return
    } else {
      callBackend(url)
    }
  }

//cors issues

  async function callBackend() {
    try {
      const response = await axios.get(`${API_URL}/chapters`, {
        headers: { 'Content-Type': 'application/json' },
        mode: 'cors',
        params: {
          url: pageURL
        }
      }
      )
      if (response.statusText !== "OK") {
        throw new Error("Failed to fetch data")
      }
      if (response.Response === "False") {
        throw new Error(data.Error || "Failed to fetch data")
      }
      const dataY = await response
      const dataX = JSON.parse(JSON.stringify(dataY.data))
      dataX.map(setChapters)
      setChapters(dataX)

    }
    catch (error) {
      console.error(error)
    }
  }

  const [pageURL, setpageURL] = useState('');

  const [chapters, setChapters] = useState([]);
  //onChange={(event) => loadChapterList(event.target.value)

  return (
    <>
      <div class='px-auto h-screen w-screen flex flex-col'>
        <div class='mx-auto inline bg-white p-4 mt-4 rounded-lg shadow-lg'>
          <h1 class='text-black text-2xl font-bold'>Web Scraper</h1>
          <div class="pt-10">
            <div class="">
              <input className="text-black border-solid border-black border-2 mr-10"
                
                onKeyDown={(event) => {
                  if (event.key == 'Enter') {
                    setpageURL(event.target.value);
                    //handleKeyPress(event.key);
                  }
                }}
                type="text"
                value={pageURL}
                placeholder="Search for Page" />

              <button className="" onClick={loadChapterList(pageURL)}>Search</button>
            </div>
          </div>
          <div className="all-chapters" class="mt-10 max-h-100 overflow-scroll overflow-x-hidden">


          </div>


        </div>
      </div>
    </>
  )
}

export default App
