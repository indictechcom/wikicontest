import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiClient } from "./api";
import "./SubmissionReview.css";

const SubmissionReview = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [submission, setSubmission] = useState(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    const fetchSubmission = async () => {
      try {
        setLoading(true);
        const response = await apiClient.get(`/submission/${id}`);
        setSubmission(response.data);
      } catch (err) {
        if (err.response?.status === 403 || err.response?.status === 401) {
          setError("You don't have permission to view this submission.");
        } else if (err.response?.status === 404) {
          setError("Submission not found.");
        } else {
          setError("Failed to load submission. Please try again.");
        }
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchSubmission();
    }
  }, [id]);

  const handleStatusChange = async (newStatus) => {
    if (!submission || updating) return;

    setUpdating(true);
    setMessage("");
    setError("");

    try {
      const response = await apiClient.put(`/submission/${id}`, { status: newStatus });
      setSubmission(prev => ({ ...prev, status: newStatus }));
      setMessage(`Submission ${newStatus} successfully!`);
    } catch (err) {
      // const errorMsg = err.response?.data?.message || `Failed to ${newStatus} submission`;
      // setError(errorMsg);
      navigate('*');
    } finally {
      setUpdating(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="submission-page">
        <div className="loading">
          <p>Loading submission...</p>
        </div>
      </div>
    );
  }

  if (error && !submission) {
    return (
      <div className="submission-page">
        <button className="back-btn" onClick={() => navigate(-1)}>← Back</button>
        <div className="error-container">
          <p className="error">{error}</p>
          <button className="retry-btn" onClick={() => window.location.reload()}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="submission-page">
      <button className="back-btn" onClick={() => navigate(-1)}>← Back</button>
      
      <div className="header">
        <h1>Submission Review</h1>
        <div className="submission-id">#{id}</div>
      </div>

      <div className="submission-details">
        <div className="details-grid">
          <div className="detail-item">
            <div className="detail-label">Submitted by</div>
            <div className="detail-value">User #{submission.user_id}</div>
          </div>
          
          <div className="detail-item">
            <div className="detail-label">Contest</div>
            <div className="detail-value">#{submission.contest_id}</div>
          </div>
          
          <div className="detail-item">
            <div className="detail-label">Status</div>
            <div className="detail-value">
              <span className={`status ${submission.status}`}>
                {submission.status.charAt(0).toUpperCase() + submission.status.slice(1)}
              </span>
            </div>
          </div>
          
          <div className="detail-item">
            <div className="detail-label">Score</div>
            <div className="detail-value">{submission.score || 'Not scored'}</div>
          </div>
          
          <div className="detail-item">
            <div className="detail-label">Submitted</div>
            <div className="detail-value">{formatDate(submission.submitted_at)}</div>
          </div>
          
          <div className="detail-item article-item">
            <div className="detail-label">Article</div>
            <div className="detail-value">
              <a 
                href={submission.article_link} 
                target="_blank" 
                rel="noopener noreferrer"
                className="article-link"
              >
                {submission.article_title}
              </a>
            </div>
          </div>
        </div>
      </div>

      {submission.status === "pending" && (
        <div className="action-section">
          <h3>Review Actions</h3>
          <div className="action-buttons">
            <button 
              className="action-btn accept-btn" 
              onClick={() => handleStatusChange("accepted")}
              disabled={updating}
            >
              {updating ? 'Processing...' : '✓ Accept Submission'}
            </button>
            <button 
              className="action-btn reject-btn" 
              onClick={() => handleStatusChange("rejected")}
              disabled={updating}
            >
              {updating ? 'Processing...' : '✗ Reject Submission'}
            </button>
          </div>
        </div>
      )}

      {submission.status !== "pending" && (
        <div className="status-notice">
          This submission has been <strong>{submission.status}</strong> and can no longer be changed.
        </div>
      )}

      {message && (
        <div className="message success">{message}</div>
      )}

      {error && (
        <div className="message error">{error}</div>
      )}
    </div>
  );
};

export default SubmissionReview;