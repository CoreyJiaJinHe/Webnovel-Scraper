import '../NavBar.css'
import { Link } from 'react-router-dom';

function Navbar(){
    return(
        <>
        <nav>
            <div className="navbar-center">
                <ul className="nav-links">
                    <li>
                        
                        <Link to="/react/HomePage">Home Page</Link>
                    </li>
                    <li>
                        <Link to="/react/DownloadPage">Downloads</Link>
                    </li>


                </ul>
            </div>
            <div className="navbar-right">
                <li>
                    <Link to="/react/UserPage">User</Link>
                </li>
                <li>
                    <Link to="/react/LoginPage">Login</Link>
                </li>
            </div>


        </nav>        
        </>
    )


}
export default Navbar