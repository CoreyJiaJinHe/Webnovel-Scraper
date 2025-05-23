import { useState, useEffect } from 'react'
import BookCard from '../components/BookCard.jsx'
import NavBar from '../components/NavBar'

import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });


function DownloadPage() {

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

    async function getFiles()
    {
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

        //For files. Get response type as blob > Get Data from Blob > Create Object Url > 
        //Create Element, Give Element HREF, Add Element to Page
        
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
        //console.log(dataY)
        setBookList(dataY)
        //console.log(dataX)
    }
    catch(error){
        console.log(error)
    }
    }


    const renderBookSections = () => {
    // Iterate over the bookList, where each entry is [websiteHost, booksArray]
    console.log(bookList)
    return bookList.map((entry, index) => {
        const websiteHost = entry[0]; // The website host
        const booksArray = entry[1]; // Array of books for this host
        if (!Array.isArray(booksArray)) {
        console.warn(`Invalid booksArray for websiteHost: ${websiteHost}`);
        return null; // Skip rendering this section
        }
        return (
        <section key={index} className="book-section mb-8">
            {/* Section Header */}
            <h2 className="text-2xl font-bold mb-4">{websiteHost}</h2>
            {/* Grid of BookCards */}
            <article className="grid grid-cols-4 gap-6 rounded-lg">
            {booksArray.map((book) => (
                <BookCard
                key={book[0]} // Assuming book[0] is the bookID
                data={{
                    _id: book[0], // bookID
                    bookName: book[1], // bookName
                    lastScraped: book[2], // lastScraped date
                    latestChapter: book[3], // latestChapter
                }}
                getBook={grabBook}
                />
            ))}
            </article>
        </section>
        );
    });
    };

    function grabBook(id){
    getBook(id)
    }
    //DONE: Make categories for saved books. One for royalroad, one for novelbin, one for foxaholic, etc.
    return (
    <>
    <NavBar/>
    <div className='h-full mx-50 w-[calc(100%-100)] max-w-full text-white'>
        <header className='flex flex-col gap-10 h-full mx-50 text-center '>
            <h1 className='text-4xl mt-10'>Rudimentary File Hosting</h1>
            <p>Get your files below</p>
            <button onClick={getFiles}>Get File</button>
        </header>
        <main className='mt-20'>
            {renderBookSections()}
        </main>
    </div>
    </>
    )
    }
export default DownloadPage;
