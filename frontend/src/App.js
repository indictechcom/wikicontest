import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import ContestCreatePage from './pages/CreateContest';
import ContestDetails from './pages/ContestDetails';
import SubmissionReview from './pages/SubmissionReview';
import SubmitPage from './pages/SubmitPage';
import NotAllowed from './pages/NotAllowed';
import Dashboard from './pages/Dashboard';
import ProtectedRoute from './pages/ProtectedRoute';
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/contest/:id" element={<ContestDetails />} />
        <Route path="*" element={<NotAllowed />} />

      <Route
        path="/create-contest"
        element={
          <ProtectedRoute>
            <ContestCreatePage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/submission/:id"
        element={
          <ProtectedRoute>
            <SubmissionReview />
          </ProtectedRoute>
        }
      />

      <Route
        path="/contest/:id/submit"
        element={
          <ProtectedRoute>
            <SubmitPage />
          </ProtectedRoute>
        }
      />
        

      </Routes>
    </Router>
  );
}

export default App;
