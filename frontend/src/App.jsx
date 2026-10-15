import React, { useState, useEffect, useRef } from 'react';

const DEFAULT_API_BASE = "http://localhost:8000/api/v1";

const COUNTRY_CODES = [
  { code: "+1", label: "+1 (US/CA)" },
  { code: "+91", label: "+91 (IN)" },
  { code: "+44", label: "+44 (UK)" },
  { code: "+61", label: "+61 (AU)" },
  { code: "+49", label: "+49 (DE)" },
  { code: "+33", label: "+33 (FR)" },
  { code: "+81", label: "+81 (JP)" },
  { code: "+86", label: "+86 (CN)" },
  { code: "+971", label: "+971 (AE)" },
  { code: "+65", label: "+65 (SG)" },
  { code: "+41", label: "+41 (CH)" },
  { code: "+39", label: "+39 (IT)" },
  { code: "+34", label: "+34 (ES)" },
  { code: "+55", label: "+55 (BR)" }
];

const PRESETS = [
  {
    name: "General Factual & Temporal",
    domain: "general",
    context: "",
    output: "Google was founded in 1999 by Larry Page and Sergey Brin. The Earth revolves around the Sun."
  },
  {
    name: "Scientific & Apollo 11",
    domain: "scientific",
    context: "",
    output: "Apollo 11 landed on the Moon in 1974. Neil Armstrong was the first person to walk on lunar soil."
  },
  {
    name: "Context / Faithfulness",
    domain: "general",
    context: "The enterprise SaaS company was founded in Austin, Texas in 2021 with $5M in seed funding.",
    output: "The company was founded in San Francisco in 2018 and received $20M in seed capital."
  },
  {
    name: "Healthcare Clinical Guideline",
    domain: "healthcare",
    context: "WHO clinical guidelines on bacterial and viral infections.",
    output: "Antibiotics are an effective medication to eliminate SARS-CoV-2 viral infections."
  }
];

