import appsData from './apps.json';

// Checks if email is free provider
const FREE_EMAILS = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com"];
function isFreeEmail(email) {
  if (!email) return true;
  const domain = email.split('@').pop().toLowerCase();
  return FREE_EMAILS.includes(domain);
}

export async function fetchApps(params = {}) {
  let apps = [...appsData];

  // 1. Search filter
  if (params.search) {
    const term = params.search.toLowerCase();
    apps = apps.filter(
      a =>
        a.name?.toLowerCase().includes(term) ||
        a.developer?.toLowerCase().includes(term) ||
        a.package?.toLowerCase().includes(term)
    );
  }

  // 2. Risk filter
  if (params.risk) {
    const riskLevel = params.risk.toUpperCase();
    apps = apps.filter(a => a.risk?.level === riskLevel);
  }

  // 3. Min Rating filter
  if (params.minRating !== undefined && params.minRating !== null) {
    apps = apps.filter(a => a.rating !== undefined && a.rating >= params.minRating);
  }

  // 4. Score filters
  if (params.minScore !== undefined && params.minScore !== null) {
    apps = apps.filter(a => (a.risk?.score || 0) >= params.minScore);
  }
  if (params.maxScore !== undefined && params.maxScore !== null) {
    apps = apps.filter(a => (a.risk?.score || 0) <= params.maxScore);
  }

  // 5. Sorting
  if (params.sort === 'risk_desc') {
    apps.sort((a, b) => (b.risk?.score || 0) - (a.risk?.score || 0));
  } else if (params.sort === 'risk_asc') {
    apps.sort((a, b) => (a.risk?.score || 0) - (b.risk?.score || 0));
  } else if (params.sort === 'rating_desc') {
    apps.sort((a, b) => (b.rating || 0) - (a.rating || 0));
  } else if (params.sort === 'rating_asc') {
    apps.sort((a, b) => (a.rating || 5) - (b.rating || 5));
  } else if (params.sort === 'name_asc') {
    apps.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
  }

  // 6. Pagination
  const total = apps.length;
  const page = params.page || 1;
  const limit = params.limit || 20;
  const start = (page - 1) * limit;
  const end = start + limit;
  const paginatedData = apps.slice(start, end);

  return {
    total,
    page,
    limit,
    pages: Math.ceil(total / limit),
    data: paginatedData
  };
}

export async function fetchAppDetail(packageId) {
  const detail = appsData.find(a => a.package === packageId);
  if (!detail) {
    throw new Error(`App with package ID ${packageId} not found.`);
  }
  return detail;
}

export async function fetchStats() {
  const total_apps = appsData.length;
  
  if (total_apps === 0) {
    return {
      total_apps: 0,
      level_counts: { HIGH_RISK: 0, CAUTION: 0, LOWER_RISK: 0, INSUFFICIENT_EVIDENCE: 0 },
      average_risk_score: 0.0
    };
  }

  const level_counts = {
    HIGH_RISK: appsData.filter(a => a.risk?.level === 'HIGH_RISK').length,
    CAUTION: appsData.filter(a => a.risk?.level === 'CAUTION').length,
    LOWER_RISK: appsData.filter(a => a.risk?.level === 'LOWER_RISK').length,
    INSUFFICIENT_EVIDENCE: appsData.filter(a => a.risk?.level === 'INSUFFICIENT_EVIDENCE').length
  };

  const validScores = appsData
    .filter(a => a.risk?.level !== 'INSUFFICIENT_EVIDENCE')
    .map(a => a.risk?.score || 0);
  
  const average_risk_score = validScores.length 
    ? Math.round((validScores.reduce((sum, s) => sum + s, 0) / validScores.length) * 10) / 10
    : 0.0;

  return {
    total_apps,
    level_counts,
    average_risk_score
  };
}
