import React, { useState, useEffect } from 'react';
import { apiClient } from './api'; // Make sure this is the correct path
import './ContestCreatePage.css'; // We'll create this CSS file

const ContestCreatePage = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const [user, setUser] = useState(null);
  useEffect(() => {
    apiClient.get('/cookie', { withCredentials: true })
      .then(res => setUser(res.data))
      .catch(() => setUser(null));
  }, []);
  // Form data state
  const [formData, setFormData] = useState({
    name: '',
    code_link: '',
    project_name: '',
    description: '',
    start_date: '',
    end_date: '',
    rules: {
      article_namespace: '',
      user_role: '',
      custom_rules: ''
    },
    marks_setting_accepted: 1,
    marks_setting_rejected: 0,
    jury_members: []
  });
  
  // Temporary state for jury member input
  const [juryInput, setJuryInput] = useState('');
  
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    if (name.includes('rules.')) {
      const ruleProp = name.split('.')[1];
      setFormData(prev => ({
        ...prev,
        rules: {
          ...prev.rules,
          [ruleProp]: value
        }
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };
  
  const handleDateChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  const handleMarksChange = (type, value) => {
    setFormData(prev => ({
      ...prev,
      [type]: parseInt(value) || 0
    }));
  };
  
  const addJuryMember = () => {
    if (juryInput.trim() && !formData.jury_members.includes(juryInput.trim())) {
      setFormData(prev => ({
        ...prev,
        jury_members: [...prev.jury_members, juryInput.trim()]
      }));
      setJuryInput('');
    }
  };
  
  const removeJuryMember = (member) => {
    setFormData(prev => ({
      ...prev,
      jury_members: prev.jury_members.filter(m => m !== member)
    }));
  };
  
  const clearAllJuryMembers = () => {
    setFormData(prev => ({
      ...prev,
      jury_members: []
    }));
  };
  
  const handleNext = () => {
    setCurrentStep(currentStep + 1);
  };
  
  const handleBack = () => {
    setCurrentStep(currentStep - 1);
  };
  
  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    
    try {
      const response = await apiClient.post('/contest', formData);
      setSuccess(true);
      setError('');
    } catch (err) {
      if (err.response && err.response.data) {
        setError(err.response.data.error || 'Failed to create contest');
      } else {
        setError('Failed to create contest');
      }
    } finally {
      setLoading(false);
    }
  };
  
  const navigateToHome = () => {
    window.location.href = '/'; // Adjust this according to your routing setup
  };
  
  if (success) {
    return (
      <div className="page-container">
        <div className="header">
          <button onClick={navigateToHome} className="home-button">
            HOME
          </button>
        </div>
        <div className="main-content">
          <div className="success-container">
            <h2 className="success-title">Success!</h2>
            <p className="success-message">Contest created successfully</p>
            <button onClick={navigateToHome} className="home-link-button">
              Go to Home
            </button>
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="page-container">
      {/* Header */}
      <div className="header">
        <button onClick={navigateToHome} className="home-button">
          HOME
        </button>
      </div>
      
      {/* Main Content */}
      <div className="main-content">
        <h1 className="page-title">New Editathon</h1>
        
        {/* Tab Navigation */}
        <div className="tab-navigation">
          <div className={`tab ${currentStep === 1 ? 'tab-active' : ''}`}>
            INFO
          </div>
          <div className={`tab ${currentStep === 2 ? 'tab-active' : ''}`}>
            RULES
          </div>
          <div className={`tab ${currentStep === 3 ? 'tab-active' : ''}`}>
            MARKS
          </div>
          <div className={`tab ${currentStep === 4 ? 'tab-active' : ''}`}>
            JURY
          </div>
        </div>
        
        {/* Step 1: Info */}
        {currentStep === 1 && (
          <div className="form-step">
            <h2 className="step-title">Contest Information</h2>
            
            <div className="form-group">
              <label className="form-label">Name</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                className="form-input"
                placeholder="Contest Name"
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Code</label>
              <input
                type="text"
                name="code_link"
                value={formData.code_link}
                onChange={handleInputChange}
                className="form-input"
                placeholder="Code or Link"
              />
            </div>
            
        <div className="form-group">
          <label className="form-label">Project</label>
          <select
            name="project_name"
            value={formData.project_name}
            onChange={handleInputChange}
            className="form-input"
          >
            <option value="">Select a project</option>
            <option value="Wikipedia">Wikipedia</option>
            <option value="Wikimedia">Wikimedia</option>
          </select>
        </div>

            
          <div className="form-group">
            <label className="form-label">Created By</label>
            <input
              type="text"
              disabled
              value={user?.username || "unknown"}
              className="form-input form-input-disabled"
            />
          </div>

            
            <div className="form-group">
              <label className="form-label">Description</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                rows={4}
                className="form-textarea"
                placeholder="Contest Description"
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Start Date</label>
              <input
                type="date"
                name="start_date"
                value={formData.start_date}
                onChange={handleDateChange}
                className="form-input"
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">End Date</label>
              <input
                type="date"
                name="end_date"
                value={formData.end_date}
                onChange={handleDateChange}
                className="form-input"
              />
            </div>
            
            <div className="form-actions">
              <button
                onClick={handleBack}
                disabled={currentStep === 1}
                className="btn btn-secondary"
              >
                BACK
              </button>
              <button
                onClick={handleNext}
                className="btn btn-primary"
              >
                NEXT
              </button>
            </div>
          </div>
        )}
        
        {/* Step 2: Rules */}
        {currentStep === 2 && (
          <div className="form-step">
            <h2 className="step-title">Rule Settings</h2>
            
            <div className="form-group">
              <label className="form-label">Select Rule</label>
              <select
                name="rules.article_namespace"
                value={formData.rules.article_namespace}
                onChange={handleInputChange}
                className="form-select"
              >
                <option value="">Select a rule</option>
                <option value="main">Article Namespace</option>
                <option value="user">User Role</option>
              </select>
            </div>
            
            {formData.rules.article_namespace && (
              <div className="form-group">
                <label className="form-label">Article Namespace</label>
                <input
                  type="text"
                  name="rules.article_namespace"
                  value={formData.rules.article_namespace}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="main"
                />
              </div>
            )}
            
            <div className="form-group">
              <label className="form-label">User Role</label>
              <input
                type="text"
                name="rules.user_role"
                value={formData.rules.user_role}
                onChange={handleInputChange}
                className="form-input"
                placeholder="user"
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Custom Rules</label>
              <textarea
                name="rules.custom_rules"
                value={formData.rules.custom_rules}
                onChange={handleInputChange}
                rows={3}
                className="form-textarea"
                placeholder="Enter custom rules..."
              />
            </div>
            
            <div className="form-actions">
              <button
                onClick={handleBack}
                className="btn btn-secondary"
              >
                BACK
              </button>
              <button
                onClick={handleNext}
                className="btn btn-primary"
              >
                NEXT
              </button>
            </div>
          </div>
        )}
        
        {/* Step 3: Marks */}
        {currentStep === 3 && (
          <div className="form-step">
            <h2 className="step-title">Marks Settings</h2>
            
            <div className="form-group">
              <label className="form-label">Group Title</label>
              <input
                type="text"
                value="Accept the article?"
                readOnly
                className="form-input form-input-disabled"
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Button Title</label>
              <input
                type="text"
                value="Yes"
                readOnly
                className="form-input form-input-disabled"
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Value:</label>
              <div className="marks-control">
                <button
                  onClick={() => handleMarksChange('marks_setting_accepted', formData.marks_setting_accepted - 1)}
                  className="marks-button"
                >
                  -
                </button>
                <input
                  type="number"
                  value={formData.marks_setting_accepted}
                  onChange={(e) => handleMarksChange('marks_setting_accepted', e.target.value)}
                  className="marks-input"
                />
                <button
                  onClick={() => handleMarksChange('marks_setting_accepted', formData.marks_setting_accepted + 1)}
                  className="marks-button"
                >
                  +
                </button>
              </div>
            </div>
            
            <div className="form-group">
              <label className="form-label">Action Description</label>
              <input
                type="text"
                value="accepted"
                readOnly
                className="form-input form-input-disabled"
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Button Title</label>
              <input
                type="text"
                value="No"
                readOnly
                className="form-input form-input-disabled"
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Value:</label>
              <div className="marks-control">
                <button
                  onClick={() => handleMarksChange('marks_setting_rejected', formData.marks_setting_rejected - 1)}
                  className="marks-button"
                >
                  -
                </button>
                <input
                  type="number"
                  value={formData.marks_setting_rejected}
                  onChange={(e) => handleMarksChange('marks_setting_rejected', e.target.value)}
                  className="marks-input"
                />
                <button
                  onClick={() => handleMarksChange('marks_setting_rejected', formData.marks_setting_rejected + 1)}
                  className="marks-button"
                >
                  +
                </button>
              </div>
            </div>
            
            <div className="form-group">
              <label className="form-label">Action Description</label>
              <input
                type="text"
                value="rejected"
                readOnly
                className="form-input form-input-disabled"
              />
            </div>
            
          
            
            <div className="preview-section">
              <h3 className="preview-title">Preview</h3>
              <p className="preview-subtitle">Please pick all compulsory mark controls below to test the mark.</p>
              <p className="preview-question">Accept the article?</p>
              <div className="preview-buttons">
                <button className="btn btn-blue">Yes</button>
                <button className="btn btn-blue">No</button>
              </div>
            </div>
            
            <div className="form-actions">
              <button
                onClick={handleBack}
                className="btn btn-secondary"
              >
                BACK
              </button>
              <button
                onClick={handleNext}
                className="btn btn-primary"
              >
                NEXT
              </button>
            </div>
          </div>
        )}
        
        {/* Step 4: Jury */}
        {currentStep === 4 && (
          <div className="form-step">
            <h2 className="step-title">Jury Settings</h2>
            
            <div className="form-group">
              <label className="form-label">Add Jury Member:</label>
              <div className="jury-input-container">
                <input
                  type="text"
                  value={juryInput}
                  onChange={(e) => setJuryInput(e.target.value)}
                  className="form-input jury-input"
                  placeholder="Enter username"
                />
                <button
                  onClick={addJuryMember}
                  className="btn btn-blue"
                >
                  ADD
                </button>
              </div>
            </div>
            
            <div className="form-group">
              <h3 className="jury-members-title">Jury Members:</h3>
              <p className="jury-count">Total Jury Members: {formData.jury_members.length}</p>
              
              {formData.jury_members.length > 0 && (
                <div className="jury-members-list">
                  {formData.jury_members.map((member, index) => (
                    <div key={index} className="jury-member-item">
                      <span>{member}</span>
                      <button
                        onClick={() => removeJuryMember(member)}
                        className="remove-member-button"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={clearAllJuryMembers}
                    className="btn btn-purple"
                  >
                    CLEAR ALL JURY MEMBERS
                  </button>
                </div>
              )}
            </div>
            
            
            
            {error && (
              <div className="error-message">
                {error}
              </div>
            )}
            
            <div className="form-actions">
              <button
                onClick={handleBack}
                className="btn btn-secondary"
              >
                BACK
              </button>
              <button
                onClick={handleSubmit}
                disabled={loading}
                className="btn btn-primary"
              >
                {loading ? 'CREATING...' : 'SAVE'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContestCreatePage;