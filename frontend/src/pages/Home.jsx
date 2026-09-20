import { Link } from "react-router-dom";

function Home() {
  return (
    <div className="app">
      <header className="navbar">
        <div className="logo"><span className="logo-icon">AI</span><span>ClaimAI</span></div>
        <Link className="login-btn" to="/new-claim">Start a claim</Link>
      </header>
      <main className="hero">
        <div className="hero-content">
          <span className="badge">VEHICLE CLAIM ASSISTANT</span>
          <h1>Prepare your claim <span>with confidence.</span></h1>
          <p>Upload clear vehicle photos and prepare them for a future AI damage-detection workflow.</p>
          <div className="hero-buttons"><Link className="primary-btn" to="/new-claim">Create new claim <span>→</span></Link></div>
        </div>
      </main>
    </div>
  );
}

export default Home;

