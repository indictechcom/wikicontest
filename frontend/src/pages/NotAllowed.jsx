import React from 'react';
import { useNavigate } from 'react-router-dom';

export default function NotAllowed() {
  const navigate = useNavigate();

  return (
    <div style={styles.container}>
      <h1 style={styles.heading}>🚫 Access Denied</h1>
      <p style={styles.message}>You are not allowed to access this page.</p>

      <div style={styles.buttonGroup}>
        <button style={styles.button} onClick={() => navigate(-1)}>
          🔙 Go Back
        </button>
        <button style={styles.button} onClick={() => navigate('/')}>
          🏠 Home
        </button>
      </div>
    </div>
  );
}

const styles = {
  container: {
    textAlign: 'center',
    marginTop: '10vh',
    padding: '2rem',
    fontFamily: 'Segoe UI, sans-serif',
  },
  heading: {
    fontSize: '2.5rem',
    color: '#c0392b',
    marginBottom: '1rem',
  },
  message: {
    fontSize: '1.2rem',
    color: '#555',
  },
  buttonGroup: {
    marginTop: '2rem',
    display: 'flex',
    justifyContent: 'center',
    gap: '1rem',
  },
  button: {
    padding: '0.6rem 1.2rem',
    fontSize: '1rem',
    backgroundColor: '#2980b9',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'background-color 0.3s ease',
  },
};
