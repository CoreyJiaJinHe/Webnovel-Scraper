import '../NavBar.css'

function Navbar(){
    return(
        <>
        <nav>
            <div className="navbar-center">
                <ul className="nav-links">
                    <li>
                        <a href="/react/HomePage/">Home Page</a>
                    </li>
                    <li>
                        <a href="/react/DownloadPage/">Downloads</a>
                    </li>


                </ul>
            </div>
            <div className="navbar-right">
                <li>
                    <a href="/react/LoginPage/">Login</a>
                </li>
            </div>


        </nav>        
        </>
    )


}
export default Navbar