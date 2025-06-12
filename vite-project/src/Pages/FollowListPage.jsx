import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom';
import BookCard from '../components/BookCard.jsx'
import NavBar from '../components/NavBar'
import { useUser } from "../components/UserContext";

import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });



export function FollowListPage() {

  const [bookList, setBookList] = useState([]);

  const {
    isLoggedIn, setIsLoggedIn,
    username, setUsername,
    verifiedState, setVerifiedState,
    logout
  } = useUser();


  const navigate = useNavigate();

  useEffect(() => {
    authenticateAndPopulate();
  }, []);

  //Cookie is not accessible to JS which is why this and the userpage is broken
  async function authenticateAndPopulate() {
    try {
      const response = await axios.post(`${API_URL}/token/`, {}, {withCredentials:true});
      if (response.status === 200) {
        console.log("User is authenticated:", response.data);
        setIsLoggedIn(true);
        setUsername(response.data.username);
        setVerifiedState(response.data.verified);
        try{
          const response = await axios.get(`${API_URL}/followedBooks`, { withCredentials: true });
          if (response.status !== 200) {
            console.error("Error fetching followed books:", response.statusText);
            return;
          }
          if (response.data && response.data.allbooks) {
          setBookList(response.data.allbooks);
          } else {
          // Handle case where no data is returned
          setBookList([]);
          console.warn("No followed books data returned from backend.");
        }
        }
        catch(error){
          console.error("Error fetching followed books:", error);
        }
      }
    } catch (error) {
      console.log("User is not authenticated, redirecting to login:", error);
      //setIsLoggedIn(false);
      navigate("/react/LoginPage/");
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
        <section key={index} className="book-section">
        <h2 className="book-section-header">{websiteHost}</h2>
        <article className="book-section-article">
            {booksArray.map((book) => (
              <BookCard
                key={book[0]} // Assuming book[0] is the bookID
                //function bookCard({data:{_id, bookName,lastScraped,latestChapter},getBook}){
                data={{
                  _id: book[0],
                  bookName: book[1],
                  description: book[3],
                  lastScraped: book[5],
                  latestChapter: book[6],
                }}
                getBook={grabBook}
              />
            ))}
          </article>
        </section>
      );
    });
  };

  function grabBook(id) {
    getBook(id)
  }

//flex flex-col gap-10 h-full mx-50 text-center  className='text-4xl mt-10'
  return (
    <>
      <NavBar />
      <div className="follow-list-page-bg">
        <div className='follow-list-page-main'>
          <header className='follow-list-page-header'>
            <h1 >Your followed books</h1>
          </header>
          <main className='mt-20'>
            {bookList.length === 0 ? (
            <h2 className="no-books-heading">
              You are not following any books yet!
            </h2>
          ) : (
            renderBookSections()
          )}
          </main>
        </div>
      </div>
    </>
  )
}

export default FollowListPage