import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient } from './api';
import './SubmitPage.css';

const SubmitPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [contest, setContest] = useState(null);
  const [formData, setFormData] = useState({
    article_title: '',
    article_link: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });
  const [errors, setErrors] = useState({});

  useEffect(() => {
    // Fetch contest details
    apiClient.get(`/contest/${id}`)
      .then(res => setContest(res.data))
      .catch(err => {
        console.error('Error fetching contest:', err);
        setMessage({ text: 'Error loading contest details', type: 'error' });
      });
  }, [id]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.article_title.trim()) {
      newErrors.article_title = 'Article title is required';
    }
    
    if (!formData.article_link.trim()) {
      newErrors.article_link = 'Article link is required';
    } else {
      // Basic URL validation
      try {
        new URL(formData.article_link);
      } catch {
        newErrors.article_link = 'Please enter a valid URL';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setIsSubmitting(true);
    setMessage({ text: '', type: '' });
    
    try {
      // Ensure we're sending properly formatted data
      const submitData = {
        article_title: formData.article_title.trim(),
        article_link: formData.article_link.trim()
      };
      
      console.log('Submitting data:', submitData); // Debug log
      
      const response = await apiClient.post(`/contest/${id}/submit`, submitData);
      
      if (response.data.message) {
        setMessage({ 
          text: `Success! ${response.data.message}`,
          type: 'success'
        });
        
        // Clear form
        setFormData({
          article_title: '',
          article_link: ''
        });
        
        // Redirect to contest details after a delay
        setTimeout(() => {
          navigate(`/contest/${id}`);
        }, 2000);
      }
    } catch (error) {
      console.error('Submit error:', error.response?.data || error.message); // Debug log
      const errorMessage = error.response?.data?.error || 'Failed to submit. Please try again.';
      setMessage({ 
        text: errorMessage,
        type: 'error'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const isActive = () => {
    if (!contest) return false;
    const now = new Date();
    const start = new Date(contest.start_date);
    const end = new Date(contest.end_date);
    return now >= start && now <= end;
  };

  if (!contest) return <div className="loading">Loading contest...</div>;

  return (
    <div className="submit-page">
      <div className="header">
        <button className="back-btn" onClick={() => navigate(`/contest/${id}`)}>
          <span>←</span> Back to Contest
        </button>
        <h1>Submit to {contest.name}</h1>
      </div>

      {!isActive() && (
        <div className="warning-banner">
          <span>⚠️</span>
          <div>
            <strong>Contest is not active</strong>
            <p>This contest is currently not accepting submissions.</p>
          </div>
        </div>
      )}

      <div className="contest-info-banner">
        <h3>Contest Details</h3>
        <div className="info-grid">
          <div className="info-item">
            <span className="label">Project:</span>
            <span className="value">{contest.project_name}</span>
          </div>
          <div className="info-item">
            <span className="label">Namespace:</span>
            <span className="value">{contest.rules.article_namespace}</span>
          </div>
          <div className="info-item">
            <span className="label">End Date:</span>
            <span className="value">{new Date(contest.end_date).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit'
            })}</span>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="submit-form">
        <div className="form-group">
          <label htmlFor="article_title" className="form-label">
            Article Title
            <span className="required">*</span>
          </label>
          <input
            type="text"
            id="article_title"
            name="article_title"
            value={formData.article_title}
            onChange={handleInputChange}
            placeholder="Enter the article title"
            className={`form-input ${errors.article_title ? 'error' : ''}`}
            disabled={!isActive() || isSubmitting}
          />
          {errors.article_title && (
            <div className="error-message">{errors.article_title}</div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="article_link" className="form-label">
            Article Link
            <span className="required">*</span>
          </label>
          <input
            type="url"
            id="article_link"
            name="article_link"
            value={formData.article_link}
            onChange={handleInputChange}
            placeholder="https://en.wikipedia.org/wiki/article-name"
            className={`form-input ${errors.article_link ? 'error' : ''}`}
            disabled={!isActive() || isSubmitting}
          />
          {errors.article_link && (
            <div className="error-message">{errors.article_link}</div>
          )}
          <div className="form-help">
            Please enter the full Wikipedia URL for the article you want to submit.
          </div>
        </div>

        {message.text && (
          <div className={`message-banner ${message.type}`}>
            <span>{message.type === 'success' ? '✓' : '✕'}</span>
            {message.text}
          </div>
        )}

        <div className="form-actions">
          <button 
            type="submit" 
            className="submit-btn"
            disabled={!isActive() || isSubmitting}
          >
            {isSubmitting ? (
              <>
                <span className="spinner"></span>
                Submitting...
              </>
            ) : (
              <>
                <span>📝</span>
                Submit Article
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default SubmitPage;