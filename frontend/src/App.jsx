import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  HelpCircle, 
  Search, 
  ExternalLink, 
  X, 
  Star, 
  ArrowRight, 
  UserCheck, 
  AlertCircle, 
  FileText,
  Mail,
  Globe,
  Settings,
  Shield,
  ThumbsUp,
  MessageSquare
} from 'lucide-react';
import { fetchApps, fetchAppDetail, fetchStats } from './api';

export default function App() {
  const [apps, setApps] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Search & Filter state
  const [search, setSearch] = useState('');
  const [risk, setRisk] = useState('');
  const [sort, setSort] = useState('risk_desc');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalAppsCount, setTotalAppsCount] = useState(0);
  
  // Selected App detail drawer state
  const [selectedPackage, setSelectedPackage] = useState(null);
  const [selectedApp, setSelectedApp] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Fetch apps lists and stats
  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const statsData = await fetchStats();
        setStats(statsData);
        
        const appsData = await fetchApps({
          search,
          risk,
          sort,
          page,
          limit: 12
        });
        
        setApps(appsData.data || []);
        setTotalPages(appsData.pages || 1);
        setTotalAppsCount(appsData.total || 0);
        setError(null);
      } catch (err) {
        setError(err.message || 'Error loading dashboard data. Make sure backend is running.');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [search, risk, sort, page]);

  // Fetch app details when selected
  useEffect(() => {
    if (!selectedPackage) {
      setSelectedApp(null);
      return;
    }
    
    async function loadDetail() {
      setLoadingDetail(true);
      try {
        const detail = await fetchAppDetail(selectedPackage);
        setSelectedApp(detail);
      } catch (err) {
        alert(err.message || 'Error loading app details');
        setSelectedPackage(null);
      } finally {
        setLoadingDetail(false);
      }
    }
    loadDetail();
  }, [selectedPackage]);

  const handleSearchChange = (e) => {
    setSearch(e.target.value);
    setPage(1); // reset to first page
  };

  const handleRiskChange = (e) => {
    setRisk(e.target.value);
    setPage(1);
  };

  const handleSortChange = (e) => {
    setSort(e.target.value);
    setPage(1);
  };

  // Helper: Get Risk Icon
  const getRiskIcon = (level, size = 20) => {
    switch (level) {
      case 'HIGH_RISK':
        return <ShieldAlert size={size} color="var(--risk-danger)" />;
      case 'CAUTION':
        return <AlertTriangle size={size} color="var(--risk-caution)" />;
      case 'LOWER_RISK':
        return <ShieldCheck size={size} color="var(--risk-safe)" />;
      default:
        return <HelpCircle size={size} color="var(--risk-unknown)" />;
    }
  };

  const getRiskClass = (level) => {
    switch (level) {
      case 'HIGH_RISK': return 'danger';
      case 'CAUTION': return 'caution';
      case 'LOWER_RISK': return 'safe';
      default: return 'unknown';
    }
  };

  const formatRiskLevel = (level) => {
    if (!level) return 'UNKNOWN';
    return level.replace('_', ' ');
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-title-section">
          <h1>
            <Shield size={36} color="var(--color-primary)" />
            Loan App Safety Analyzer
          </h1>
          <p>End-to-end evidence-based risk assessment & developer legitimacy directory</p>
        </div>
        <div className="disclaimer-badge">
          <strong>Disclaimer:</strong> This project provides an evidence-based risk assessment from publicly available information. It is not a definitive determination that an app is safe, unsafe, fraudulent, or illegal.
        </div>
      </header>

      {/* Stats Dashboard */}
      {stats && (
        <section className="stats-grid">
          <div className="stat-card">
            <span className="stat-label">Total Analyzed</span>
            <span className="stat-value">{stats.total_apps}</span>
          </div>
          <div className="stat-card danger">
            <span className="stat-label">🔴 High Risk</span>
            <span className="stat-value">{stats.level_counts?.HIGH_RISK || 0}</span>
          </div>
          <div className="stat-card caution">
            <span className="stat-label">🟡 Caution</span>
            <span className="stat-value">{stats.level_counts?.CAUTION || 0}</span>
          </div>
          <div className="stat-card safe">
            <span className="stat-label">🟢 Lower Risk</span>
            <span className="stat-value">{stats.level_counts?.LOWER_RISK || 0}</span>
          </div>
          <div className="stat-card unknown">
            <span className="stat-label">⚫ Insufficient Info</span>
            <span className="stat-value">{stats.level_counts?.INSUFFICIENT_EVIDENCE || 0}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Avg Risk Score</span>
            <span className="stat-value">{stats.average_risk_score}/100</span>
          </div>
        </section>
      )}

      {/* Filters */}
      <section className="filters-panel">
        <div className="search-input-wrapper">
          <Search size={18} className="search-icon" />
          <input 
            type="text" 
            placeholder="Search by app name, developer, or package..."
            value={search}
            onChange={handleSearchChange}
          />
        </div>
        
        <div className="filter-group">
          <label>Risk Level</label>
          <select className="filter-select" value={risk} onChange={handleRiskChange}>
            <option value="">All Levels</option>
            <option value="HIGH_RISK">🔴 High Risk</option>
            <option value="CAUTION">🟡 Caution</option>
            <option value="LOWER_RISK">🟢 Lower Risk</option>
            <option value="INSUFFICIENT_EVIDENCE">⚫ Insufficient Evidence</option>
          </select>
        </div>

        <div className="filter-group">
          <label>Sort By</label>
          <select className="filter-select" value={sort} onChange={handleSortChange}>
            <option value="risk_desc">Highest Risk Score</option>
            <option value="risk_asc">Lowest Risk Score</option>
            <option value="rating_desc">Highest Play Store Rating</option>
            <option value="rating_asc">Lowest Play Store Rating</option>
            <option value="name_asc">App Name (A-Z)</option>
          </select>
        </div>
      </section>

      {/* Dashboard Error Alert */}
      {error && (
        <div className="detail-section" style={{ borderColor: 'var(--risk-danger)', background: 'var(--risk-danger-bg)' }}>
          <div className="detail-section-title" style={{ color: 'var(--risk-danger)' }}>
            <AlertCircle size={20} /> Connection Error
          </div>
          <p style={{ fontSize: '0.9rem' }}>{error}</p>
        </div>
      )}

      {/* Apps Cards List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          <p>Running analytics and fetching loan app database...</p>
        </div>
      ) : (
        <>
          {apps.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '4rem', background: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
              <p style={{ color: 'var(--text-muted)' }}>No loan applications match the search/filter criteria.</p>
            </div>
          ) : (
            <section className="apps-grid">
              {apps.map((app) => (
                <div 
                  key={app.package} 
                  className="app-card"
                  onClick={() => setSelectedPackage(app.package)}
                >
                  <div className="app-card-header">
                    <img 
                      src={app.icon || 'https://via.placeholder.com/64'} 
                      alt={app.name} 
                      className="app-icon"
                      onError={(e) => { e.target.src = 'https://via.placeholder.com/64'; }}
                    />
                    <div className="app-info-meta">
                      <h3 className="app-name" title={app.name}>{app.name}</h3>
                      <div className="app-developer">{app.developer}</div>
                      <div className="app-store-stats">
                        <span className="app-rating-pill">
                          <Star size={12} fill="currentColor" />
                          {app.rating || 'N/A'}
                        </span>
                        <span>•</span>
                        <span>{app.installs || '0+'} Installs</span>
                      </div>
                    </div>
                  </div>

                  <p className="app-key-reason">
                    {app.risk?.reasons?.[0] || 'No critical warning flags found.'}
                  </p>

                  <div className="risk-indicator-section">
                    <span className={`risk-level-badge ${app.risk?.level?.toLowerCase()}`}>
                      {formatRiskLevel(app.risk?.level)}
                    </span>
                    <span className={`risk-score-circle ${getRiskClass(app.risk?.level)}`}>
                      {app.risk?.level === 'INSUFFICIENT_EVIDENCE' ? '—' : `${app.risk?.score}/100`}
                    </span>
                  </div>
                </div>
              ))}
            </section>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination-controls">
              <button 
                className="pagination-btn"
                disabled={page === 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
              >
                Previous
              </button>
              <span className="pagination-info">
                Page {page} of {totalPages} ({totalAppsCount} apps)
              </span>
              <button 
                className="pagination-btn"
                disabled={page === totalPages}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      {/* App Details Modal/Drawer */}
      {selectedPackage && (
        <div className="modal-overlay" onClick={() => setSelectedPackage(null)}>
          <div className="modal-content-wrapper" onClick={(e) => e.stopPropagation()}>
            {loadingDetail ? (
              <div style={{ display: 'flex', flex1: 1, alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                <p>Loading application details & reviews data...</p>
              </div>
            ) : selectedApp ? (
              <>
                <header className="modal-header">
                  <div className="modal-header-app">
                    <img 
                      src={selectedApp.icon || 'https://via.placeholder.com/64'} 
                      alt={selectedApp.name} 
                      onError={(e) => { e.target.src = 'https://via.placeholder.com/64'; }}
                    />
                    <div>
                      <h2>{selectedApp.name}</h2>
                      <div className="app-developer" style={{ whiteSpace: 'normal' }}>{selectedApp.developer}</div>
                    </div>
                  </div>
                  <button className="modal-close-btn" onClick={() => setSelectedPackage(null)}>
                    <X size={20} />
                  </button>
                </header>

                <div className="modal-body">
                  {/* Overview Grid */}
                  <section className="metadata-fields-grid">
                    <div className="meta-field-item">
                      <span className="label">Package ID</span>
                      <span className="value">{selectedApp.package}</span>
                    </div>
                    <div className="meta-field-item">
                      <span className="label">Rating</span>
                      <span className="value" style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
                        <Star size={14} fill="var(--risk-caution)" color="var(--risk-caution)" />
                        {selectedApp.rating || 'N/A'} ({selectedApp.reviews_count?.toLocaleString() || 0} reviews)
                      </span>
                    </div>
                    <div className="meta-field-item">
                      <span className="label">Installs</span>
                      <span className="value">{selectedApp.installs || 'N/A'}</span>
                    </div>
                    <div className="meta-field-item">
                      <span className="label">Last Updated</span>
                      <span className="value">{selectedApp.last_updated || 'N/A'}</span>
                    </div>
                    <div className="meta-field-item">
                      <span className="label">Play Store Link</span>
                      <a href={selectedApp.play_store_url} target="_blank" rel="noreferrer" className="value">
                        Google Play Store <ExternalLink size={12} />
                      </a>
                    </div>
                    <div className="meta-field-item">
                      <span className="label">Privacy Policy</span>
                      {selectedApp.privacy_policy_url ? (
                        <a href={selectedApp.privacy_policy_url} target="_blank" rel="noreferrer" className="value">
                          View Policy <ExternalLink size={12} />
                        </a>
                      ) : (
                        <span className="value" style={{ color: 'var(--risk-danger)' }}>Missing Policy URL</span>
                      )}
                    </div>
                  </section>

                  {/* Risk Assessment Section */}
                  <section className="detail-section" style={{ borderLeft: `5px solid var(--risk-${getRiskClass(selectedApp.risk?.level)})` }}>
                    <h3 className="detail-section-title">
                      {getRiskIcon(selectedApp.risk?.level, 22)}
                      Risk Evaluation Report
                    </h3>
                    
                    <div className="risk-assessment-summary">
                      <div className={`risk-summary-score-large ${getRiskClass(selectedApp.risk?.level)}`}>
                        <span className="score-num">{selectedApp.risk?.level === 'INSUFFICIENT_EVIDENCE' ? '—' : selectedApp.risk?.score}</span>
                        <span className="score-label">Score</span>
                      </div>
                      <div className="risk-summary-text-block">
                        <h3 className={getRiskClass(selectedApp.risk?.level)}>
                          {formatRiskLevel(selectedApp.risk?.level)}
                        </h3>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                          Scoring based on {selectedApp.signals?.length || 0} active reputation signals
                        </p>
                      </div>
                    </div>

                    <div style={{ marginTop: '0.5rem' }}>
                      <h4 style={{ fontSize: '0.9rem', marginBottom: '0.4rem', color: '#fff' }}>Evidence-Backed Reasons</h4>
                      <ul className={`detail-bullet-list ${selectedApp.risk?.level === 'HIGH_RISK' ? 'danger' : ''}`}>
                        {selectedApp.risk?.reasons?.map((reason, idx) => (
                          <li key={idx}>{reason}</li>
                        ))}
                      </ul>
                    </div>

                    {selectedApp.risk?.important_uncertainties?.length > 0 && (
                      <div style={{ marginTop: '0.5rem', background: 'rgba(255,255,255,0.02)', padding: '0.75rem', borderRadius: 'var(--radius-sm)' }}>
                        <h4 style={{ fontSize: '0.85rem', marginBottom: '0.4rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <HelpCircle size={14} /> Analysis Gaps / Uncertainties
                        </h4>
                        <ul style={{ listStyle: 'none', paddingLeft: '0.5rem' }}>
                          {selectedApp.risk.important_uncertainties.map((unc, idx) => (
                            <li key={idx} style={{ fontSize: '0.78rem', color: 'var(--text-muted-dark)', marginBottom: '0.2rem' }}>
                              • {unc}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </section>

                  {/* Permissions Section */}
                  <section className="detail-section">
                    <h3 className="detail-section-title">
                      <Settings size={20} color="var(--color-primary)" />
                      Sensitive Device Permissions
                    </h3>
                    {selectedApp.permissions?.status === 'unavailable' ? (
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted-dark)' }}>
                        Permission manifest could not be programmatically parsed from store metadata.
                      </p>
                    ) : (
                      <>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                          Categorization of sensitive Android permissions requested by the application binary.
                        </p>
                        <div className="perms-grid">
                          {['Contacts', 'SMS', 'Call logs', 'Location', 'Storage', 'Camera', 'Microphone'].map((cat) => {
                            const catPerms = selectedApp.permissions?.sensitive_permissions?.[cat] || [];
                            const isRequested = catPerms.length > 0;
                            return (
                              <div key={cat} className="perm-cat-card" style={{ opacity: isRequested ? 1 : 0.45 }}>
                                <div className={`perm-cat-header ${isRequested ? 'danger-icon' : ''}`}>
                                  {isRequested ? <AlertTriangle size={14} /> : <ShieldCheck size={14} color="var(--text-muted-dark)" />}
                                  {cat}
                                </div>
                                {isRequested ? (
                                  catPerms.map((p, idx) => (
                                    <div key={idx} className="perm-item-tag">{p.split('.').pop()}</div>
                                  ))
                                ) : (
                                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted-dark)', fontStyle: 'italic' }}>Not requested</div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </>
                    )}
                  </section>

                  {/* Reviews Themes & Sentiment Section */}
                  <section className="detail-section">
                    <h3 className="detail-section-title">
                      <MessageSquare size={20} color="var(--color-primary)" />
                      User Review Themes
                    </h3>
                    
                    {selectedApp.reviews_analysis?.sentiment ? (
                      <div className="review-stats-summary">
                        {/* Sentiment breakdown */}
                        <div className="sentiment-breakdown">
                          <h4 style={{ fontSize: '0.85rem', color: '#fff', marginBottom: '0.25rem', textAlign: 'center' }}>
                            Sentiment Breakdown
                          </h4>
                          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textAlign: 'center', marginBottom: '0.5rem' }}>
                            Based on {selectedApp.reviews?.length || 0} reviews sample
                          </p>
                          
                          {[['positive', 'var(--risk-safe)'], ['negative', 'var(--risk-danger)'], ['neutral', 'var(--risk-unknown)']].map(([type, color]) => {
                            const count = selectedApp.reviews_analysis.sentiment[type] || 0;
                            const total = selectedApp.reviews?.length || 1;
                            const percentage = Math.round((count / total) * 100);
                            return (
                              <div key={type} className="sentiment-bar-wrapper">
                                <div className="sentiment-bar-label">
                                  <span style={{ textTransform: 'capitalize' }}>{type}</span>
                                  <span>{percentage}% ({count})</span>
                                </div>
                                <div className="sentiment-bar-bg">
                                  <div 
                                    className={`sentiment-bar-fill ${type}`} 
                                    style={{ width: `${percentage}%` }}
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                        
                        {/* Themes Counts */}
                        <div className="review-themes-list">
                          <h4 style={{ fontSize: '0.85rem', color: '#fff', marginBottom: '0.25rem' }}>Key Flagged Themes</h4>
                          {Object.entries(selectedApp.reviews_analysis.themes || {})
                            .filter(([name, data]) => data.count > 0)
                            .map(([name, data]) => {
                              const isNegativeTheme = !['successful_loan', 'easy_application', 'good_support', 'transparent'].includes(name);
                              return (
                                <div key={name} className={`theme-pill-item ${isNegativeTheme ? 'danger-theme' : ''}`}>
                                  <span className="name">{name.replace('_', ' ')}</span>
                                  <span className="badge">{data.count} mentions</span>
                                </div>
                              );
                            })}
                          {Object.values(selectedApp.reviews_analysis.themes || {}).every(data => data.count === 0) && (
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted-dark)' }}>No matches detected for the pre-defined safety keyword lists.</p>
                          )}
                        </div>
                      </div>
                    ) : (
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted-dark)' }}>No reviews collected for analysis.</p>
                    )}

                    {selectedApp.reviews_analysis?.manipulation?.detected && (
                      <div style={{ marginTop: '0.5rem', border: '1px solid rgba(255,165,0,0.2)', background: 'rgba(255,165,0,0.02)', padding: '0.75rem', borderRadius: 'var(--radius-sm)' }}>
                        <h4 style={{ fontSize: '0.82rem', color: 'var(--risk-caution)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <AlertTriangle size={14} /> Review Manipulation Alert
                        </h4>
                        <ul style={{ listStyle: 'none', paddingLeft: '0.5rem', marginTop: '0.25rem' }}>
                          {selectedApp.reviews_analysis.manipulation.reasons.map((r, idx) => (
                            <li key={idx} style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                              • {r}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </section>

                  {/* Developer legitimacy */}
                  <section className="detail-section">
                    <h3 className="detail-section-title">
                      <UserCheck size={20} color="var(--color-primary)" />
                      Developer & Licensing Legitimacy
                    </h3>
                    <div className="metadata-fields-grid">
                      <div className="meta-field-item">
                        <span className="label">Registered Email</span>
                        <span className="value" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                          <Mail size={12} color="var(--text-muted)" />
                          {selectedApp.developer_email}
                        </span>
                      </div>
                      <div className="meta-field-item">
                        <span className="label">Developer Website</span>
                        {selectedApp.developer_website && selectedApp.developer_website !== 'unknown' ? (
                          <a href={selectedApp.developer_website} target="_blank" rel="noreferrer" className="value">
                            <Globe size={12} /> {selectedApp.developer_website.replace(/(^\w+:|^)\/\//, '')}
                          </a>
                        ) : (
                          <span className="value" style={{ color: 'var(--risk-danger)' }}>Missing Website URL</span>
                        )}
                      </div>
                    </div>
                  </section>

                  {/* Web Research Sources */}
                  <section className="detail-section">
                    <h3 className="detail-section-title">
                      <FileText size={20} color="var(--color-primary)" />
                      External Web Research & Reputation Sources
                    </h3>
                    {selectedApp.web_sources?.length === 0 ? (
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted-dark)' }}>
                        No search references or consumer complaints found on the wider web.
                      </p>
                    ) : (
                      <div className="sources-list">
                        {selectedApp.web_sources?.map((source, idx) => (
                          <div key={idx} className="source-item">
                            <div className="source-item-header">
                              <span className="source-title">{source.title}</span>
                              <span className={`source-type-badge ${source.source_type}`}>
                                {source.source_type}
                              </span>
                            </div>
                            <p className="source-summary">{source.summary}</p>
                            <a 
                              href={source.url} 
                              target="_blank" 
                              rel="noreferrer" 
                              className="source-link-action"
                            >
                              Verify Source <ExternalLink size={10} />
                            </a>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>
                </div>
              </>
            ) : (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                <p>Could not fetch details. Please try again later.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
