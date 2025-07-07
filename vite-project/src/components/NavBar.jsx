//import '../NavBar.css'
import { Link } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';
import { useUser } from "./UserContext";


import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });


function Navbar(){
    const { isDeveloper, isLoggedIn, logout } = useUser();

    const navigate = useNavigate();

    async function handleLogout(e) {
        await logout();
        navigate("/react/LoginPage");
    }

    return(
        <>
        <nav>
            <navbar className="navbar-center">
                <ul className="nav-links">
                    <li>
                        
                        <Link to="/react/HomePage">Home Page</Link>
                    </li>
                    <li>
                        <Link to="/react/DownloadPage">Downloads</Link>
                    </li>
                    <li>
                        <Link to="/react/BooksPage">Books</Link>
                    </li>
                    <li>
                        <Link to="/react/BookScraperPage">Online Api</Link>
                    </li>

                </ul>
            </navbar>
            <navbar className="navbar-right">
                {isDeveloper && (
                    <li>
                        <Link to="/react/DeveloperBookEditPage">Edit Book Data</Link>
                    </li>
                )}
                {isDeveloper && (
                    <li>
                        <Link to="/react/DeveloperPage">Developer</Link>
                    </li>
                )}
                <li>
                    <Link to="/react/FollowListPage">Follow Lists</Link>
                </li>
                <li>
                    <Link to="/react/UserPage">User</Link>
                </li>
                {isLoggedIn ? (
                        <button onClick={handleLogout} className="logout-button">
                            Logout
                        </button>
                    ) : (
                        <Link to="/react/LoginPage">Login</Link>
                    )}
            </navbar>


        </nav>        
        </>
    )


}
export default Navbar