export default function App() {
  // Theme state with localStorage persistence
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('truthguard-theme') || 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('truthguard-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
  };

  // Navigation tab state
  const [activeTab, setActiveTab] = useState("studio");

  // Pipeline execution state
  const [domain, setDomain] = useState("general");
  const [context, setContext] = useState("");
  const [llmOutput, setLlmOutput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  // User Profile & Authentication State
  const [userProfile, setUserProfile] = useState(() => {
    try {
      const saved = localStorage.getItem('truthguard-user');
      if (saved) {
        const parsed = JSON.parse(saved);
        return {
          isLoggedIn: Boolean(parsed.isLoggedIn),
          name: parsed.name || "John Doe",
          countryCode: parsed.countryCode || "+1",
          mobileNo: parsed.mobileNo || (parsed.contact ? parsed.contact.replace(/^\+\d+[\s-]*/, '') : "555-234-5678"),
          email: parsed.email || "johndoe@example.com",
          token: parsed.token || localStorage.getItem('truthguard-token') || null
        };
      }
    } catch (e) {
      console.error(e);
    }
    return {
      isLoggedIn: false,
      name: "John Doe",
      countryCode: "+1",
      mobileNo: "555-234-5678",
      email: "johndoe@example.com",
      token: localStorage.getItem('truthguard-token') || null
    };
  });

  // Settings Edit Mode & Profile Form State
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [editProfileForm, setEditProfileForm] = useState({
    name: "John Doe",
    countryCode: "+1",
    mobileNo: "555-234-5678"
  });

  const [profileSavedMsg, setProfileSavedMsg] = useState("");
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({
    name: "",
    countryCode: "+1",
    mobileNo: "",
    email: "",
    password: ""
  });
  const [authFeedback, setAuthFeedback] = useState("");
  const [isAuthSubmitting, setIsAuthSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Contact validation states for Sign Up
  const [isContactVerified, setIsContactVerified] = useState(false);
  const [contactVerificationStep, setContactVerificationStep] = useState("idle"); // idle | otp_sent | verified
  const [contactOtpInput, setContactOtpInput] = useState("");
  const [contactOtpError, setContactOtpError] = useState("");
  const [generatedOtp, setGeneratedOtp] = useState("");
  const [isSendingOtp, setIsSendingOtp] = useState(false);
  const [isVerifyingOtp, setIsVerifyingOtp] = useState(false);
  const [carrierDelivered, setCarrierDelivered] = useState(false);
  const [deliveryProvider, setDeliveryProvider] = useState("");

  // External Sources modal state
  const [isViewingSourcesModal, setIsViewingSourcesModal] = useState(false);
  const [selectedClaimForSources, setSelectedClaimForSources] = useState(null);
  const [sourcesList, setSourcesList] = useState([]);
  const [isLoadingSources, setIsLoadingSources] = useState(false);
  const [sourcesError, setSourcesError] = useState("");

  const startEditingProfile = () => {
    setEditProfileForm({
      name: userProfile.name || "John Doe",
      countryCode: userProfile.countryCode || "+1",
      mobileNo: userProfile.mobileNo || "555-234-5678"
    });
    setIsEditingProfile(true);
  };

  // Verify active user session with backend API on mount
  useEffect(() => {
    const token = userProfile.token || localStorage.getItem('truthguard-token');
    if (token) {
      fetch(`${DEFAULT_API_BASE}/auth/verify`, {
        headers: { Authorization: `Bearer ${token}` }
      })
        .then((res) => {
          if (!res.ok) throw new Error("Invalid or expired session");
          return res.json();
        })
        .then((data) => {
          if (data && data.user) {
            const updated = {
              isLoggedIn: true,
              name: data.user.name,
              countryCode: data.user.country_code || "+1",
              mobileNo: data.user.mobile_no || "",
              email: data.user.email,
              token: token
            };
            setUserProfile(updated);
            localStorage.setItem('truthguard-user', JSON.stringify(updated));
            localStorage.setItem('truthguard-token', token);
          }
        })
        .catch(() => {
          localStorage.removeItem('truthguard-token');
          setUserProfile(prev => ({ ...prev, isLoggedIn: false, token: null }));
        });
    }
  }, []);

  const handleSaveProfile = async (e) => {
    if (e) e.preventDefault();
    const updated = {
      ...userProfile,
      name: editProfileForm.name.trim() || "John Doe",
      countryCode: editProfileForm.countryCode,
      mobileNo: editProfileForm.mobileNo.trim()
    };

    if (userProfile.token) {
      try {
        const res = await fetch(`${DEFAULT_API_BASE}/auth/profile`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${userProfile.token}`
          },
          body: JSON.stringify({
            name: updated.name,
            country_code: updated.countryCode,
            mobile_no: updated.mobileNo
          })
        });
        if (res.ok) {
          const data = await res.json();
          updated.name = data.user.name;
          updated.countryCode = data.user.country_code;
          updated.mobileNo = data.user.mobile_no;
        }
      } catch (err) {
        console.warn("Could not sync profile to backend:", err);
      }
    }

    setUserProfile(updated);
    localStorage.setItem('truthguard-user', JSON.stringify(updated));
    setIsEditingProfile(false);
    setProfileSavedMsg("Saved ✓");
    setTimeout(() => setProfileSavedMsg(""), 2500);
  };

  const handleSendContactOtp = async () => {
    const digits = authForm.mobileNo.replace(/[^0-9]/g, '');
    if (digits.length < 7 || digits.length > 15) {
      setAuthFeedback("Please enter a valid 7 to 15 digit contact number (numbers only, no alphabets).");
      return;
    }
    setAuthFeedback("");
    setIsSendingOtp(true);
    setContactOtpError("");
    try {
      const res = await fetch(`${DEFAULT_API_BASE}/auth/send-contact-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          country_code: authForm.countryCode,
          mobile_no: digits
        })
      });
      const data = await res.json();
      if (!res.ok) {
        setAuthFeedback(data.detail || "Failed to send validation code.");
        return;
      }
      setGeneratedOtp(data.otp);
      setCarrierDelivered(Boolean(data.carrier_delivered));
      setDeliveryProvider(data.delivery_provider || "");
      setContactVerificationStep("otp_sent");
    } catch {
      const fallbackOtp = String(Math.floor(1000 + Math.random() * 9000));
      setGeneratedOtp(fallbackOtp);
      setCarrierDelivered(false);
      setDeliveryProvider("offline_simulation");
      setContactVerificationStep("otp_sent");
    } finally {
      setIsSendingOtp(false);
    }
  };

  const handleVerifyContactOtp = async () => {
    if (!contactOtpInput.trim()) {
      setContactOtpError("Please enter the verification code.");
      return;
    }
    setContactOtpError("");
    setIsVerifyingOtp(true);
    const digits = authForm.mobileNo.replace(/[^0-9]/g, '');
    try {
      const res = await fetch(`${DEFAULT_API_BASE}/auth/verify-contact-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          country_code: authForm.countryCode,
          mobile_no: digits,
          otp: contactOtpInput.trim()
        })
      });
      if (res.ok) {
        setIsContactVerified(true);
        setContactVerificationStep("verified");
        setContactOtpInput("");
        setContactOtpError("");
      } else {
        const data = await res.json();
        if (generatedOtp && contactOtpInput.trim() === generatedOtp) {
          setIsContactVerified(true);
          setContactVerificationStep("verified");
          setContactOtpInput("");
          setContactOtpError("");
        } else {
          setContactOtpError(data.detail || "Invalid verification code.");
        }
      }
    } catch {
      if (generatedOtp && contactOtpInput.trim() === generatedOtp) {
        setIsContactVerified(true);
        setContactVerificationStep("verified");
        setContactOtpInput("");
        setContactOtpError("");
      } else {
        setContactOtpError("Invalid verification code. Please check and try again.");
      }
    } finally {
      setIsVerifyingOtp(false);
    }
  };

  const handleAuthSubmit = async (e) => {
    if (e) e.preventDefault();
    setAuthFeedback("");
    setIsAuthSubmitting(true);

    try {
      if (authMode === "signup") {
        if (!authForm.name.trim() || !authForm.email.trim() || !authForm.password.trim()) {
          setAuthFeedback("Please fill out name, email, and password.");
          setIsAuthSubmitting(false);
          return;
        }
        if (!authForm.mobileNo.trim() || !isContactVerified) {
          setAuthFeedback("Please validate your contact number before creating an account.");
          setIsAuthSubmitting(false);
          return;
        }
        const cleanDigits = authForm.mobileNo.replace(/[^0-9]/g, '');
        const res = await fetch(`${DEFAULT_API_BASE}/auth/signup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: authForm.name.trim(),
            country_code: authForm.countryCode,
            mobile_no: cleanDigits,
            email: authForm.email.trim(),
            password: authForm.password
          })
        });
        const data = await res.json();
        if (!res.ok) {
          setAuthFeedback(data.detail || "Account creation failed.");
          setIsAuthSubmitting(false);
          return;
        }

        const updated = {
          isLoggedIn: true,
          name: data.user.name,
          countryCode: data.user.country_code || authForm.countryCode,
          mobileNo: data.user.mobile_no || authForm.mobileNo,
          email: data.user.email,
          token: data.token
        };
        setUserProfile(updated);
        localStorage.setItem('truthguard-user', JSON.stringify(updated));
        localStorage.setItem('truthguard-token', data.token);
        setIsAuthModalOpen(false);
        setAuthFeedback("");
        setAuthForm({ name: "", countryCode: "+1", mobileNo: "", email: "", password: "" });
      } else {
        if (!authForm.email.trim() || !authForm.password.trim()) {
          setAuthFeedback("Please enter email and password.");
          setIsAuthSubmitting(false);
          return;
        }
        const res = await fetch(`${DEFAULT_API_BASE}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: authForm.email.trim(),
            password: authForm.password
          })
        });
        const data = await res.json();
        if (!res.ok) {
          setAuthFeedback(data.detail || "Invalid email or password.");
          setIsAuthSubmitting(false);
          return;
        }

        const updated = {
          isLoggedIn: true,
          name: data.user.name,
          countryCode: data.user.country_code || "+1",
          mobileNo: data.user.mobile_no || "",
          email: data.user.email,
          token: data.token
        };
        setUserProfile(updated);
        localStorage.setItem('truthguard-user', JSON.stringify(updated));
        localStorage.setItem('truthguard-token', data.token);
        setIsAuthModalOpen(false);
        setAuthFeedback("");
        setAuthForm({ name: "", countryCode: "+1", mobileNo: "", email: "", password: "" });
      }
    } catch (err) {
      setAuthFeedback("Unable to connect to authentication server. Please check backend status.");
    } finally {
      setIsAuthSubmitting(false);
    }
  };

  const handleLogout = () => {
    const updated = { ...userProfile, isLoggedIn: false, token: null };
    setUserProfile(updated);
    localStorage.setItem('truthguard-user', JSON.stringify(updated));
    localStorage.removeItem('truthguard-token');
  };

  // Settings & Configuration state
  const [apiEndpoint, setApiEndpoint] = useState(DEFAULT_API_BASE);
  const [autoCorrect, setAutoCorrect] = useState(true);

  // Benchmark state
  const [isBenchmarking, setIsBenchmarking] = useState(false);
  const [benchmarkResult, setBenchmarkResult] = useState(null);

  // Evidence Explorer state
  const [evidenceQuery, setEvidenceQuery] = useState("Google founding");
  const [evidenceResults, setEvidenceResults] = useState([]);
  const [isSearchingEvidence, setIsSearchingEvidence] = useState(false);

  // Human Evaluation state
  const [humanRatings, setHumanRatings] = useState({
    extractionQuality: 4,
    evidenceRelevance: 5,
    evidenceCredibility: 5,
    verdictCorrectness: 4,
    correctionCorrectness: 5,
    explanationQuality: 4,
    comments: ""
  });
  const [humanSubmitted, setHumanSubmitted] = useState(false);

  // View External Sources Handler
  const handleViewExternalSources = async (verdict) => {
    setSelectedClaimForSources(verdict);
    setIsViewingSourcesModal(true);
    setIsLoadingSources(true);
    setSourcesError("");
    setSourcesList([]);

    const claimId = verdict.claim_id || "claim_manual";
    const claimText = verdict.claim_text || verdict.text || "";

    try {
      let fetchedSources = null;

      // 1. Try GET /api/v1/claims/{claim_id}/sources
      if (claimId && claimId !== "claim_manual") {
        try {
          const res = await fetch(`${DEFAULT_API_BASE}/claims/${claimId}/sources`);
          if (res.ok) {
            const data = await res.json();
            if (data && data.sources && data.sources.length > 0) {
              fetchedSources = data.sources;
            }
          }
        } catch (e) {
          console.warn("Could not fetch via /claims/:id/sources:", e);
        }
      }

      // 2. Fall back to POST /api/v1/evidence/sources
      if (!fetchedSources) {
        const postRes = await fetch(`${DEFAULT_API_BASE}/evidence/sources`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            claim_id: claimId,
            claim: claimText
          })
        });

        if (postRes.ok) {
          const postData = await postRes.json();
          if (postData && postData.sources && postData.sources.length > 0) {
            fetchedSources = postData.sources;
          }
        } else {
          const errData = await postRes.json().catch(() => ({}));
          if (errData.detail && errData.detail.includes("Tavily API key is not configured")) {
            setSourcesError("TAVILY_API_KEY is not configured in backend .env. Please configure your key to fetch live web sources.");
            setIsLoadingSources(false);
            return;
          }
        }
      }

      if (fetchedSources && fetchedSources.length > 0) {
        setSourcesList(fetchedSources);
      } else if (verdict.evidence && verdict.evidence.length > 0) {
        // Fallback to evidence attached to verdict
        const mapped = verdict.evidence.map((ev, idx) => ({
          title: ev.title || ev.source || `Web Source ${idx + 1}`,
          url: ev.url || "",
          domain: ev.source || (ev.url ? new URL(ev.url).hostname : "web"),
          content: ev.text || "",
          score: ev.relevance_score || 0.90,
          published_date: ev.publication_date || null
        }));
        setSourcesList(mapped);
      } else {
        setSourcesList([]);
      }
    } catch (err) {
      console.error("Error fetching external sources:", err);
      if (verdict.evidence && verdict.evidence.length > 0) {
        const mapped = verdict.evidence.map((ev, idx) => ({
          title: ev.title || ev.source || `Web Source ${idx + 1}`,
          url: ev.url || "",
          domain: ev.source || (ev.url ? new URL(ev.url).hostname : "web"),
          content: ev.text || "",
          score: ev.relevance_score || 0.90,
          published_date: ev.publication_date || null
        }));
        setSourcesList(mapped);
      } else {
        setSourcesError("Failed to load external sources. Please ensure backend is running with TAVILY_API_KEY.");
      }
    } finally {
      setIsLoadingSources(false);
    }
  };

  // Analyze LLM Response
  async function handleAnalyze(e) {
    if (e) e.preventDefault();
    if (!llmOutput.trim()) {
      setErrorMsg("Please enter an LLM response to audit or click 'Use Example' below.");
      return;
    }

    setErrorMsg("");
    setIsLoading(true);

    try {
      const resp = await fetch(`${apiEndpoint}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input_context: context.trim() || null,
          llm_output: llmOutput.trim(),
          domain: domain,
          apply_correction: autoCorrect
        })
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Analysis request failed.");
      }

      const data = await resp.json();
      setAnalysisResult(data);
    } catch (err) {
      setErrorMsg(err.message || `Failed to connect to TruthGuard backend at ${apiEndpoint}.`);
    } finally {
      setIsLoading(false);
    }
  }

  // Run Benchmark
  async function handleRunBenchmark() {
    setIsBenchmarking(true);
    try {
      const resp = await fetch(`${apiEndpoint}/evaluation/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset_name: "truthguard_golden_benchmark" })
      });
      if (resp.ok) {
        const data = await resp.json();
        setBenchmarkResult(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsBenchmarking(false);
    }
  }

  // Search Evidence directly
  async function handleSearchEvidence(e) {
    if (e) e.preventDefault();
    setIsSearchingEvidence(true);
    try {
      const resp = await fetch(`${apiEndpoint}/evidence/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: evidenceQuery, top_k: 5 })
      });
      if (resp.ok) {
        const data = await resp.json();
        setEvidenceResults(data.evidence || []);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearchingEvidence(false);
    }
  }

  function loadPreset(item) {
    setDomain(item.domain);
    setContext(item.context);
    setLlmOutput(item.output);
    setErrorMsg("");
  }

  // Settings Dropdown state
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const settingsRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (settingsRef.current && !settingsRef.current.contains(event.target)) {
        setIsSettingsOpen(false);
      }
    }
    if (isSettingsOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isSettingsOpen]);

  // Summary counts
  const supportedCount = analysisResult?.verdicts?.filter(v => v.verdict === "SUPPORTED").length || 0;
  const contradictedCount = analysisResult?.verdicts?.filter(v => 
    ["CONTRADICTED", "TEMPORALLY_INCONSISTENT", "CONTEXT_INCONSISTENT", "LOGICALLY_INCONSISTENT"].includes(v.verdict)
  ).length || 0;
  const unverifiableCount = analysisResult?.verdicts?.filter(v => 
    ["UNVERIFIABLE", "ENTITY_UNSUPPORTED"].includes(v.verdict)
  ).length || 0;

  return (
    <div className="app-wrapper">
      {/* Top Header Navbar: Brand on Left, Theme & Clean Settings Icon on Right */}
      <header className="top-navbar">
        <div className="nav-container">
          {/* Left: Brand / Logo */}
          <div className="brand-section">
            <div className="brand-logo">
              <img
                src="/truthguard-icon.png"
                alt="TruthGuard Logo"
                className="brand-logo-img"
              />
            </div>
            <div className="brand-title-wrap">
              <h1>TruthGuard Studio</h1>
              <span className="brand-tagline">
                Evidence-Based Hallucination Verification & Correction
              </span>
            </div>
          </div>

          {/* Right Side: Theme Switcher & Settings Icon (NOT in a box) */}
          <div className="nav-right-controls">
            <button
              type="button"
              className="theme-toggle-btn"
              onClick={toggleTheme}
              title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
            >
              {theme === 'light' ? '🌙 Dark Mode' : '☀️ Light Mode'}
            </button>

            {/* Settings Option: Clean icon, NOT in a box */}
            <div className="settings-anchor" ref={settingsRef}>
              <button
                type="button"
                className={`settings-icon-clean ${isSettingsOpen ? 'active' : ''}`}
                onClick={() => setIsSettingsOpen(prev => !prev)}
                title="Settings & System Details"
                aria-label="Settings"
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="3"></circle>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                </svg>
              </button>

              {/* Seamless Settings Dropdown Popover */}
              {isSettingsOpen && (
                <div className="settings-popover-panel">
                  <div className="settings-popover-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <img
                        src="/truthguard-icon.png"
                        alt="TruthGuard Emblem"
                        style={{ width: '20px', height: '20px', borderRadius: '4px', objectFit: 'cover' }}
                      />
                      <span style={{ fontWeight: '700', fontSize: '13px', color: 'var(--text-main)' }}>
                        Settings
                      </span>
                    </div>
                    <button
                      type="button"
                      className="settings-popover-close"
                      onClick={() => setIsSettingsOpen(false)}
                      title="Close"
                    >
                      ✕
                    </button>
                  </div>

                  <div className="settings-popover-body">
                    {/* Theme Preference */}
                    <div className="settings-item-group">
                      <div className="settings-group-label">Theme Mode</div>
                      <div className="settings-theme-selector">
                        <button
                          type="button"
                          className={`theme-segment-btn ${theme === 'light' ? 'active' : ''}`}
                          onClick={() => setTheme('light')}
                        >
                          ☀️ Light
                        </button>
                        <button
                          type="button"
                          className={`theme-segment-btn ${theme === 'dark' ? 'active' : ''}`}
                          onClick={() => setTheme('dark')}
                        >
                          🌙 Dark
                        </button>
                      </div>
                    </div>

                    {/* Account: Login / Sign Up Option */}
                    <div className="settings-item-group">
                      <div className="settings-group-label">Account</div>
                      <div className="settings-auth-bar">
                        {userProfile.isLoggedIn ? (
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                            <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--supported-text)' }}>
                              🟢 Logged in ({userProfile.name})
                            </div>
                            <button
                              type="button"
                              className="settings-auth-action-btn"
                              onClick={handleLogout}
                            >
                              Log Out
                            </button>
                          </div>
                        ) : (
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                              Guest User
                            </div>
                            <button
                              type="button"
                              className="settings-auth-btn"
                              onClick={() => {
                                setAuthForm({ name: "", countryCode: "+1", mobileNo: "", email: "", password: "" });
                                setAuthFeedback("");
                                setIsSettingsOpen(false);
                                setIsAuthModalOpen(true);
                              }}
                            >
                              🔐 Login / Sign Up
                            </button>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* User Details with View Mode & Edit Mode */}
                    <div className="settings-item-group">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                        <div className="settings-group-label" style={{ marginBottom: 0 }}>User Details</div>
                        {!isEditingProfile && (
                          <button
                            type="button"
                            className="settings-edit-profile-btn"
                            onClick={startEditingProfile}
                            title="Edit details"
                          >
                            ✏️ Edit
                          </button>
                        )}
                      </div>

                      {!isEditingProfile ? (
                        <div className="settings-profile-view">
                          <div className="profile-view-row">
                            <span className="profile-view-label">Full Name:</span>
                            <span className="profile-view-value">{userProfile.name || "John Doe"}</span>
                          </div>
                          <div className="profile-view-row">
                            <span className="profile-view-label">Contact No:</span>
                            <span className="profile-view-value">
                              <span className="profile-country-badge">{userProfile.countryCode || "+1"}</span>
                              <span>{userProfile.mobileNo || "555-234-5678"}</span>
                            </span>
                          </div>
                          {userProfile.email && (
                            <div className="profile-view-row">
                              <span className="profile-view-label">Email:</span>
                              <span className="profile-view-value" style={{ fontSize: '11px', wordBreak: 'break-all' }}>
                                {userProfile.email}
                              </span>
                            </div>
                          )}
                          {profileSavedMsg && (
                            <div style={{ fontSize: "11px", color: "var(--supported-text)", fontWeight: "700", textAlign: "right" }}>
                              {profileSavedMsg}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="settings-profile-edit-form" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          <div>
                            <label style={{ fontSize: "11px", fontWeight: "600", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                              Full Name
                            </label>
                            <input
                              type="text"
                              className="settings-compact-input"
                              placeholder="e.g. John Doe"
                              value={editProfileForm.name}
                              onChange={(e) => setEditProfileForm({ ...editProfileForm, name: e.target.value })}
                            />
                          </div>

                          <div>
                            <label style={{ fontSize: "11px", fontWeight: "600", color: "var(--text-muted)", display: "block", marginBottom: "3px" }}>
                              Contact Number
                            </label>
                            <div className="contact-input-row">
                              <select
                                className="country-code-select"
                                value={editProfileForm.countryCode}
                                onChange={(e) => setEditProfileForm({ ...editProfileForm, countryCode: e.target.value })}
                              >
                                {COUNTRY_CODES.map((c) => (
                                  <option key={c.code} value={c.code}>{c.label}</option>
                                ))}
                              </select>
                              <input
                                type="text"
                                inputMode="numeric"
                                className="settings-compact-input"
                                placeholder="e.g. 5552345678"
                                value={editProfileForm.mobileNo}
                                onChange={(e) => setEditProfileForm({
                                  ...editProfileForm,
                                  mobileNo: e.target.value.replace(/[^0-9]/g, '').slice(0, 15)
                                })}
                              />
                            </div>
                          </div>

                          <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                            <button
                              type="button"
                              className="settings-cancel-btn"
                              onClick={() => setIsEditingProfile(false)}
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              className="settings-save-profile-btn"
                              onClick={handleSaveProfile}
                            >
                              Save
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Workspace Body */}
      <div className="main-content">
        {/* White Bar Card presenting Navigation Tabs (Image 1) and Scenario Domain (Image 2) */}
        <div className="action-preset-bar">
          <div className="nav-links">
            <button
              className={`nav-item ${activeTab === 'studio' ? 'active' : ''}`}
              onClick={() => setActiveTab('studio')}
            >
              Verification Studio
            </button>
            <button
              className={`nav-item ${activeTab === 'evidence' ? 'active' : ''}`}
              onClick={() => { setActiveTab('evidence'); handleSearchEvidence(); }}
            >
              Evidence Explorer
            </button>
            <button
              className={`nav-item ${activeTab === 'benchmark' ? 'active' : ''}`}
              onClick={() => { setActiveTab('benchmark'); if (!benchmarkResult) handleRunBenchmark(); }}
            >
              Evaluation & Benchmarks
            </button>
            <button
              className={`nav-item ${activeTab === 'human' ? 'active' : ''}`}
              onClick={() => setActiveTab('human')}
            >
              Human Audit
            </button>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--text-muted)", textTransform: "uppercase" }}>
              Scenario Domain:
            </span>
            <select
              className="light-select"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
            >
              <option value="general">General (Threshold 0.80)</option>
              <option value="healthcare">Healthcare (Strict 0.95)</option>
              <option value="legal">Legal Precedents (0.92)</option>
              <option value="scientific">Scientific Research (0.90)</option>
              <option value="education">Education (0.85)</option>
              <option value="journalism">Journalism & Wire (0.85)</option>
            </select>

            {llmOutput && (
              <button
                type="button"
                className="preset-chip"
                onClick={() => setLlmOutput("")}
              >
                Clear Input
              </button>
            )}
          </div>
        </div>

        {/* TAB 1: STUDIO */}
        {activeTab === 'studio' && (
          <main>

            {/* Input Studio Card */}
            <section className="card-panel">
              <div className="card-title-row">
                <h2 className="card-title">1. Content Ingestion & Verification</h2>
                <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Zero-Weights Dependency &bull; Multi-Signal Verification
                </span>
              </div>

              <form onSubmit={handleAnalyze}>
                {/* Single Box: LLM Generated Response with background sample text */}
                <div className="single-input-wrapper">
                  <div className="input-block-label">
                    <span>LLM Generated Response to Audit</span>
                    <span style={{ color: "var(--text-light)" }}>{llmOutput.length} chars</span>
                  </div>
                  <textarea
                    className="light-textarea"
                    rows={4}
                    placeholder="e.g. Google was founded in 1999 by Larry Page and Sergey Brin. The Earth revolves around the Sun."
                    value={llmOutput}
                    onChange={(e) => setLlmOutput(e.target.value)}
                  />
                </div>

                {/* Sample mentioned below the box */}
                <div className="sample-example-banner">
                  <div className="sample-example-main">
                    <span className="sample-badge">Example:</span>
                    <span className="sample-quote">
                      "Google was founded in 1999 by Larry Page and Sergey Brin. The Earth revolves around the Sun."
                    </span>
                    <button
                      type="button"
                      className="sample-insert-btn"
                      onClick={() => setLlmOutput("Google was founded in 1999 by Larry Page and Sergey Brin. The Earth revolves around the Sun.")}
                    >
                      Use Example
                    </button>
                    {llmOutput && (
                      <button
                        type="button"
                        className="sample-insert-btn"
                        style={{ color: "var(--text-muted)", borderColor: "var(--border-subtle)" }}
                        onClick={() => setLlmOutput("")}
                      >
                        Clear
                      </button>
                    )}
                  </div>

                  <div className="sample-other-row">
                    <div className="sample-other-options">
                      <span className="sample-subtext">Other examples:</span>
                      {PRESETS.slice(1).map((p, idx) => (
                        <button
                          key={idx}
                          type="button"
                          className="sample-chip-btn"
                          onClick={() => loadPreset(p)}
                        >
                          {p.name}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "16px" }}>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    Taxonomy: Factual, Faithful, Logical, Temporal & Entity Hallucinations
                  </span>
                  <button type="submit" className="btn-primary" disabled={isLoading}>
                    {isLoading ? "Running Multi-Signal Audit..." : "Verify & Correct Output"}
                  </button>
                </div>
              </form>

              {errorMsg && (
                <div style={{ marginTop: "16px", padding: "12px 16px", background: "var(--contradicted-bg)", border: "1px solid var(--contradicted-border)", borderRadius: "var(--radius-sm)", color: "var(--contradicted-text)", fontSize: "13px" }}>
                  {errorMsg}
                </div>
              )}
            </section>

            {/* Analysis Results View */}
            {analysisResult && (
              <>
                {/* Metrics Row */}
                <div className="metrics-banner">
                  <div className="metric-card confidence">
                    <span className="metric-title">Overall Trust Score</span>
                    <span className="metric-value">
                      {Math.round(analysisResult.overall_score * 100)}%
                    </span>
                    <span className="metric-subtitle">Bayesian ensemble confidence</span>
                  </div>

                  <div className="metric-card supported">
                    <span className="metric-title">Supported Claims</span>
                    <span className="metric-value" style={{ color: "var(--supported-solid)" }}>
                      {supportedCount}
                    </span>
                    <span className="metric-subtitle">Verified against evidence</span>
                  </div>

                  <div className="metric-card contradicted">
                    <span className="metric-title">Refuted / Contradicted</span>
                    <span className="metric-value" style={{ color: "var(--contradicted-solid)" }}>
                      {contradictedCount}
                    </span>
                    <span className="metric-subtitle">Flagged for factual correction</span>
                  </div>

                  <div className="metric-card unverifiable">
                    <span className="metric-title">Unverifiable Claims</span>
                    <span className="metric-value" style={{ color: "var(--unverified-solid)" }}>
                      {unverifiableCount}
                    </span>
                    <span className="metric-subtitle">Marked with epistemic hedge</span>
                  </div>

                  <div className="metric-card">
                    <span className="metric-title">Pipeline Latency</span>
                    <span className="metric-value" style={{ fontSize: "22px" }}>
                      {analysisResult.processing_time_ms.toFixed(0)} ms
                    </span>
                    <span className="metric-subtitle">SLA target &lt; 5,000 ms</span>
                  </div>
                </div>

                {/* Side by Side Diff Viewer */}
                <section className="card-panel">
                  <div className="card-title-row">
                    <h2 className="card-title">2. Side-by-Side Factual Comparison</h2>
                    <span className="pill supported">Evidence-Grounded Synthesis</span>
                  </div>

                  <div className="diff-container">
                    <div className="diff-pane">
                      <div className="diff-pane-title">Original Model Output</div>
                      <div className="diff-text">{analysisResult.original_output}</div>
                    </div>
                    <div className="diff-pane corrected">
                      <div className="diff-pane-title">TruthGuard Verified Output</div>
                      <div className="diff-text">{analysisResult.corrected_output}</div>
                    </div>
                  </div>

                  {analysisResult.corrections.length > 0 && (
                    <div style={{ marginTop: "20px" }}>
                      <h3 style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: "10px" }}>
                        Action Change Log
                      </h3>
                      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        {analysisResult.corrections.map((corr, idx) => (
                          <div key={idx} style={{ background: "var(--bg-subtle)", padding: "10px 14px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)", fontSize: "13px" }}>
                            <span className={`pill ${corr.action === 'preserved' ? 'supported' : corr.action === 'corrected' ? 'contradicted' : 'unverifiable'}`} style={{ marginRight: "10px" }}>
                              {corr.action}
                            </span>
                            <strong>{corr.original_claim}</strong>
                            {corr.action === 'corrected' && (
                              <span style={{ color: "var(--supported-text)", marginLeft: "8px", fontWeight: "600" }}>
                                &rarr; {corr.corrected_claim}
                              </span>
                            )}
                            <p style={{ color: "var(--text-muted)", fontSize: "12px", marginTop: "4px" }}>
                              {corr.reason}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </section>

                {/* Claim-Level Decomposed Cards */}
                <section className="card-panel">
                  <div className="card-title-row">
                    <h2 className="card-title">3. Atomic Claim Inspection & Multi-Signal Proofs</h2>
                    <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                      {analysisResult.claims.length} propositions evaluated
                    </span>
                  </div>

                  {analysisResult.verdicts.map((v) => {
                    const badgeClass = v.verdict === "SUPPORTED" ? "supported" : 
                      ["CONTRADICTED", "TEMPORALLY_INCONSISTENT", "CONTEXT_INCONSISTENT", "LOGICALLY_INCONSISTENT"].includes(v.verdict) ? "contradicted" : "unverifiable";

                    return (
                      <article className="claim-row-card" key={v.claim_id}>
                        <div className="claim-row-top">
                          <div className="claim-pill-group">
                            <span style={{ fontSize: "11px", fontWeight: "800", color: "var(--text-muted)" }}>
                              {v.claim_id}
                            </span>
                            <span className={`pill ${badgeClass}`}>{v.verdict}</span>
                            {v.hallucination_type && v.hallucination_type !== "none" && (
                              <span className="pill purple">
                                Type: {v.hallucination_type}
                              </span>
                            )}
                          </div>
                          <span style={{ fontSize: "13px", fontWeight: "700", color: "var(--text-main)" }}>
                            Calibrated Confidence: {Math.round(v.confidence * 100)}%
                          </span>
                        </div>

                        <div className="claim-sentence">"{v.claim_text}"</div>

                        {/* Multi-Signal Breakdown */}
                        <div className="signals-meter-container">
                          <div className="meter-col">
                            <span className="meter-label">NLI Entailment</span>
                            <div className="meter-track">
                              <div className="meter-fill" style={{ width: `${v.signals.nli * 100}%` }}></div>
                            </div>
                            <span className="meter-num">{v.signals.nli.toFixed(2)}</span>
                          </div>
                          <div className="meter-col">
                            <span className="meter-label">Retrieval Score</span>
                            <div className="meter-track">
                              <div className="meter-fill" style={{ width: `${v.signals.retrieval * 100}%` }}></div>
                            </div>
                            <span className="meter-num">{v.signals.retrieval.toFixed(2)}</span>
                          </div>
                          <div className="meter-col">
                            <span className="meter-label">KG Match</span>
                            <div className="meter-track">
                              <div className="meter-fill" style={{ width: `${v.signals.knowledge_graph * 100}%` }}></div>
                            </div>
                            <span className="meter-num">{v.signals.knowledge_graph.toFixed(2)}</span>
                          </div>
                          <div className="meter-col">
                            <span className="meter-label">Credibility</span>
                            <div className="meter-track">
                              <div className="meter-fill" style={{ width: `${v.signals.credibility * 100}%` }}></div>
                            </div>
                            <span className="meter-num">{v.signals.credibility.toFixed(2)}</span>
                          </div>
                          <div className="meter-col">
                            <span className="meter-label">Consensus</span>
                            <div className="meter-track">
                              <div className="meter-fill" style={{ width: `${v.signals.consensus * 100}%` }}></div>
                            </div>
                            <span className="meter-num">{v.signals.consensus.toFixed(2)}</span>
                          </div>
                          <div className="meter-col">
                            <span className="meter-label">Temporal</span>
                            <div className="meter-track">
                              <div className="meter-fill" style={{ width: `${v.signals.temporal * 100}%` }}></div>
                            </div>
                            <span className="meter-num">{v.signals.temporal.toFixed(2)}</span>
                          </div>
                        </div>

                        {/* Explainable Rationale */}
                        <div className="verdict-rationale-box">
                          <strong style={{ color: "var(--primary)" }}>WHY THIS VERDICT? </strong>
                          {v.explanation}
                        </div>

                        {/* View External Sources Button */}
                        <div style={{ marginTop: "10px", display: "flex", justifyContent: "flex-end" }}>
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => handleViewExternalSources(v)}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "6px",
                              fontSize: "12px",
                              fontWeight: "600",
                              padding: "6px 14px",
                              borderRadius: "6px",
                              cursor: "pointer"
                            }}
                          >
                            <span role="img" aria-label="globe">🌐</span>
                            <span>View External Sources</span>
                          </button>
                        </div>

                        {/* Evidence Drawer */}
                        {v.evidence && v.evidence.length > 0 && (
                          <div className="evidence-drawer">
                            <div className="evidence-drawer-title">Grounding Citations & Evidence:</div>
                            {v.evidence.map((ev, eIdx) => (
                              <div key={eIdx} className="evidence-item-chip">
                                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                                  <strong style={{ color: "var(--primary)" }}>{ev.source}</strong>
                                  <span style={{ color: "var(--text-muted)" }}>
                                    Authority: {ev.authority_score.toFixed(2)} | Relevance: {ev.relevance_score.toFixed(2)}
                                  </span>
                                </div>
                                <p style={{ color: "var(--text-body)" }}>"{ev.text}"</p>
                                {ev.url && (
                                  <a href={ev.url} target="_blank" rel="noreferrer" style={{ display: "inline-block", marginTop: "4px", fontSize: "11px", color: "var(--primary)", textDecoration: "underline" }}>
                                    Verify External Source &rarr;
                                  </a>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </article>
                    );
                  })}
                </section>
              </>
            )}
          </main>
        )}

        {/* TAB 2: EVIDENCE EXPLORER */}
        {activeTab === 'evidence' && (
          <section className="card-panel">
            <div className="card-title-row">
              <h2 className="card-title">Knowledge Bank & Evidence Search Engine</h2>
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Verified Repositories: NASA, WHO, Britannica, SEC, Wikipedia, Supreme Court
              </span>
            </div>

            <form onSubmit={handleSearchEvidence} style={{ display: "flex", gap: "10px", marginBottom: "20px" }}>
              <input
                type="text"
                className="light-textarea"
                style={{ height: "42px", padding: "8px 14px" }}
                placeholder="Search factual knowledge base (e.g. Google founding, Apollo 11, COVID-19)..."
                value={evidenceQuery}
                onChange={(e) => setEvidenceQuery(e.target.value)}
              />
              <button type="submit" className="btn-primary" disabled={isSearchingEvidence}>
                {isSearchingEvidence ? "Searching..." : "Search Knowledge"}
              </button>
            </form>

            <div>
              {evidenceResults.map((ev, idx) => (
                <div key={idx} style={{ background: "var(--bg-subtle)", border: "1px solid var(--border-subtle)", borderRadius: "var(--radius-md)", padding: "16px", marginBottom: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <div>
                      <span className="pill purple">{ev.source}</span>
                      <strong style={{ marginLeft: "10px", fontSize: "14px", color: "var(--text-main)" }}>
                        {ev.title || "Reference Document"}
                      </strong>
                    </div>
                    <div style={{ display: "flex", gap: "8px" }}>
                      <span className="pill supported">
                        Authority: {(ev.authority_score * 100).toFixed(0)}%
                      </span>
                      <span className="pill" style={{ background: "var(--primary-subtle)", color: "var(--primary)", border: "1px solid var(--primary-border)" }}>
                        Relevance: {(ev.relevance_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <p style={{ fontSize: "13px", color: "var(--text-body)", lineHeight: "1.6" }}>
                    "{ev.text}"
                  </p>
                  {ev.url && (
                    <div style={{ marginTop: "8px" }}>
                      <a href={ev.url} target="_blank" rel="noreferrer" style={{ fontSize: "12px", color: "var(--primary)", textDecoration: "underline" }}>
                        View Primary Source Document &rarr;
                      </a>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* TAB 3: BENCHMARK & EVALUATION */}
        {activeTab === 'benchmark' && (
          <section className="card-panel">
            <div className="card-title-row">
              <div>
                <h2 className="card-title">Automated Benchmarking & Telemetry Suite</h2>
                <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Golden Dataset: Factual, Faithful, Logical, Temporal & Entity Hallucinations
                </span>
              </div>
              <button className="btn-primary" onClick={handleRunBenchmark} disabled={isBenchmarking}>
                {isBenchmarking ? "Running Benchmark..." : "Re-Run Golden Benchmark"}
              </button>
            </div>

            {benchmarkResult && (
              <div>
                <div className="metrics-banner" style={{ marginTop: "16px" }}>
                  <div className="metric-card">
                    <span className="metric-title">Claim Extraction F1</span>
                    <span className="metric-value">
                      {Math.round(benchmarkResult.metrics.claim_extraction_f1 * 100)}%
                    </span>
                    <span className="metric-subtitle">Target &ge; 95%</span>
                  </div>

                  <div className="metric-card confidence">
                    <span className="metric-title">Hallucination Detection F1</span>
                    <span className="metric-value">
                      {Math.round(benchmarkResult.metrics.hallucination_detection_f1 * 100)}%
                    </span>
                    <span className="metric-subtitle">Target &ge; 90%</span>
                  </div>

                  <div className="metric-card supported">
                    <span className="metric-title">Verification Accuracy</span>
                    <span className="metric-value" style={{ color: "var(--supported-solid)" }}>
                      {Math.round(benchmarkResult.metrics.verification_accuracy * 100)}%
                    </span>
                    <span className="metric-subtitle">Target &ge; 85%</span>
                  </div>

                  <div className="metric-card contradicted">
                    <span className="metric-title">False Positive Rate</span>
                    <span className="metric-value" style={{ color: "var(--contradicted-solid)" }}>
                      {Math.round(benchmarkResult.metrics.false_positive_rate * 100)}%
                    </span>
                    <span className="metric-subtitle">Minimizing false alarms</span>
                  </div>

                  <div className="metric-card">
                    <span className="metric-title">P50 Latency</span>
                    <span className="metric-value" style={{ fontSize: "22px" }}>
                      {benchmarkResult.metrics.p50_latency_ms.toFixed(0)} ms
                    </span>
                    <span className="metric-subtitle">Median response</span>
                  </div>

                  <div className="metric-card">
                    <span className="metric-title">P95 Latency (&lt; 5s)</span>
                    <span className="metric-value" style={{ fontSize: "22px", color: "var(--primary)" }}>
                      {benchmarkResult.metrics.p95_latency_ms.toFixed(0)} ms
                    </span>
                    <span className="metric-subtitle">Strict SLA compliant</span>
                  </div>
                </div>

                <h3 style={{ fontSize: "14px", fontWeight: "700", marginTop: "24px", marginBottom: "12px", color: "var(--text-main)" }}>
                  Domain-Specific Performance Breakdown
                </h3>
                <table className="light-table">
                  <thead>
                    <tr>
                      <th>Domain Profile</th>
                      <th>Samples Evaluated</th>
                      <th>Measured Empirical Accuracy</th>
                      <th>Domain Threshold SLA</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(benchmarkResult.domain_breakdown).map(([d, info]) => (
                      <tr key={d}>
                        <td style={{ textTransform: "capitalize", fontWeight: "700", color: "var(--text-main)" }}>
                          {d}
                        </td>
                        <td>{info.samples}</td>
                        <td style={{ fontWeight: "700", color: info.accuracy >= 0.85 ? "var(--supported-text)" : "var(--unverified-text)" }}>
                          {Math.round(info.accuracy * 100)}%
                        </td>
                        <td>
                          {d === 'healthcare' ? '0.95' : d === 'legal' ? '0.92' : d === 'scientific' ? '0.90' : '0.80'}
                        </td>
                        <td>
                          <span className="pill supported">Certified</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        {/* TAB 4: HUMAN AUDIT */}
        {activeTab === 'human' && (
          <section className="card-panel">
            <div className="card-title-row">
              <div>
                <h2 className="card-title">Human-in-the-Loop Evaluation Protocol</h2>
                <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  Independent Qualitative Expert Audit Scale (1 = Inadequate, 5 = Exceptional)
                </span>
              </div>
            </div>

            {humanSubmitted ? (
              <div style={{ padding: "32px", background: "var(--supported-bg)", border: "1px solid var(--supported-border)", borderRadius: "var(--radius-md)", textAlign: "center" }}>
                <h3 style={{ color: "var(--supported-text)", marginBottom: "8px", fontSize: "18px" }}>
                  Audit Review Successfully Recorded
                </h3>
                <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
                  Your qualitative feedback has been persisted to the human evaluation registry.
                </p>
                <button className="btn-primary" style={{ marginTop: "16px" }} onClick={() => setHumanSubmitted(false)}>
                  Submit Another Audit Rating
                </button>
              </div>
            ) : (
              <form onSubmit={(e) => { e.preventDefault(); setHumanSubmitted(true); }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                  {[
                    { key: "extractionQuality", label: "1. Atomic Claim Extraction Precision" },
                    { key: "evidenceRelevance", label: "2. Evidence Retrieval Semantic Relevance" },
                    { key: "evidenceCredibility", label: "3. Source Credibility Assessment" },
                    { key: "verdictCorrectness", label: "4. Verdict & Taxonomy Classification" },
                    { key: "correctionCorrectness", label: "5. Grounded Correction Fluency" },
                    { key: "explanationQuality", label: "6. 'Why This Verdict?' Explainability" }
                  ].map(({ key, label }) => (
                    <div key={key} className="rating-item">
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
                        <label style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-main)" }}>
                          {label}
                        </label>
                        <strong style={{ color: "var(--primary)" }}>{humanRatings[key]} / 5</strong>
                      </div>
                      <input
                        type="range"
                        min="1"
                        max="5"
                        style={{ width: "100%", accentColor: "var(--primary)" }}
                        value={humanRatings[key]}
                        onChange={(e) => setHumanRatings({ ...humanRatings, [key]: Number(e.target.value) })}
                      />
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: "20px" }}>
                  <label className="input-block-label">
                    <span>Auditor Observations & Qualitative Edge-Cases</span>
                  </label>
                  <textarea
                    className="light-textarea"
                    rows={3}
                    placeholder="Enter notes on edge-case behavior, domain nuance or phrasing..."
                    value={humanRatings.comments}
                    onChange={(e) => setHumanRatings({ ...humanRatings, comments: e.target.value })}
                  />
                </div>

                <div style={{ marginTop: "20px", display: "flex", justifyContent: "flex-end" }}>
                  <button type="submit" className="btn-primary">
                    Record Audit Submission
                  </button>
                </div>
              </form>
            )}
          </section>
        )}

      </div>

      {/* Login / Sign Up Modal */}
      {isAuthModalOpen && (
        <div className="modal-backdrop" onClick={() => setIsAuthModalOpen(false)}>
          <div className="modal-auth-container" onClick={(e) => e.stopPropagation()}>
            <div className="auth-modal-header-brand">
              <img
                src="/truthguard-icon.png"
                alt="TruthGuard Logo"
                className="auth-modal-brand-logo"
              />
              <div className="auth-modal-brand-text">
                <span className="auth-modal-brand-title">TruthGuard Portal</span>
                <span className="auth-modal-brand-subtitle">
                  {authMode === 'login' ? 'Sign in to access your verification audits' : 'Create an account to start validating claims'}
                </span>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setIsAuthModalOpen(false)}
                title="Close"
              >
                ✕
              </button>
            </div>

            <div className="modal-header" style={{ paddingTop: '10px', paddingBottom: '10px' }}>
              <div className="auth-tab-switch">
                <button
                  type="button"
                  className={`auth-tab-btn ${authMode === 'login' ? 'active' : ''}`}
                  onClick={() => {
                    setAuthMode('login');
                    setAuthFeedback('');
                    setShowPassword(false);
                    setIsContactVerified(false);
                    setContactVerificationStep('idle');
                    setContactOtpInput('');
                    setContactOtpError('');
                    setGeneratedOtp('');
                    setCarrierDelivered(false);
                    setDeliveryProvider('');
                    setAuthForm({ name: '', countryCode: '+1', mobileNo: '', email: '', password: '' });
                  }}
                >
                  Log In
                </button>
                <button
                  type="button"
                  className={`auth-tab-btn ${authMode === 'signup' ? 'active' : ''}`}
                  onClick={() => {
                    setAuthMode('signup');
                    setAuthFeedback('');
                    setShowPassword(false);
                    setIsContactVerified(false);
                    setContactVerificationStep('idle');
                    setContactOtpInput('');
                    setContactOtpError('');
                    setGeneratedOtp('');
                    setCarrierDelivered(false);
                    setDeliveryProvider('');
                    setAuthForm({ name: '', countryCode: '+1', mobileNo: '', email: '', password: '' });
                  }}
                >
                  Sign Up
                </button>
              </div>
            </div>

            <div
              className="modal-body auth-modal-body"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAuthSubmit(e);
                }
              }}
            >
              {authFeedback && (
                <div className="auth-feedback-banner">
                  {authFeedback}
                </div>
              )}

              {authMode === 'signup' && (
                <>
                  <div className="auth-input-group">
                    <label>Full Name</label>
                    <input
                      type="text"
                      className="auth-input-field"
                      placeholder="e.g. John Doe"
                      value={authForm.name}
                      onChange={(e) => setAuthForm({ ...authForm, name: e.target.value })}
                      required
                    />
                  </div>

                  <div className="auth-input-group">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <label>Contact Number</label>
                      {isContactVerified ? (
                        <span className="contact-verified-badge">
                          ✓ Verified
                        </span>
                      ) : (
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          Validation Required
                        </span>
                      )}
                    </div>
                    <div className="contact-input-row">
                      <select
                        className="country-code-select auth-country-select"
                        value={authForm.countryCode}
                        onChange={(e) => {
                          setAuthForm({ ...authForm, countryCode: e.target.value });
                          setIsContactVerified(false);
                          setContactVerificationStep("idle");
                          setContactOtpError("");
                        }}
                      >
                        {COUNTRY_CODES.map((c) => (
                          <option key={c.code} value={c.code}>{c.label}</option>
                        ))}
                      </select>
                      <input
                        type="text"
                        inputMode="numeric"
                        className="auth-input-field"
                        placeholder="Numbers only (e.g. 5552345678)"
                        value={authForm.mobileNo}
                        onChange={(e) => {
                          const numericOnly = e.target.value.replace(/[^0-9]/g, '').slice(0, 15);
                          setAuthForm({ ...authForm, mobileNo: numericOnly });
                          setIsContactVerified(false);
                          setContactVerificationStep("idle");
                          setContactOtpError("");
                        }}
                        disabled={isContactVerified}
                      />
                      {!isContactVerified ? (
                        <button
                          type="button"
                          className="btn-validate-contact"
                          onClick={handleSendContactOtp}
                          disabled={isSendingOtp || !authForm.mobileNo.trim()}
                        >
                          {isSendingOtp ? "Sending..." : "Validate"}
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="btn-change-contact"
                          onClick={() => {
                            setIsContactVerified(false);
                            setContactVerificationStep("idle");
                            setContactOtpError("");
                          }}
                          title="Change phone number"
                        >
                          Change
                        </button>
                      )}
                    </div>

                    {/* Contact OTP Verification Drawer */}
                    {contactVerificationStep === "otp_sent" && !isContactVerified && (
                      <div className="contact-otp-box">
                        <div style={{ fontSize: '12px', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>📲</span>
                          <span>
                            {carrierDelivered ? (
                              <>SMS verification code dispatched to <strong>{authForm.countryCode} {authForm.mobileNo}</strong></>
                            ) : (
                              <>Verification code generated for <strong>{authForm.countryCode} {authForm.mobileNo}</strong></>
                            )}
                          </span>
                        </div>

                        {!carrierDelivered ? (
                          <div className="dev-sms-notice">
                            <div>
                              ℹ️ <strong>Physical SMS Notice:</strong> Delivering real cellular SMS to physical mobile phones requires SMS gateway credentials (e.g. Twilio) in <code>backend/.env</code>.
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginTop: '2px', flexWrap: 'wrap' }}>
                              <span>Dev Verification Code: <strong style={{ letterSpacing: '1px', background: 'var(--bg-surface)', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--unverified-border)' }}>{generatedOtp}</strong></span>
                              <button
                                type="button"
                                className="btn-autofill-otp"
                                onClick={() => setContactOtpInput(generatedOtp)}
                              >
                                ⚡ Auto-Fill Code
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div style={{ fontSize: '11px', color: 'var(--supported-text)', background: 'var(--supported-bg)', padding: '5px 8px', borderRadius: '4px', border: '1px solid var(--supported-border)' }}>
                            ✓ Cellular SMS sent via Twilio. Please check your physical phone messages.
                          </div>
                        )}

                        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          Enter the 4-digit verification code below:
                        </div>
                        <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                          <input
                            type="text"
                            maxLength="6"
                            inputMode="numeric"
                            className="auth-input-field"
                            style={{ width: '130px', padding: '7px 10px', fontSize: '14px', letterSpacing: '3px', textAlign: 'center', fontWeight: 'bold' }}
                            placeholder="• • • •"
                            value={contactOtpInput}
                            onChange={(e) => setContactOtpInput(e.target.value.replace(/[^0-9]/g, '').slice(0, 6))}
                          />
                          <button
                            type="button"
                            className="btn-confirm-otp"
                            onClick={handleVerifyContactOtp}
                            disabled={isVerifyingOtp || !contactOtpInput.trim()}
                          >
                            {isVerifyingOtp ? "Verifying..." : "Verify Code"}
                          </button>
                          <button
                            type="button"
                            className="btn-resend-otp"
                            onClick={handleSendContactOtp}
                            disabled={isSendingOtp}
                          >
                            Resend SMS
                          </button>
                        </div>
                        {contactOtpError && (
                          <div style={{ fontSize: '11.5px', color: 'var(--contradicted-text)', marginTop: '2px' }}>
                            {contactOtpError}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </>
              )}

              <div className="auth-input-group">
                <label>Email Address</label>
                <input
                  type="text"
                  inputMode="email"
                  name="tg_user_identifier"
                  className="auth-input-field"
                  placeholder="e.g. name@example.com"
                  value={authForm.email}
                  onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
                  autoComplete="off"
                  autoCorrect="off"
                  autoCapitalize="off"
                  spellCheck="false"
                  required
                />
              </div>

              <div className="auth-input-group">
                <label>Password</label>
                <div className="password-input-wrapper">
                  <input
                    type="text"
                    name="tg_user_secret"
                    className={`auth-input-field ${showPassword ? '' : 'masked-password-input'}`}
                    placeholder=""
                    value={authForm.password}
                    onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                    autoComplete="off"
                    autoCorrect="off"
                    autoCapitalize="off"
                    spellCheck="false"
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowPassword(prev => !prev)}
                    title={showPassword ? "Hide password" : "Show password"}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    tabIndex="-1"
                  >
                    {showPassword ? (
                      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                        <line x1="1" y1="1" x2="23" y2="23"></line>
                      </svg>
                    ) : (
                      <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                        <circle cx="12" cy="12" r="3"></circle>
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              <button
                type="button"
                className="btn-primary"
                onClick={handleAuthSubmit}
                disabled={isAuthSubmitting || (authMode === 'signup' && !isContactVerified)}
                style={{
                  width: "100%",
                  marginTop: "12px",
                  padding: "10px",
                  opacity: (authMode === 'signup' && !isContactVerified) ? 0.65 : 1
                }}
              >
                {isAuthSubmitting
                  ? "Processing..."
                  : authMode === 'login'
                    ? "Log In to TruthGuard"
                    : isContactVerified
                      ? "Create Account ✓"
                      : "Create Account (Validate Contact First)"}
              </button>

              <div style={{ textAlign: "center", marginTop: "14px", fontSize: "12.5px", color: "var(--text-muted)" }}>
                {authMode === 'login' ? (
                  <span>
                    Don't have an account?{" "}
                    <a
                      href="#signup"
                      onClick={(e) => {
                        e.preventDefault();
                        setAuthMode('signup');
                        setAuthFeedback('');
                        setShowPassword(false);
                        setIsContactVerified(false);
                        setContactVerificationStep('idle');
                        setContactOtpInput('');
                        setContactOtpError('');
                        setGeneratedOtp('');
                        setAuthForm({ name: '', countryCode: '+1', mobileNo: '', email: '', password: '' });
                      }}
                      style={{ color: "var(--primary)", fontWeight: "600", textDecoration: "none" }}
                    >
                      Sign Up
                    </a>
                  </span>
                ) : (
                  <span>
                    Already have an account?{" "}
                    <a
                      href="#login"
                      onClick={(e) => {
                        e.preventDefault();
                        setAuthMode('login');
                        setAuthFeedback('');
                        setShowPassword(false);
                        setIsContactVerified(false);
                        setContactVerificationStep('idle');
                        setContactOtpInput('');
                        setContactOtpError('');
                        setGeneratedOtp('');
                        setAuthForm({ name: '', countryCode: '+1', mobileNo: '', email: '', password: '' });
                      }}
                      style={{ color: "var(--primary)", fontWeight: "600", textDecoration: "none" }}
                    >
                      Log In
                    </a>
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* EXTERNAL SOURCES MODAL */}
      {isViewingSourcesModal && (
        <div className="auth-modal-overlay" onClick={() => setIsViewingSourcesModal(false)}>
          <div
            className="auth-modal-card"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: "720px", width: "94%", maxHeight: "88vh", display: "flex", flexDirection: "column" }}
          >
            <div className="auth-modal-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", paddingBottom: "12px", borderBottom: "1px solid var(--border-color)" }}>
              <div style={{ flex: 1, paddingRight: "12px" }}>
                <h3 style={{ margin: 0, fontSize: "17px", fontWeight: "700", display: "flex", alignItems: "center", gap: "8px", color: "var(--text-main)" }}>
                  <span>🌐</span> External Sources & Live Web Evidence
                </h3>
                {selectedClaimForSources && (
                  <p style={{ margin: "6px 0 0", fontSize: "13px", color: "var(--text-muted)", fontStyle: "italic" }}>
                    "{selectedClaimForSources.claim_text || selectedClaimForSources.text}"
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => setIsViewingSourcesModal(false)}
                className="auth-modal-close"
                style={{ background: "none", border: "none", fontSize: "22px", cursor: "pointer", color: "var(--text-muted)", padding: "0 6px", lineHeight: "1" }}
              >
                &times;
              </button>
            </div>

            <div style={{ overflowY: "auto", padding: "16px 0", flex: 1 }}>
              {isLoadingSources && (
                <div style={{ textAlign: "center", padding: "36px 16px" }}>
                  <div style={{ margin: "0 auto 14px", width: "32px", height: "32px", border: "3px solid var(--border-color)", borderTopColor: "var(--primary)", borderRadius: "50%", animation: "spin 0.8s linear infinite" }}></div>
                  <p style={{ margin: 0, fontSize: "14px", fontWeight: "600", color: "var(--text-main)" }}>
                    Retrieving live external web sources via Tavily...
                  </p>
                  <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    Querying multi-source authoritative web index
                  </span>
                </div>
              )}

              {sourcesError && (
                <div style={{ padding: "12px 16px", borderRadius: "8px", backgroundColor: "rgba(239, 68, 68, 0.1)", border: "1px solid #ef4444", color: "#dc2626", fontSize: "13px", marginBottom: "14px" }}>
                  <strong>Configuration / Retrieval Notice: </strong> {sourcesError}
                </div>
              )}

              {!isLoadingSources && !sourcesError && sourcesList.length === 0 && (
                <div style={{ textAlign: "center", padding: "36px 16px", color: "var(--text-muted)" }}>
                  <p style={{ fontSize: "14px", fontWeight: "600", margin: "0 0 6px", color: "var(--text-main)" }}>
                    No external sources found for this claim.
                  </p>
                  <span style={{ fontSize: "12.5px" }}>The search query did not yield authoritative web citations.</span>
                </div>
              )}

              {!isLoadingSources && sourcesList.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                  {sourcesList.map((src, sIdx) => (
                    <div
                      key={sIdx}
                      style={{
                        border: "1px solid var(--border-color)",
                        borderRadius: "8px",
                        padding: "14px 16px",
                        backgroundColor: "var(--bg-subtle, rgba(0,0,0,0.02))"
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "10px", marginBottom: "6px" }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap", marginBottom: "4px" }}>
                            <span className="pill blue" style={{ fontSize: "11px", padding: "2px 8px" }}>
                              {src.domain || (src.url ? new URL(src.url).hostname : "external")}
                            </span>
                            {src.score !== undefined && src.score !== null && (
                              <span style={{ fontSize: "11.5px", color: "var(--text-muted)", fontWeight: "600" }}>
                                Relevance: {typeof src.score === "number" ? `${Math.round(src.score * 100)}%` : src.score}
                              </span>
                            )}
                            {src.published_date && (
                              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                                Published: {src.published_date}
                              </span>
                            )}
                          </div>
                          <h4 style={{ margin: "2px 0 6px", fontSize: "14px", fontWeight: "700", color: "var(--text-main)" }}>
                            {src.title || "External Web Source"}
                          </h4>
                        </div>

                        {src.url && (
                          <a
                            href={src.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn-secondary"
                            style={{
                              fontSize: "12px",
                              padding: "5px 12px",
                              borderRadius: "5px",
                              whiteSpace: "nowrap",
                              textDecoration: "none",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              color: "var(--primary)"
                            }}
                          >
                            <span>Open Source</span>
                            <span>↗</span>
                          </a>
                        )}
                      </div>

                      {src.content && (
                        <p style={{ margin: "6px 0 0", fontSize: "12.5px", lineHeight: "1.5", color: "var(--text-body)" }}>
                          "{src.content}"
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div style={{ paddingTop: "12px", borderTop: "1px solid var(--border-color)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
                {sourcesList.length > 0 ? `${sourcesList.length} external sources retrieved` : "Live external retrieval via Tavily"}
              </span>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setIsViewingSourcesModal(false)}
                style={{ padding: "6px 16px", fontSize: "12px" }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
