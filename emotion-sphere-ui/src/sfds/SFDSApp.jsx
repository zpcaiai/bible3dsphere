import React, { useState, useEffect } from 'react';
import Dashboard from './Dashboard';
import DecisionInput from './DecisionInput';
import DiscernmentResult from './DiscernmentResult';
import ReflectionJournal from './ReflectionJournal';
import './styles.css';

/**
 * SFDS - Spiritual Formation & Discernment System
 * Main Application Component
 * 
 * Design Principles:
 * - Minimal and calm aesthetic
 * - Non-judgmental tone throughout
 * - Focus on reflection, not performance
 * - Acts as a "spiritual mirror", not an oracle
 */

const SFDSApp = ({ onClose }) => {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [pageParams, setPageParams] = useState({});
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Fade in animation
    const timer = setTimeout(() => setIsVisible(true), 50);
    return () => clearTimeout(timer);
  }, []);

  const navigate = (page, params = {}) => {
    setIsVisible(false);
    setTimeout(() => {
      setCurrentPage(page);
      setPageParams(params);
      setIsVisible(true);
    }, 200);
  };

  const handleDecisionSubmit = (formData) => {
    // In real implementation, this would send data to the backend
    console.log('Decision submitted:', formData);
    // Navigate to result page after analysis
    navigate('result', { decisionId: 'temp-id' });
  };

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard onNavigate={navigate} />;
      case 'new-decision':
        return <DecisionInput onNavigate={navigate} onSubmit={handleDecisionSubmit} />;
      case 'result':
        return <DiscernmentResult onNavigate={navigate} resultId={pageParams.decisionId} />;
      case 'journal':
        return <ReflectionJournal onNavigate={navigate} />;
      case 'history':
        // For now, redirect to dashboard with future enhancement note
        return (
          <div className="sfds-page sfds-fade-in">
            <div className="sfds-empty" style={{ paddingTop: '100px' }}>
              <div className="sfds-empty-icon">📚</div>
              <h3 style={{ fontWeight: 500, marginBottom: '12px' }}>完整历史记录</h3>
              <p style={{ color: 'var(--sfds-text-muted)', marginBottom: '24px' }}>
                此功能将在后续版本中完善
              </p>
              <button className="sfds-btn sfds-btn-primary" onClick={() => navigate('dashboard')}>
                返回首页
              </button>
            </div>
          </div>
        );
      default:
        return <Dashboard onNavigate={navigate} />;
    }
  };

  return (
    <div 
      className="sfds-container"
      style={{
        opacity: isVisible ? 1 : 0,
        transition: 'opacity 0.2s ease',
      }}
    >
      {/* Header with close button */}
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        background: 'var(--sfds-bg-card)',
        borderBottom: '1px solid var(--sfds-border)',
        padding: '12px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        zIndex: 100,
        height: '56px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            background: 'linear-gradient(135deg, var(--sfds-accent-teal) 0%, var(--sfds-accent-sage) 100%)',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <span style={{ 
            fontSize: '16px', 
            fontWeight: 600, 
            color: 'var(--sfds-text-primary)',
            letterSpacing: '-0.3px'
          }}>
            灵性决策陪伴
          </span>
        </div>
        
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              padding: '8px',
              cursor: 'pointer',
              color: 'var(--sfds-text-muted)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '8px',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--sfds-bg-secondary)';
              e.currentTarget.style.color = 'var(--sfds-text-primary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = 'var(--sfds-text-muted)';
            }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        )}
      </div>

      {/* Main Content */}
      <div style={{ paddingTop: '56px' }}>
        {renderPage()}
      </div>

      {/* Bottom Navigation */}
      <nav className="sfds-nav">
        <button
          className={`sfds-nav-item ${currentPage === 'dashboard' ? 'active' : ''}`}
          onClick={() => navigate('dashboard')}
        >
          <svg className="sfds-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7"/>
            <rect x="14" y="3" width="7" height="7"/>
            <rect x="14" y="14" width="7" height="7"/>
            <rect x="3" y="14" width="7" height="7"/>
          </svg>
          首页
        </button>

        <button
          className={`sfds-nav-item ${currentPage === 'new-decision' ? 'active' : ''}`}
          onClick={() => navigate('new-decision')}
        >
          <svg className="sfds-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="16"/>
            <line x1="8" y1="12" x2="16" y2="12"/>
          </svg>
          新决定
        </button>

        <button
          className={`sfds-nav-item ${currentPage === 'journal' ? 'active' : ''}`}
          onClick={() => navigate('journal')}
        >
          <svg className="sfds-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
          日记
        </button>

        <button
          className={`sfds-nav-item ${currentPage === 'history' ? 'active' : ''}`}
          onClick={() => navigate('history')}
        >
          <svg className="sfds-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
          历史
        </button>
      </nav>
    </div>
  );
};

export default SFDSApp;
