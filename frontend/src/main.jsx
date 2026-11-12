import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import Layout from "./Layout.jsx";
import Booking from "./pages/Booking.jsx";
import Cancel from "./pages/Cancel.jsx";
import NotFound from "./pages/NotFound.jsx";
import Owner from "./pages/Owner.jsx";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Booking />} />
          <Route path="otkazi/:token" element={<Cancel />} />
          <Route path="vlasnik" element={<Owner />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
