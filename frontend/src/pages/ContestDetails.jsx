import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiClient } from "./api";
import "./ContestDetails.css";
import { Link } from 'react-router-dom';

const ContestDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [contest, setContest] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [user, setUser] = useState(null);
  const [submissionsError, setSubmissionsError] = useState(false);

  useEffect(() => {
    // Get logged-in user (if any)
    apiClient.get("/cookie")
      .then((res) => setUser(res.data))
      .catch(() => setUser(null));
  }, []);

  useEffect(() => {
    // Contest Details
    apiClient.get(`/contest/${id}`)
      .then(res => setContest(res.data))
      .catch(console.error);

    // Leaderboard
    apiClient.get(`/contest/${id}/leaderboard`)
      .then(res => setLeaderboard(res.data))
      .catch(console.error);

    // Submissions (only for users with access)
    apiClient.get(`/contest/${id}/submissions`)
      .then(res => setSubmissions(res.data))
      .catch(err => setSubmissionsError(true));
  }, [id]);

  const isActive = () => {
    if (!contest) return false;
    const now = new Date();
    const start = new Date(contest.start_date);
    const end = new Date(contest.end_date);
    return now >= start && now <= end;
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (status) => {
    const statusClass = status.toLowerCase().replace(' ', '-');
    return <span className={`status-badge status-${statusClass}`}>{status}</span>;
  };

  if (!contest) return <div className="loading">Loading contest...</div>;

  return (
    <div className="contest-page">
      <div className="header">
        <button className="home-btn" onClick={() => navigate("/")}>
          <span>🏠</span> Home
        </button>
        <h1 className="contest-title">{contest.name}</h1>
        {isActive() && <div className="active-badge">ACTIVE</div>}
      </div>

      <div className="contest-info">
        <div className="info-card">
          <h3>Contest Information</h3>
          <div className="info-grid">
            <div className="info-item">
              <span className="label">Project:</span>
              <span className="value">{contest.project_name}</span>
            </div>
            <div className="info-item">
              <span className="label">Created by:</span>
              <span className="value">{contest.created_by}</span>
            </div>
            <div className="info-item">
              <span className="label">Start Date:</span>
              <span className="value">{formatDate(contest.start_date)}</span>
            </div>
            <div className="info-item">
              <span className="label">End Date:</span>
              <span className="value">{formatDate(contest.end_date)}</span>
            </div>
            <div className="info-item">
              <span className="label">Description:</span>
              <span className="value">{contest.description}</span>
            </div>
            <div className="info-item">
              <span className="label">Code Link:</span>
              <a href={contest.code_link} target="_blank" rel="noreferrer" className="code-link">
                {contest.code_link}
              </a>
            </div>
          </div>
        </div>

        <div className="rules-card">
          <h3>Rules & Settings</h3>
          <div className="rules-grid">
            <div className="rule-item">
              <span className="label">Namespace:</span>
              <span className="value">{contest.rules.article_namespace}</span>
            </div>
            <div className="rule-item">
              <span className="label">User Role:</span>
              <span className="value">{contest.rules.user_role}</span>
            </div>
            <div className="rule-item">
              <span className="label">Custom Rules:</span>
              <span className="value">{contest.rules.custom_rules}</span>
            </div>
            <div className="rule-item">
              <span className="label">Scoring:</span>
              <span className="value">
                +{contest.marks_setting_accepted} accepted, {contest.marks_setting_rejected} rejected
              </span>
            </div>
            <div className="rule-item">
              <span className="label">Jury:</span>
              <span className="value">{contest.jury_members.join(", ")}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="section leaderboard-section">
        <h2>🏆 Leaderboard</h2>
        {leaderboard.length === 0 ? (
          <div className="empty-state">No scores available yet.</div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>User</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.map((entry, index) => (
                  <tr key={entry.user_id} className={index < 3 ? `rank-${index + 1}` : ''}>
                    <td className="rank-cell">
                      {index === 0 && <span className="trophy">🥇</span>}
                      {index === 1 && <span className="trophy">🥈</span>}
                      {index === 2 && <span className="trophy">🥉</span>}
                      {index > 2 && <span className="rank-number">{index + 1}</span>}
                    </td>
                    <td>{entry.username}</td>
                    <td className="score-cell">{entry.total_score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {user && isActive() && (
        <div className="section submit-section">
          <button
            className="submit-btn"
            onClick={() => navigate(`/contest/${id}/submit`)}
          >
            <span>➕</span> Add Submission
          </button>
        </div>
      )}

      <div className="section submissions-section">
        <h2>📋 Submissions</h2>
        {submissionsError ? (
          <div className="error-state">
            <span>🔒</span> You do not have access to view submissions.
          </div>
        ) : submissions.length === 0 ? (
          <div className="empty-state">No submissions found.</div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Article Title</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {submissions.map(sub => (
                  <tr key={sub.id} className="submission-row" onClick={() => navigate(`/submission/${sub.id}`)}>
                    <td className="submission-title">
                      <Link to={`/submission/${sub.id}`} className="submission-link">
                        {sub.article_title}
                      </Link>
                    </td>
                    <td className="status-cell">
                      {getStatusBadge(sub.status)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContestDetails;