import React from "react";
import { Route, Routes } from "react-router-dom";
import { Shell } from "./components/layout";
import UploadPage from "./pages/UploadPage";
import JobsPage from "./pages/JobsPage";
import SearchPage from "./pages/SearchPage";
import OutlinePage from "./pages/OutlinePage";
import ChunksPage from "./pages/ChunksPage";
import AboutPage from "./pages/AboutPage";
import ChatPage from "./pages/ChatPage";
import ReportPage from "./pages/ReportPage";

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/outline" element={<OutlinePage />} />
        <Route path="/chunks" element={<ChunksPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/report" element={<ReportPage />} />
        <Route path="/about" element={<AboutPage />} />
      </Routes>
    </Shell>
  );
}
