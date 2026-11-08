import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { LocaleProvider } from './contexts/LocaleContext';
import Layout from './components/Layout/Layout';
import HomePage from './pages/HomePage';
import ProblemsPage from './pages/ProblemsPage';
import ProblemDetailPage from './pages/ProblemDetailPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProfilePage from './pages/ProfilePage';
import RecordsPage from './pages/RecordsPage';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <LocaleProvider>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<HomePage />} />
              <Route path="problems" element={<ProblemsPage />} />
              <Route path="problems/:identifier" element={<ProblemDetailPage />} />
              <Route path="login" element={<LoginPage />} />
              <Route path="register" element={<RegisterPage />} />
              <Route path="profile" element={<ProfilePage />} />
              <Route path="records" element={<RecordsPage />} />
            </Route>
          </Routes>
        </LocaleProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
