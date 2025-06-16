import React,{ useState, useEffect, useRef } from 'react'
import NavBar from '../components/NavBar.jsx'
import axios from "axios";
const API_URL = "http://localhost:8000/api";
const api = axios.create({ baseURL: API_URL });
import { useUser } from "../components/UserContext.jsx";


function OnlineReaderPage() {


return (
    <>
    <NavBar/>
    </>



)
}export default OnlineReaderPage;

