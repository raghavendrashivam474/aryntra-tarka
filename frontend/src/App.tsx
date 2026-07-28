import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import ChatWindow from "./components/ChatWindow";
import { SettingsPage } from "./pages/Settings";
import CommandCenterPage from "./pages/CommandCenterPage";

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Command Center - fullscreen, no Layout wrapper */}
        <Route path="/command-center" element={<CommandCenterPage />} />

        {/* Everything else - inside main Layout */}
        <Route
          path="/*"
          element={
            <Layout>
              <Routes>
                <Route path="/" element={<ChatWindow />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </Layout>
          }
        />
      </Routes>
    </BrowserRouter>
  );
};

export default App;
