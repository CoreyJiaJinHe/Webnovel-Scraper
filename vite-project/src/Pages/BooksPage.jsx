import React,{ useState, useEffect, useRef } from 'react'
import DescriptiveBookCard from '../components/DescriptiveBookCard.jsx'
import NavBar from '../components/NavBar'
import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });
import BookPopup from '../components/BookPopupPanel.jsx';


function BooksPage() {

    const [doOnce, setDoOnce] = useState(false);
    const [bookList, setBookList]=useState(['']);
    const [popupBook, setPopupBook] = useState(null); // For popup panel

    const sectionRefs = useRef({});
    useEffect(()=>{
    if (!doOnce){
        setDoOnce(true);
        populateTable();
        }
    })

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
        setBookList(dataY)
        console.log(dataY)
    }
    catch(error){
        console.log(error)
    }
    }


    // Scroll to section by websiteHost
    const scrollToSection = (websiteHost) => {
        if (sectionRefs.current[websiteHost]) {
            sectionRefs.current[websiteHost].scrollIntoView({ behavior: "smooth", block: "start" });
        }
    };

    const renderBookSections = () => {
        return bookList.map(([websiteHost, booksArray], index) => (
            Array.isArray(booksArray) && (
                <section
                    key={index}
                    ref={el => sectionRefs.current[websiteHost] = el}
                    className="book-section mb-8"
                    id={`section-${websiteHost}`}
                >
                    <h2 className="text-2xl font-bold mb-4">{websiteHost}</h2>
                    <article className="grid grid-cols-4 gap-6 rounded-lg">
                        {booksArray.map((book) => (
                            <div key={book[0]} onClick={() => setPopupBook(book)} className="cursor-pointer">
                                <DescriptiveBookCard
                                    data={{
                                        _id: book[0],
                                        bookName: book[1],
                                        bookAuthor: book[2],
                                        description: book[3],
                                        lastScraped: book[5],
                                        latestChapter: book[6],
                                    }}
                                />
                            </div>
                        ))}
                    </article>
                </section>
            )
        ));
    };

    // Render jump buttons for each websiteHost
    const renderJumpButtons = () => (
        <div className="flex flex-col gap-2 p-4">
            {bookList.map(([websiteHost]) => (
                <button
                    key={websiteHost}
                    className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded text-left"
                    onClick={() => scrollToSection(websiteHost)}>
                    {websiteHost}
                </button>))}
        </div>
    );
    
    // Pop-up close handler
    const closePopup = () => setPopupBook(null);
    return (
    <>
    <NavBar />
        <h1 className="books-page-heading">
            Here you can find the current selection of books available.
        </h1>
        <main className="books-page-content">
            {/* Left panel: jump buttons */}
            <aside className="books-page-content-left">
                {renderJumpButtons()}
            </aside>
            {/* Center panel: scrollable book cards */}
            <div className="books-page-content-main">    {renderBookSections()}
            </div>
        </main>
        {/* Popup Panel */}
        <BookPopup book={popupBook} onClose={closePopup} />
    </>
    )
    }
export default BooksPage;
