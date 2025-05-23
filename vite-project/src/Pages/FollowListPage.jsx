import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom';
import BookCard from '../components/BookCard.jsx'
import NavBar from '../components/NavBar'

import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });



export function FollowListPage() {
  
  const [username, setUserName]=useState("");
  const [verifiedState, setVerifiedState]=useState(false);

  const [bookList, setBookList]=useState([]);

  const navigate = useNavigate();

  useEffect(() => {
  async function authenticateAndPopulate() {
    const response = await axios.get(`${API_URL}/followedBooks`,{withCredentials:true});
    if (response.status === 200) {
      setUserName(response.data.username);
      setVerifiedState(response.data.verified);
      setBookList(response.data.allbooks);

    } else {
      navigate("/react/LoginPage/");
    }
  }
  authenticateAndPopulate();
}, []);

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

  return (
    <>
    <NavBar/>
    <div className='h-full mx-50 w-[calc(100%-100)] max-w-full text-white'>
        <header className='flex flex-col gap-10 h-full mx-50 text-center '>
            <h1 className='text-4xl mt-10'>Your followed books</h1>
        </header>
        <main className='mt-20'>
            {renderBookSections()}
        </main>
    </div>
    </>
  )
}

export default FollowListPage