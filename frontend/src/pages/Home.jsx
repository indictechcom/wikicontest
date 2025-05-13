import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AddIcon from '@mui/icons-material/Add';
import { apiClient } from './api'; // Adjust path if needed

const Home = () => {
  const [contests, setContests] = useState({ current: [], upcoming: [], past: [] });
  const [searchTerm, setSearchTerm] = useState('');
  const [projectFilter, setProjectFilter] = useState('All Projects');
  const [user, setUser] = useState(null);
  const navigate = useNavigate();

  // Fetch login status from cookie
  useEffect(() => {
    apiClient.get('/cookie', { withCredentials: true })
      .then(res => {
        setUser(res.data);
      })
      .catch(() => {
        setUser(null);
      });
  }, []);

  // Fetch contests
  useEffect(() => {
    apiClient.get('/contest')
      .then(res => {
        setContests(res.data);
        // console.log('Fetched contests:', res.data);
      })
      .catch(err => console.error('Error fetching contests:', err));
  }, []);

  const handleSearch = (list) => {
    return list.filter(c =>
      c.name.toLowerCase().includes(searchTerm.toLowerCase()) &&
      (projectFilter === 'All Projects' || c.project_name === projectFilter)
    );
  };

  const handleLogout = async () => {
    try {
      await apiClient.post('/user/logout', {}, { withCredentials: true });
    } catch (err) {
      console.error('Logout failed:', err);
    } finally {
      setUser(null);
      navigate('/');
    }
  };

  const renderContests = (title, list) => {
    const filteredList = handleSearch(list);
    if (filteredList.length === 0) return null;

    return (
      <div style={{ marginTop: '2rem' }}>
        <h3>{title}</h3>
        <div>
          {filteredList.map(contest => (
            <div
              key={contest.id}
              onClick={() => navigate(`/contest/${contest.id}`)}
              style={{
                border: '1px solid #ccc',
                padding: '1rem',
                margin: '0.5rem 0',
                cursor: 'pointer',
                borderRadius: '6px',
                backgroundColor: '#f9f9f9',
              }}
            >
              <strong>{contest.name}</strong>
              <div style={{ float: 'right' }}>
                <small>{contest.start_date} to {contest.end_date}</small>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div style={{ backgroundColor: '#f4f6f8', minHeight: '100vh', paddingBottom: '4rem' }}>
      
      {/* Header */}
      <div style={{
        backgroundColor: '#0066cc',
        padding: '1rem 2rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        color: 'white',
        boxShadow: '0 2px 5px rgba(0,0,0,0.1)',
      }}>
        <h2 style={{ margin: 0 }}>Editathons</h2>
        {user ? (
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              onClick={() => navigate('/dashboard')}
              style={{
                background: 'linear-gradient(to right, #00b09b, #96c93d)',
                color: 'white',
                border: 'none',
                padding: '0.5rem 1.2rem',
                borderRadius: '20px',
                fontWeight: 'bold',
                cursor: 'pointer'
              }}
            >
              DASHBOARD
            </button>
            <button
              onClick={handleLogout}
              style={{
                background: 'linear-gradient(to right, #ff416c, #ff4b2b)',
                color: 'white',
                border: 'none',
                padding: '0.5rem 1.2rem',
                borderRadius: '20px',
                fontWeight: 'bold',
                cursor: 'pointer'
              }}
            >
              LOGOUT
            </button>
          </div>
        ) : (
          <button
            onClick={() => navigate('/login')}
            style={{
              background: 'linear-gradient(to right, #d100a3, #ff00cc)',
              color: 'white',
              border: 'none',
              padding: '0.5rem 1.2rem',
              borderRadius: '20px',
              fontWeight: 'bold',
              cursor: 'pointer'
            }}
          >
            LOG IN
          </button>
        )}
      </div>

      {/* Main content container */}
      <div style={{
        maxWidth: '900px',
        margin: '2rem auto',
        backgroundColor: 'white',
        padding: '2rem',
        borderRadius: '10px',
        boxShadow: '0 0 10px rgba(0,0,0,0.1)'
      }}>
        
        {/* Filters */}
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '2rem',
        }}>
          <input
            type="text"
            placeholder="Search contests..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            style={{
              flex: 1,
              padding: '0.6rem',
              borderRadius: '5px',
              border: '1px solid #ccc',
              minWidth: '200px'
            }}
          />
          <div>
            <label style={{ fontSize: '0.8rem' }}>Project Type</label>
            <select
              value={projectFilter}
              onChange={e => setProjectFilter(e.target.value)}
              style={{ display: 'block', padding: '0.5rem', minWidth: '150px' }}
            >
              <option>All Projects</option>
              <option>Wikipedia</option>
              <option>Wikimedia</option>
            </select>
          </div>
        </div>

        {/* Contest Sections */}
        {handleSearch([
          ...contests.current,
          ...contests.upcoming,
          ...contests.past
        ]).length === 0 ? (
          <div>
            <h3>Contests</h3>
            <p>No contests found</p>
          </div>
        ) : (
          <>
            {renderContests('Current Contests', contests.current)}
            {renderContests('Upcoming Contests', contests.upcoming)}
            {renderContests('Past Contests', contests.past)}
          </>
        )}
      </div>

      {/* Floating Action Button */}
      {user && (
        <button
          onClick={() => navigate('/create-contest')}
          style={{
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            backgroundColor: '#0066cc',
            color: 'white',
            border: 'none',
            borderRadius: '50%',
            width: '56px',
            height: '56px',
            fontSize: '30px',
            lineHeight: '56px',
            textAlign: 'center',
            boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
            cursor: 'pointer',
          }}
          title="Create Contest"
        >
          <AddIcon />
        </button>
      )}
    </div>
  );
};

export default Home;
