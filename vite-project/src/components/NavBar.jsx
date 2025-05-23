import '../NavBar.css'
import { Link } from 'react-router-dom';

function Navbar(){
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


                </ul>
            </navbar>
            <navbar className="navbar-right">
                <li>
                    <Link to="/react/FollowListPage">Follow Lists</Link>
                </li>
                <li>
                    <Link to="/react/UserPage">User</Link>
                </li>
                <li>
                    <Link to="/react/LoginPage">Login</Link>
                </li>
            </navbar>


        </nav>        
        </>
    )


}
export default Navbar