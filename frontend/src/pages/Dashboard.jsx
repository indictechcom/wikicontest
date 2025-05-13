import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "./api";
import "./Dashboard.css";

const Dashboard = () => {
  const navigate = useNavigate();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get("/user/dashboard");
      setDashboardData(response.data);
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getStatusBadge = (status) => {
    const statusClass = status.toLowerCase().replace(' ', '-');
    return <span className={`status-badge status-${statusClass}`}>{status}</span>;
  };

  const getContestStatus = (startDate, endDate) => {
    const now = new Date();
    const start = new Date(startDate);
    const end = new Date(endDate);
    
    if (now < start) return { text: "Upcoming", class: "upcoming" };
    if (now > end) return { text: "Ended", class: "ended" };
    return { text: "Active", class: "active" };
  };

  if (loading) {
    return <div className="dashboard-loading">Loading dashboard...</div>;
  }

  if (!dashboardData) {
    return <div className="dashboard-error">Failed to load dashboard data</div>;
  }

  return (
    <div className="dashboard">
      <div className="nav-header">
        <button className="nav-btn" onClick={() => navigate(-1)}>
          ← Back
        </button>
        <button className="nav-btn" onClick={() => navigate('/')}>
          🏠 Home
        </button>
      </div>
      <div className="dashboard-header">
        <h1>🎯 Dashboard</h1>
        <div className="user-summary">
          <span className="username">Welcome, {dashboardData.username}!</span>
          <div className="total-score">
            Total Score: <span className="score-value">{dashboardData.total_score}</span>
          </div>
        </div>
      </div>

      {/* Contest Performance Overview */}
      <div className="section">
        <h2>📊 Contest Performance</h2>
        <div className="performance-cards">
          {dashboardData.contest_wise_scores.map((contest) => (
            <div 
              key={contest.contest_id} 
              className="performance-card"
              onClick={() => navigate(`/contest/${contest.contest_id}`)}
            >
              <h3>{contest.contest_name}</h3>
              <div className="performance-stats">
                <div className="stat">
                  <span className="stat-label">Score</span>
                  <span className="stat-value score">{contest.contest_score}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Submissions</span>
                  <span className="stat-value">{contest.submission_count}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Submissions by Contest */}
      <div className="section">
        <h2>📝 Your Submissions</h2>
        <div className="submissions-by-contest">
          {dashboardData.submissions_by_contest.map((contestGroup) => (
            <div key={contestGroup.contest_id} className="contest-submissions">
              <h3 
                className="contest-header clickable"
                onClick={() => navigate(`/contest/${contestGroup.contest_id}`)}
              >
                {contestGroup.contest_name}
              </h3>
              <div className="submissions-grid">
                {contestGroup.submissions.map((submission) => (
                  <div 
                    key={submission.id} 
                    className="submission-card"
                    onClick={() => navigate(`/submission/${submission.id}`)}
                  >
                    <h4>{submission.article_title}</h4>
                    <div className="submission-details">
                      <div className="submission-meta">
                        <span className="submission-date">
                          📅 {formatDate(submission.submitted_at)}
                        </span>
                        <div className="submission-status">
                          {getStatusBadge(submission.status)}
                        </div>
                      </div>
                      <div className="submission-score">
                        Score: <span className="score-value">{submission.score}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Created Contests */}
      <div className="section">
        <h2>🏆 Created Contests</h2>
        <div className="contests-table-container">
          <table className="contests-table">
            <thead>
              <tr>
                <th>Contest Name</th>
                <th>Project</th>
                <th>Status</th>
                <th>Period</th>
                <th>Submissions</th>
                <th>Scoring</th>
              </tr>
            </thead>
            <tbody>
              {dashboardData.created_contests.map((contest) => {
                const status = getContestStatus(contest.start_date, contest.end_date);
                return (
                  <tr 
                    key={contest.id} 
                    className="contest-row"
                    onClick={() => navigate(`/contest/${contest.id}`)}
                  >
                    <td className="contest-name">
                      <div className="contest-title">{contest.name}</div>
                      <div className="contest-desc">{contest.description}</div>
                    </td>
                    <td>{contest.project_name}</td>
                    <td>
                      <span className={`status-badge status-${status.class}`}>
                        {status.text}
                      </span>
                    </td>
                    <td className="contest-period">
                      <div>{formatDate(contest.start_date)}</div>
                      <div>- {formatDate(contest.end_date)}</div>
                    </td>
                    <td className="submission-count">{contest.submission_count}</td>
                    <td className="scoring">
                      <span className="score-positive">+{contest.marks_setting_accepted}</span>
                      <span className="score-negative">{contest.marks_setting_rejected}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Jury Contests */}
      <div className="section">
        <h2>⚖️ Jury Duties</h2>
        <div className="contests-table-container">
          <table className="contests-table">
            <thead>
              <tr>
                <th>Contest Name</th>
                <th>Project</th>
                <th>Created By</th>
                <th>Status</th>
                <th>Period</th>
                <th>Submissions</th>
              </tr>
            </thead>
            <tbody>
              {dashboardData.jury_contests.map((contest) => {
                const status = getContestStatus(contest.start_date, contest.end_date);
                return (
                  <tr 
                    key={contest.id} 
                    className="contest-row"
                    onClick={() => navigate(`/contest/${contest.id}`)}
                  >
                    <td className="contest-name">
                      <div className="contest-title">{contest.name}</div>
                      <div className="contest-desc">{contest.description}</div>
                    </td>
                    <td>{contest.project_name}</td>
                    <td>{contest.created_by}</td>
                    <td>
                      <span className={`status-badge status-${status.class}`}>
                        {status.text}
                      </span>
                    </td>
                    <td className="contest-period">
                      <div>{formatDate(contest.start_date)}</div>
                      <div>- {formatDate(contest.end_date)}</div>
                    </td>
                    <td className="submission-count">{contest.submission_count}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;